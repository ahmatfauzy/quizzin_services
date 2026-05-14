from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date
from sqlalchemy.sql import func
from database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    avatar_url = Column("picture", String, nullable=True)
    hashed_password = Column(String, nullable=True)
    academic_level = Column(String, nullable=True)
    major = Column(String, nullable=True)
    xp_points = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    last_active_date = Column(Date, nullable=True)
    subjects_mastered = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
