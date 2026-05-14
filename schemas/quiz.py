from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class GenerateQuizRequest(BaseModel):
    chapter_id: int
    difficulty: str


class QuestionOption(BaseModel):
    key: str
    text: str


class QuestionItem(BaseModel):
    id: int
    order: int
    subject_tag: Optional[str] = None
    question_text: str
    question_description: Optional[str] = None
    question_type: str
    hint: Optional[str] = None
    options: Optional[List[QuestionOption]] = None

    class Config:
        from_attributes = True


class GenerateQuizResponse(BaseModel):
    attempt_id: int
    chapter_id: int
    chapter_title: Optional[str] = None
    difficulty: str
    total_questions: int
    estimated_time_seconds: int
    questions: List[QuestionItem]


class SubmitAnswerItem(BaseModel):
    question_id: int
    answer: str


class SubmitQuizRequest(BaseModel):
    answers: List[SubmitAnswerItem]
    time_taken_seconds: int


class QuizResultItem(BaseModel):
    question_id: int
    order: int
    subject_tag: Optional[str] = None
    question_text: str
    question_type: str
    user_answer: str
    correct_answer: Optional[str] = None
    score: float
    is_correct: Optional[bool] = None
    feedback: str
    missing_concepts: List[str] = []


class SubmitQuizResponse(BaseModel):
    attempt_id: int
    chapter_title: Optional[str] = None
    difficulty: str
    total_score: float
    xp_gained: int = 0
    mastery_updated: float
    time_taken_seconds: int
    next_difficulty_suggestion: str
    results: List[QuizResultItem]


class QuizHistoryItem(BaseModel):
    attempt_id: int
    chapter_title: Optional[str] = None
    document_title: Optional[str] = None
    difficulty: str
    total_score: float
    xp_gained: int = 0
    time_taken_seconds: Optional[int] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class QuizHistoryResponse(BaseModel):
    attempts: List[QuizHistoryItem]


class QuizAttemptDetailResponse(BaseModel):
    attempt_id: int
    chapter_id: int
    chapter_title: Optional[str] = None
    document_title: Optional[str] = None
    difficulty: str
    total_score: float
    xp_gained: int = 0
    time_taken_seconds: Optional[int] = None
    completed_at: Optional[datetime] = None
    results: List[QuizResultItem]
