from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.database import Base

class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    score = Column(Float, nullable=False)
    knowledge_gap_analysis = Column(JSON, nullable=True) # AI analysis of wrong answers
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", backref="results")
    quiz = relationship("Quiz", backref="results")
