from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import date

from database.database import get_db
from models.user import User
from models.chapter import Chapter
from models.question import Question, QuestionType, Difficulty
from models.quiz_attempt import QuizAttempt
from models.chapter_mastery import ChapterMastery
from models.document import Document
from schemas.quiz import (
    GenerateQuizRequest, GenerateQuizResponse, QuestionItem, QuestionOption,
    SubmitQuizRequest, SubmitQuizResponse, QuizResultItem,
    QuizHistoryResponse, QuizAttemptDetailResponse,
)
from utils.dependencies import get_current_user
from utils.nlp_service import generate_questions
from utils.semantic import score_mcq, score_essay
from utils.adaptive import suggest_next_difficulty, calculate_xp, update_streak
from utils.logger import log_action

router = APIRouter(prefix="/quizzes", tags=["Quizzes"])

ESTIMATED_TIMES = {"easy": 900, "medium": 1200, "hots": 1800}


@router.post("/generate", response_model=GenerateQuizResponse, status_code=201)
def gen_quiz(payload: GenerateQuizRequest, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chapter = db.query(Chapter).filter(Chapter.id == payload.chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    if not chapter.raw_text:
        raise HTTPException(status_code=400, detail="Chapter has no extracted text")

    difficulty = payload.difficulty if payload.difficulty in ("easy", "medium", "hots") else "medium"
    
    questions = db.query(Question).filter(Question.chapter_id == chapter.id, Question.difficulty == difficulty).all()
    
    mcqs = [q for q in questions if q.question_type == QuestionType.multiple_choice][:15]
    essays = [q for q in questions if q.question_type == QuestionType.essay][:5]
    selected_questions = mcqs + essays
    
    if len(selected_questions) < 20:
        count = 20
        questions_raw = generate_questions(chapter.raw_text, difficulty, count)
        for q in questions_raw:
            qtype_raw = str(q.get("question_type", "multiple_choice")).lower().strip()
            if "essay" in qtype_raw:
                qtype = QuestionType.essay
            elif "short_answer" in qtype_raw:
                qtype = QuestionType.short_answer
            else:
                qtype = QuestionType.multiple_choice

            question = Question(
                chapter_id=chapter.id, subject_tag=q.get("subject_tag"),
                question_text=q["question_text"],
                question_description=q.get("question_description"),
                hint=q.get("hint"),
                question_type=qtype, difficulty=Difficulty(difficulty),
                options=q.get("options"), correct_answer=q.get("correct_answer"),
                reference_facts=q.get("reference_facts", []),
            )
            db.add(question)
        db.commit()
        
        questions = db.query(Question).filter(Question.chapter_id == chapter.id, Question.difficulty == difficulty).all()
        mcqs = [q for q in questions if q.question_type == QuestionType.multiple_choice][:15]
        essays = [q for q in questions if q.question_type == QuestionType.essay][:5]
        selected_questions = mcqs + essays

    attempt = QuizAttempt(user_id=current_user.id, chapter_id=chapter.id, difficulty=Difficulty(difficulty), answers=[])
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    questions_out = []
    for i, question in enumerate(selected_questions, start=1):

        opts = None
        if question.options:
            opts = [QuestionOption(key=o["key"], text=o["text"]) for o in question.options]

        questions_out.append(QuestionItem(
            id=question.id, order=i, subject_tag=question.subject_tag,
            question_text=question.question_text,
            question_description=question.question_description,
            question_type=question.question_type.value,
            hint=question.hint, options=opts,
        ))

    log_action(current_user.id, "generate_quiz", "/quizzes/generate", f"chapter={chapter.title}, difficulty={difficulty}, count={len(questions_out)}", request.client.host)

    return GenerateQuizResponse(
        attempt_id=attempt.id, chapter_id=chapter.id,
        chapter_title=chapter.title, difficulty=difficulty,
        total_questions=len(questions_out),
        estimated_time_seconds=ESTIMATED_TIMES.get(difficulty, 600),
        questions=questions_out,
    )


@router.post("/{attempt_id}/submit", response_model=SubmitQuizResponse)
def submit_quiz(attempt_id: int, payload: SubmitQuizRequest, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id, QuizAttempt.user_id == current_user.id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")

    chapter = db.query(Chapter).filter(Chapter.id == attempt.chapter_id).first()
    results = []
    total = 0.0

    for i, ans in enumerate(payload.answers, start=1):
        question = db.query(Question).filter(Question.id == ans.question_id).first()
        if not question:
            continue
        if question.question_type == QuestionType.multiple_choice:
            scoring = score_mcq(ans.answer, question.correct_answer or "")
        else:
            scoring = score_essay(ans.answer, question.correct_answer or "", question.reference_facts or [])
        s = scoring.get("score", 0.0)
        total += s
        results.append({
            "question_id": question.id, "order": i, "subject_tag": question.subject_tag,
            "question_text": question.question_text,
            "question_type": question.question_type.value,
            "user_answer": ans.answer,
            "correct_answer": question.correct_answer if question.question_type == QuestionType.multiple_choice else None,
            "score": round(s * 100, 1),
            "is_correct": s >= 1.0 if question.question_type == QuestionType.multiple_choice else None,
            "feedback": scoring.get("feedback", ""),
            "missing_concepts": scoring.get("missing_concepts", []),
        })

    qc = len(results)
    final_score = round((total / qc) * 100, 1) if qc > 0 else 0.0
    xp = calculate_xp(final_score, attempt.difficulty.value if attempt.difficulty else "medium")

    attempt.total_score = final_score
    attempt.xp_gained = xp
    attempt.answers = results
    attempt.time_taken_seconds = payload.time_taken_seconds
    db.commit()

    # Update mastery
    mastery = db.query(ChapterMastery).filter(
        ChapterMastery.user_id == current_user.id, ChapterMastery.chapter_id == attempt.chapter_id
    ).first()
    if mastery:
        mastery.mastery_percentage = round((mastery.mastery_percentage + final_score) / 2, 1)
    else:
        db.add(ChapterMastery(user_id=current_user.id, chapter_id=attempt.chapter_id, mastery_percentage=final_score))
    db.commit()

    # Update user XP & streak
    current_user.xp_points = (current_user.xp_points or 0) + xp
    current_user.streak_days = update_streak(current_user)
    current_user.last_active_date = date.today()

    # Count subjects mastered
    mastered = db.query(ChapterMastery).filter(
        ChapterMastery.user_id == current_user.id, ChapterMastery.mastery_percentage >= 100
    ).count()
    current_user.subjects_mastered = mastered
    db.commit()

    # Next difficulty
    recent = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == current_user.id, QuizAttempt.chapter_id == attempt.chapter_id
    ).order_by(QuizAttempt.completed_at.desc()).limit(3).all()
    scores = [a.total_score for a in recent if a.total_score is not None]
    next_diff = suggest_next_difficulty(scores)

    result_items = [QuizResultItem(**r) for r in results]

    log_action(current_user.id, "submit_quiz", f"/quizzes/{attempt_id}/submit", f"score={final_score}, xp={xp}", request.client.host)

    return SubmitQuizResponse(
        attempt_id=attempt.id, chapter_title=chapter.title if chapter else None,
        difficulty=attempt.difficulty.value if attempt.difficulty else "medium",
        total_score=final_score, xp_gained=xp,
        mastery_updated=mastery.mastery_percentage if mastery else final_score,
        time_taken_seconds=payload.time_taken_seconds,
        next_difficulty_suggestion=next_diff, results=result_items,
    )


@router.get("/history", response_model=QuizHistoryResponse)
def quiz_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attempts = db.query(QuizAttempt).filter(QuizAttempt.user_id == current_user.id).order_by(QuizAttempt.completed_at.desc()).all()
    items = []
    for a in attempts:
        chapter = db.query(Chapter).filter(Chapter.id == a.chapter_id).first()
        doc_title = None
        if chapter and chapter.document:
            doc_title = chapter.document.title
        items.append({
            "attempt_id": a.id, "chapter_title": chapter.title if chapter else None,
            "document_title": doc_title,
            "difficulty": a.difficulty.value if a.difficulty else "medium",
            "total_score": a.total_score or 0.0, "xp_gained": a.xp_gained or 0,
            "time_taken_seconds": a.time_taken_seconds, "completed_at": a.completed_at,
        })
    return {"attempts": items}


@router.get("/attempt/{attempt_id}", response_model=QuizAttemptDetailResponse)
def get_attempt(attempt_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    attempt = db.query(QuizAttempt).filter(QuizAttempt.id == attempt_id, QuizAttempt.user_id == current_user.id).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Quiz attempt not found")
    chapter = db.query(Chapter).filter(Chapter.id == attempt.chapter_id).first()
    doc_title = chapter.document.title if chapter and chapter.document else None
    results = [QuizResultItem(**r) for r in (attempt.answers or [])]
    return QuizAttemptDetailResponse(
        attempt_id=attempt.id, chapter_id=attempt.chapter_id,
        chapter_title=chapter.title if chapter else None, document_title=doc_title,
        difficulty=attempt.difficulty.value if attempt.difficulty else "medium",
        total_score=attempt.total_score or 0.0, xp_gained=attempt.xp_gained or 0,
        time_taken_seconds=attempt.time_taken_seconds, completed_at=attempt.completed_at,
        results=results,
    )
