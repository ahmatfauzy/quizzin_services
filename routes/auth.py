from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta, date

from database.database import get_db
from models.user import User
from schemas.auth import (
    TokenResponse, RegisterRequest, LoginRequest, VerifyEmailRequest,
    ResendVerificationRequest, ForgotPasswordRequest, ResetPasswordRequest,
)
from schemas.user import UserResponse
from utils.security import (
    create_access_token, get_password_hash, verify_password,
    generate_email_token, verify_email_token, SALT_VERIFY, SALT_RESET,
)
from utils.dependencies import get_current_user
from config.settings import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _build_user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "academic_level": user.academic_level,
        "major": user.major,
        "xp_points": user.xp_points or 0,
        "streak_days": user.streak_days or 0,
        "subjects_mastered": user.subjects_mastered or 0,
        "is_verified": user.is_verified,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _build_token_response(user: User) -> TokenResponse:
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=_build_user_dict(user),
    )


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=get_password_hash(payload.password),
        is_verified=False,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = generate_email_token(new_user.email, SALT_VERIFY)
    from utils.email import send_verification_email
    send_verification_email(new_user.email, token)

    return {
        "message": "Registration successful. Please check your email to verify your account.",
        "user": {"id": new_user.id, "full_name": new_user.full_name, "email": new_user.email, "is_verified": False},
    }


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Please check your inbox.", headers={"X-Error-Code": "EMAIL_NOT_VERIFIED"})
    return _build_token_response(user)


@router.post("/verify-email")
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    email = verify_email_token(payload.token, SALT_VERIFY)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        return {"message": "Email is already verified."}
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return _build_token_response(user)


@router.post("/resend-verification")
def resend_verification(payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email is already verified.", headers={"X-Error-Code": "ALREADY_VERIFIED"})
    token = generate_email_token(user.email, SALT_VERIFY)
    from utils.email import send_verification_email
    send_verification_email(user.email, token)
    return {"message": "Verification email has been resent."}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        token = generate_email_token(user.email, SALT_RESET)
        from utils.email import send_password_reset_email
        send_password_reset_email(user.email, token)
    return {"message": "If that email exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    email = verify_email_token(payload.token, SALT_RESET)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Password has been reset successfully. Please log in."}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
