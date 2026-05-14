import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.database import Base


class QuestionType(str, enum.Enum):
    multiple_choice = "multiple_choice"
    essay = "essay"
    short_answer = "short_answer"


class Difficulty(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hots = "hots"


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    subject_tag = Column(String, nullable=True)
    question_text = Column(Text, nullable=False)
    question_description = Column(Text, nullable=True)
    hint = Column(Text, nullable=True)
    question_type = Column(Enum(QuestionType), nullable=False)
    difficulty = Column(Enum(Difficulty), default=Difficulty.medium)
    options = Column(JSONB, nullable=True)
    correct_answer = Column(String, nullable=True)
    reference_facts = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chapter = relationship("Chapter", back_populates="questions")
