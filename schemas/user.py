from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    academic_level: Optional[str] = None
    major: Optional[str] = None
    xp_points: int = 0
    streak_days: int = 0
    subjects_mastered: int = 0
    is_active: bool = True
    is_verified: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProfileResponse(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: EmailStr
    avatar_url: Optional[str] = None
    academic_level: Optional[str] = None
    major: Optional[str] = None
    xp_points: int = 0
    streak_days: int = 0
    subjects_mastered: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
