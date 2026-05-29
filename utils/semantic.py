import json
import re
from groq import Groq
from config.settings import settings

_client = Groq(api_key=settings.GROQ_API_KEY)

SCORING_PROMPT = """You are a strict but fair academic evaluator with smart semantic understanding.
Compare the student's answer against the reference facts and correct answer context.

Output strict JSON only, no markdown:
{
  "score": 0.85,
  "missing_concepts": ["concept A", "concept B"],
  "feedback": "Constructive feedback in the same language as the student's answer."
}

Rules for Smart Semantic Evaluation:
- Score 0.0 = completely wrong or irrelevant, 1.0 = perfect answer
- Consider answers CORRECT if they convey the same meaning, even with different wording
- Accept paraphrases, synonyms, and rephrased explanations as valid
- Recognize equivalent concepts expressed in different ways
- Award partial credit (0.3-0.7) if the answer covers some key points but misses others
- Award high credit (0.8-0.9) if the answer is semantically equivalent but uses different terminology
- Only give 0.0 if the answer is completely wrong, off-topic, or contradicts the facts
- Check if the student's answer demonstrates understanding of the core concepts, not just keyword matching
- Always provide constructive, encouraging feedback in the same language as the student's answer
- List specific missing concepts so the student knows what to improve"""


def normalize_text(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def semantic_similarity_local(user_answer: str, reference: str) -> float:
    user_words = set(normalize_text(user_answer).split())
    ref_words = set(normalize_text(reference).split())
    if not ref_words:
        return 0.0
    overlap = len(user_words & ref_words)
    return overlap / len(ref_words)


def score_mcq(user_answer: str, correct_answer: str) -> dict:
    user_clean = user_answer.strip().upper()
    correct_clean = correct_answer.strip().upper()

    correct_letter = correct_clean.split(".")[0].strip() if "." in correct_clean else correct_clean
    user_letter = user_clean.split(".")[0].strip() if "." in user_clean else user_clean

    if user_letter == correct_letter or user_clean == correct_clean:
        return {"score": 1.0, "missing_concepts": [], "feedback": "Correct!"}
    return {"score": 0.0, "missing_concepts": [], "feedback": f"Incorrect. The correct answer is: {correct_answer}"}


def score_essay(user_answer: str, correct_answer: str, reference_facts: list) -> dict:
    if not user_answer or not user_answer.strip():
        return {"score": 0.0, "missing_concepts": reference_facts, "feedback": "No answer provided."}

    local_scores = []
    if reference_facts:
        for fact in reference_facts:
            local_scores.append(semantic_similarity_local(user_answer, fact))
    if correct_answer:
        local_scores.append(semantic_similarity_local(user_answer, correct_answer))

    local_score = max(local_scores) if local_scores else 0.0

    if local_score >= 0.7:
        return {
            "score": round(min(local_score + 0.1, 1.0), 2),
            "missing_concepts": [],
            "feedback": "Excellent! Your answer captures the key concepts well."
        }

    if not settings.GROQ_API_KEY:
        return {
            "score": round(local_score, 2),
            "missing_concepts": [],
            "feedback": "Partial credit given based on keyword overlap."
        }

    prompt = f"""
Reference facts: {json.dumps(reference_facts)}
Correct answer context: {correct_answer}

Student answer: {user_answer}

Evaluate whether the student's answer demonstrates understanding of the core concepts, even if expressed differently.
"""
    try:
        response = _client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": SCORING_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1024,
        )
        result = json.loads(response.choices[0].message.content)
        ai_score = result.get("score", 0.5)
        if ai_score >= 0.75:
            return result
        return {
            "score": round(max(ai_score, local_score), 2),
            "missing_concepts": result.get("missing_concepts", []),
            "feedback": result.get("feedback", "Review the reference facts for key concepts.")
        }
    except Exception:
        return {
            "score": round(local_score, 2),
            "missing_concepts": [],
            "feedback": "Partial credit given based on keyword analysis."
        }
