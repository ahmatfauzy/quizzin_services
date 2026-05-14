from pydantic import BaseModel, EmailStr
from typing import Optional

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class VerifyEmailRequest(BaseModel):
    token: str

class ResendVerificationRequest(BaseModel):
    email: EmailStr

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    academic_level: Optional[str] = None
    major: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
