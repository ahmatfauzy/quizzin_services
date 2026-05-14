from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.database import Base
from models.question import Difficulty


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    difficulty = Column(Enum(Difficulty), default=Difficulty.medium)
    total_score = Column(Float, default=0.0)
    xp_gained = Column(Integer, default=0)
    answers = Column(JSONB, nullable=True)
    time_taken_seconds = Column(Integer, nullable=True)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="quiz_attempts")
    chapter = relationship("Chapter", back_populates="quiz_attempts")
