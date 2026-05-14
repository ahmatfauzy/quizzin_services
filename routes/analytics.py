from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta

from database.database import get_db
from models.user import User
from models.document import Document, DocumentStatus
from models.chapter import Chapter
from models.chapter_mastery import ChapterMastery
from models.quiz_attempt import QuizAttempt
from schemas.analytics import (
    KnowledgeGapResponse, KnowledgeGapItem,
    PerformanceResponse, PerformanceTrendItem,
    LearningAnalyticsResponse, RecommendedFocusItem, IncorrectAnswerItem,
)
from utils.dependencies import get_current_user
from utils.adaptive import suggest_next_difficulty
from utils.nlp_service import generate_tutor_suggestion

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/learning")
def learning_analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Summary
    today_attempts = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == current_user.id,
        QuizAttempt.completed_at >= date.today(),
    ).all()
    xp_today = sum(a.xp_gained or 0 for a in today_attempts)
    mastered = current_user.subjects_mastered or 0

    # AI readiness
    all_mastery = db.query(ChapterMastery).filter(ChapterMastery.user_id == current_user.id).all()
    avg_mastery = sum(m.mastery_percentage for m in all_mastery) / len(all_mastery) if all_mastery else 0.0
    readiness = round(avg_mastery, 1)
    threshold = 80.0
    if readiness >= threshold:
        status = "ready_to_advance"
        label = "Ready to Advance"
        action = "Advance to Next Level"
    elif readiness >= 60:
        status = "on_track"
        label = "On Track"
        action = "Review Weak Areas"
    else:
        status = "needs_improvement"
        label = "Needs Improvement"
        action = "Focus on Fundamentals"

    # Recommended focus — find weak chapters
    weak = []
    for m in all_mastery:
        if m.mastery_percentage < 60:
            ch = db.query(Chapter).filter(Chapter.id == m.chapter_id).first()
            if ch and ch.document:
                severity = "high" if m.mastery_percentage < 30 else "medium"
                weak.append(RecommendedFocusItem(
                    topic=ch.title or "Unknown",
                    reason=f"Mastery at {m.mastery_percentage}% — needs attention.",
                    reference_book=ch.document.title,
                    reference_chapter=f"Chapter {ch.chapter_number}: {ch.title or ''}",
                    reference_pages=f"pp. {ch.page_start or 0}-{ch.page_end or 0}",
                    action="view_materials", action_label="View Materials",
                    action_style="secondary", severity=severity,
                ))

    # Incorrect answers — from recent attempts
    recent_attempts = db.query(QuizAttempt).filter(
        QuizAttempt.user_id == current_user.id
    ).order_by(QuizAttempt.completed_at.desc()).limit(5).all()
    incorrect = []
    for a in recent_attempts:
        for r in (a.answers or []):
            if r.get("is_correct") == False:
                ch = db.query(Chapter).filter(Chapter.id == a.chapter_id).first()
                incorrect.append(IncorrectAnswerItem(
                    question_id=r["question_id"], question_text=r.get("question_text", ""),
                    review_chapter=f"Chapter {ch.chapter_number if ch else '?'}: {ch.title if ch else 'Unknown'}",
                    action_label="Review Concept",
                ))

    # Tutor suggestion
    mastered_chapters = [m.chapter.title for m in all_mastery if m.mastery_percentage >= 100 and m.chapter and m.chapter.title]
    suggestion = generate_tutor_suggestion(mastered_chapters)

    return LearningAnalyticsResponse(
        summary={
            "total_score": round(avg_mastery, 1),
            "max_score": 100,
            "greeting": f"Great Job, {current_user.full_name or 'Learner'}!",
            "message": f"You've mastered {mastered} subjects today. Keep it up!",
            "xp_gained_today": xp_today,
            "streak_days": current_user.streak_days or 0,
        },
        ai_readiness={
            "status": status, "status_label": label,
            "recommended_action": action,
            "note": "Reviewing the Recommended Focus areas below will strengthen your foundation.",
            "readiness_percentage": readiness, "threshold_percentage": threshold,
        },
        recommended_focus=weak[:5],
        incorrect_answers=incorrect[:5],
    )


@router.get("/knowledge-gap", response_model=KnowledgeGapResponse)
def knowledge_gap(document_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        return KnowledgeGapResponse(document_id=document_id, document_title="", chapters=[])

    chapters_out = []
    for ch in doc.chapters:
        m = db.query(ChapterMastery).filter(
            ChapterMastery.user_id == current_user.id, ChapterMastery.chapter_id == ch.id
        ).first()
        mp = m.mastery_percentage if m else 0.0
        chapters_out.append(KnowledgeGapItem(
            chapter_id=ch.id, chapter_title=ch.title, mastery_percentage=mp, weak_topics=[],
        ))
    return KnowledgeGapResponse(document_id=document_id, document_title=doc.title, chapters=chapters_out)


@router.get("/performance", response_model=PerformanceResponse)
def performance(document_id: int = Query(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        return PerformanceResponse(overall_mastery=0.0, total_attempts=0, xp_points=current_user.xp_points or 0, subjects_mastered=current_user.subjects_mastered or 0, trend=[])

    all_m = []
    for ch in doc.chapters:
        m = db.query(ChapterMastery).filter(ChapterMastery.user_id == current_user.id, ChapterMastery.chapter_id == ch.id).first()
        if m:
            all_m.append(m.mastery_percentage)
    overall = sum(all_m) / len(all_m) if all_m else 0.0

    from models.chapter import Chapter as Ch
    attempts = db.query(QuizAttempt).join(Ch, QuizAttempt.chapter_id == Ch.id).filter(
        QuizAttempt.user_id == current_user.id,
        Ch.document_id == document_id,
    ).count()

    return PerformanceResponse(
        overall_mastery=round(overall, 1), total_attempts=attempts,
        xp_points=current_user.xp_points or 0, subjects_mastered=current_user.subjects_mastered or 0,
        trend=[],
    )
