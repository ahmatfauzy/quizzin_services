from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.database import Base


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    knowledge_graph = Column(JSONB, nullable=True)
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chapters")
    questions = relationship("Question", back_populates="chapter", cascade="all, delete-orphan")
    quiz_attempts = relationship("QuizAttempt", back_populates="chapter", cascade="all, delete-orphan")
    mastery_records = relationship("ChapterMastery", back_populates="chapter", cascade="all, delete-orphan")
