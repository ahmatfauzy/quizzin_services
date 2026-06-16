from database.database import SessionLocal
from models.chapter import Chapter
from models.question import Question, QuestionType, Difficulty
from models.document import Document
from utils.nlp_service import _call_groq

db = SessionLocal()
chapter = db.query(Chapter).filter(Chapter.id == 3).first()
if not chapter:
    print("Chapter 3 not found")
    exit(1)

prompt = """You are an expert educator. Given chapter text and difficulty level, generate exactly 5 essay questions.
Output strict JSON only, no markdown:
{
  "questions": [
    {
      "subject_tag": "Topic area",
      "question_text": "Main question sentence",
      "question_description": "Optional context",
      "question_type": "essay",
      "hint": null,
      "options": null,
      "correct_answer": null,
      "reference_facts": ["fact 1", "fact 2"]
    }
  ]
}
IMPORTANT: Generate EXACTLY 5 essay questions. NO multiple choice.
"""

print("Generating 5 essays...")
result = _call_groq(prompt + f"\n\nGenerate exactly 5 questions at 'easy' difficulty.", chapter.raw_text[:6000], temperature=0.3, max_tokens=2048)

if isinstance(result, dict) and "questions" in result:
    for q in result["questions"]:
        question = Question(
            chapter_id=chapter.id, subject_tag=q.get("subject_tag"),
            question_text=q["question_text"],
            question_description=q.get("question_description"),
            hint=q.get("hint"),
            question_type=QuestionType.essay, difficulty=Difficulty("easy"),
            options=None, correct_answer=None,
            reference_facts=q.get("reference_facts", []),
        )
        db.add(question)
    db.commit()
    print("Inserted 5 essays!")
else:
    print("Failed to generate:", result)
