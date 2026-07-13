from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ChapterSummaryItem(BaseModel):
    id: int
    chapter_number: int
    title: Optional[str] = None
    mastery_percentage: float = 0.0
    is_completed: bool = False
    is_locked: bool = False
    status_icon: str = "not_started"
    action_label: str = "Explore Concepts"
    page_start: Optional[int] = None
    page_end: Optional[int] = None

    class Config:
        from_attributes = True


class DocumentListItem(BaseModel):
    id: int
    title: str
    original_filename: Optional[str] = None
    total_pages: Optional[int] = None
    total_chapters: int = 0
    status: str
    created_at: datetime
    uploaded_label: str = ""

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: List[DocumentListItem]


class DocumentUploadResponse(BaseModel):
    id: int
    title: str
    original_filename: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentStatusResponse(BaseModel):
    id: int
    status: str
    total_chapters: int = 0
    total_pages: Optional[int] = None

    class Config:
        from_attributes = True


class DocumentDetailResponse(BaseModel):
    id: int
    title: str
    original_filename: Optional[str] = None
    total_pages: Optional[int] = None
    total_chapters: int = 0
    status: str
    created_at: datetime
    chapters: List[ChapterSummaryItem] = []

    class Config:
        from_attributes = True

class StudentAttemptItem(BaseModel):
    id: int
    chapter_title: str
    total_score: float
    time_taken_seconds: Optional[int] = None
    completed_at: datetime
    difficulty: str

    class Config:
        from_attributes = True

class ScannerResultItem(BaseModel):
    user_id: int
    name: str
    email: str
    avatar_url: Optional[str] = None
    scanned_at: datetime
    total_score: float = 0.0
    total_attempts: int = 0
    average_mastery: float = 0.0
    attempts: List[StudentAttemptItem] = []

class ScannerListResponse(BaseModel):
    document_id: int
    scanners: List[ScannerResultItem]

class StudentInsightsResponse(BaseModel):
    insights: List[str]
