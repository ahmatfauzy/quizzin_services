import asyncio
from utils.nlp_service import generate_questions

text = "Hukum Newton tentang gerak terdiri dari tiga hukum utama. Hukum pertama menyatakan bahwa benda akan tetap diam atau bergerak beraturan jika resultan gaya nol. Hukum kedua F = m*a. Hukum ketiga aksi reaksi." * 50
print(f"Chapter text len: {len(text)}")
print("Generating...")
questions = generate_questions(text, "easy", 20)
print("Generated total:", len(questions))
mcq_count = sum(1 for q in questions if "essay" not in str(q.get("question_type", "")).lower())
essay_count = sum(1 for q in questions if "essay" in str(q.get("question_type", "")).lower())
print(f"MCQs: {mcq_count}, Essays: {essay_count}")
if questions:
    for i, q in enumerate(questions[:3] + questions[-3:]):
        print(i, q.get("question_type"), q.get("question_text"))
else:
    print("No questions returned.")
