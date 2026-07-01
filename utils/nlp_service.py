import json
from groq import Groq
from config.settings import settings

_client = Groq(api_key=settings.GROQ_API_KEY, timeout=120.0)

SUMMARY_PROMPT = """You are an expert academic summarizer. Given a chapter from an academic textbook, write a concise, well-structured summary in the same language as the original text.

Guidelines:
- Capture all key concepts, definitions, theorems, and formulas
- Keep it under 300 words
- Use clear, educational language
- Output plain text only, no markdown"""

KNOWLEDGE_GRAPH_PROMPT = """You are an expert knowledge engineer. Extract the core concept, modules, entities, and relationships from the given chapter text.

Output strict JSON only, no markdown:
{
  "core_concept": {"title": "Main Concept", "label": "Core Concept"},
  "modules": [  
    {"module_number": "4.1", "title": "Sub Topic", "icon_type": "book"}
  ],
  "entities": ["Entity1", "Entity2"],
  "relations": [
    {"from": "Entity1", "to": "Entity2", "label": "relates to"}
  ]
}

icon_type must be one of: trending_up, cycle, atom, function, book, diagram

Guidelines:
- Extract 1 core concept
- 3-6 modules sub-topics
- 5-15 key entities (concepts, theorems, people, methods)
- Define meaningful relationships"""

QUESTION_GEN_PROMPT = """You are an expert educator. Given chapter text and difficulty level, generate exactly 20 quiz questions: 15 multiple choice and 5 essay questions.

Output strict JSON only, no markdown:
{
  "questions": [
    {
      "subject_tag": "Topic area",
      "question_text": "Main question sentence",
      "question_description": "Optional sub-text or context shown below the question, null if not needed",
      "question_type": "multiple_choice",
      "hint": "Optional hint shown below MCQ options, null for essay",
      "options": [
        {"key": "A", "text": "Choice text"},
        {"key": "B", "text": "Choice text"},
        {"key": "C", "text": "Choice text"},
        {"key": "D", "text": "Choice text"}
      ],
      "correct_answer": "B",
      "reference_facts": ["fact 1", "fact 2"]
    }
  ]
}

IMPORTANT:
- Generate EXACTLY 15 multiple_choice questions first, then EXACTLY 5 essay questions (total 20).
- Keep all text (descriptions, hints, facts, options) as brief and concise as possible to avoid exceeding output size limits!
- For essay questions: question_type = "essay", options = null, correct_answer = null, hint = null.
- For essay questions: question_description MUST NOT be null. Provide a brief scenario or context.
- For multiple_choice: 4 options required (A, B, C, D), correct_answer is the key letter (A/B/C/D).
- Vary difficulty: easy (recall), medium (application), hots (analysis).
- Each question MUST have reference_facts for scoring (1-2 short sentences max).
- Essay questions should test deeper understanding, synthesis, and explanation."""



def _call_groq(system_prompt: str, user_content: str, temperature: float = 0.3, max_tokens: int = 2048) -> dict | str:
    if not settings.GROQ_API_KEY:
        return {"error": "GROQ_API_KEY not configured"}
    try:
        response = _client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"error": str(e)}


def generate_summary(chapter_text: str) -> str:
    truncated = chapter_text[:5000]
    result = _call_groq(SUMMARY_PROMPT, truncated, temperature=0.7, max_tokens=1024)
    if isinstance(result, dict) and "error" in result:
        return f"[Summary unavailable: {result['error']}]"
    return result if isinstance(result, str) else chapter_text[:300]


def generate_knowledge_graph(chapter_text: str) -> dict:
    truncated = chapter_text[:5000]
    result = _call_groq(KNOWLEDGE_GRAPH_PROMPT, truncated, temperature=0.7, max_tokens=1024)
    if isinstance(result, dict) and "entities" in result:
        return result
    return {"core_concept": None, "modules": [], "entities": [], "relations": []}


def generate_questions(chapter_text: str, difficulty: str = "medium", count: int = 20) -> list[dict]:
    if not chapter_text or len(chapter_text.strip()) < 50:
        print(f"[NLP] Chapter text too short ({len(chapter_text)} chars), skipping")
        return []
    truncated = chapter_text[:6000]
    prompt = QUESTION_GEN_PROMPT + f"\n\nGenerate exactly {count} questions at '{difficulty}' difficulty level. VERY IMPORTANT: You must return ALL {count} questions in the JSON array."
    result = _call_groq(prompt, truncated, temperature=0.3, max_tokens=8192)
    if isinstance(result, dict) and "error" in result:
        print(f"[NLP] Question generation failed: {result['error']}")
        return []
    if isinstance(result, dict) and "questions" in result:
        return result["questions"]
    print(f"[NLP] Unexpected response: {str(result)[:200]}")
    return []


def generate_tutor_suggestion(mastered_chapters: list[str]) -> str:
    if not settings.GROQ_API_KEY:
        return "Keep up the great work! Review your mastered chapters to reinforce your learning."
    prompt = f"""The student has mastered these chapters:
{', '.join(mastered_chapters[:5])}

Give ONE encouraging sentence suggesting what to study or review next. Be specific and motivating. Output plain text only."""
    try:
        response = _client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Ready to take your learning to the next level? Try a mixed review quiz."
