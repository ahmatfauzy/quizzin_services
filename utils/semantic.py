import json
from groq import Groq
from config.settings import settings

_client = Groq(api_key=settings.GROQ_API_KEY)

SCORING_PROMPT = """You are a strict but fair academic evaluator.
Compare the student's answer against the reference facts.
Output strict JSON only, no markdown:
{
  "score": 0.85,
  "missing_concepts": ["concept A", "concept B"],
  "feedback": "Constructive feedback in the same language as the student's answer."
}

Rules:
- Score 0.0 = completely wrong, 1.0 = perfect
- For MCQ: score 1.0 if answer matches correct answer exactly, 0.0 otherwise
- For essay/short_answer: evaluate semantic similarity to reference facts
- Always provide constructive, encouraging feedback"""


def score_mcq(user_answer: str, correct_answer: str) -> dict:
    user_clean = user_answer.strip().upper()
    correct_clean = correct_answer.strip().upper()

    correct_letter = correct_clean.split(".")[0].strip() if "." in correct_clean else correct_clean
    user_letter = user_clean.split(".")[0].strip() if "." in user_clean else user_clean

    if user_letter == correct_letter or user_clean == correct_clean:
        return {"score": 1.0, "missing_concepts": [], "feedback": "Correct!"}
    return {"score": 0.0, "missing_concepts": [], "feedback": f"Incorrect. The correct answer is: {correct_answer}"}


def score_essay(user_answer: str, correct_answer: str, reference_facts: list) -> dict:
    if not settings.GROQ_API_KEY:
        return score_mcq(user_answer, correct_answer)

    prompt = f"""
Reference facts: {json.dumps(reference_facts)}
Correct answer context: {correct_answer}

Student answer: {user_answer}
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
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {"score": 0.5, "missing_concepts": [], "feedback": "Scoring unavailable."}
