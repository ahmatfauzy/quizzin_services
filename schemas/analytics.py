from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class WeeklyActivityItem(BaseModel):
    day: str
    quiz_count: int = 0
    activity_score: int = 0


class RecentDocumentItem(BaseModel):
    id: int
    title: str
    original_filename: Optional[str] = None
    total_pages: Optional[int] = None
    status: str
    has_chapters: bool = False
    uploaded_at: Optional[datetime] = None
    uploaded_label: str = ""


class DashboardResponse(BaseModel):
    greeting: dict
    overall_progress: dict
    weekly_activity: List[WeeklyActivityItem]
    recent_documents: List[RecentDocumentItem]
    tutor_suggestion: dict


class RecommendedFocusItem(BaseModel):
    topic: str
    reason: str
    reference_book: str
    reference_chapter: str
    reference_pages: str
    action: str
    action_label: str
    action_style: str
    severity: str


class IncorrectAnswerItem(BaseModel):
    question_id: int
    question_text: str
    review_chapter: str
    action_label: str


class LearningAnalyticsResponse(BaseModel):
    summary: dict
    ai_readiness: dict
    recommended_focus: List[RecommendedFocusItem]
    incorrect_answers: List[IncorrectAnswerItem]


class KnowledgeGapItem(BaseModel):
    chapter_id: int
    chapter_title: Optional[str] = None
    mastery_percentage: float = 0.0
    weak_topics: List[str] = []


class KnowledgeGapResponse(BaseModel):
    document_id: int
    document_title: str
    chapters: List[KnowledgeGapItem]


class PerformanceTrendItem(BaseModel):
    date: str
    avg_score: float


class PerformanceResponse(BaseModel):
    overall_mastery: float
    total_attempts: int
    xp_points: int = 0
    subjects_mastered: int = 0
    trend: List[PerformanceTrendItem]


class NotificationItem(BaseModel):
    id: int
    title: str
    body: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    unread_count: int
    notifications: List[NotificationItem]
