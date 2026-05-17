from pydantic import BaseModel, EmailStr
from typing import Optional, List


class FaceRegisterRequest(BaseModel):
    embedding: List[float]


class FaceLoginRequest(BaseModel):
    embedding: List[float]
