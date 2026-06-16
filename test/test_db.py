from database.database import SessionLocal
from models.chapter import Chapter
from models.question import Question

db = SessionLocal()
chapter = db.query(Chapter).filter(Chapter.id == 3).first()
if chapter:
    print("Chapter 3 text length:", len(chapter.raw_text))
else:
    print("Chapter 3 not found")

questions = db.query(Question).filter(Question.chapter_id == 3).all()
print("Questions in DB:", len(questions))
mcqs = 0
essays = 0
for q in questions:
    if q.question_type.value == "multiple_choice":
        mcqs += 1
    elif q.question_type.value == "essay":
        essays += 1
print(f"DB MCQs: {mcqs}, DB Essays: {essays}")
