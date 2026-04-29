from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta
import httpx
from pydantic import BaseModel

from database.database import get_db
from models.user import User
from schemas.auth import GoogleToken, TokenResponse, RegisterRequest, LoginRequest, ResendVerificationRequest
from schemas.user import UserResponse
from utils.security import (
    verify_google_token, create_access_token, get_password_hash, 
    verify_password, create_verification_token, verify_email_token
)
from config.settings import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

class GoogleWebToken(BaseModel):
    token: str | None = None
    code: str | None = None

def handle_user_login(db: Session, email: str, full_name: str, picture: str, is_verified: bool = True):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            full_name=full_name,
            picture=picture,
            is_verified=is_verified
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    elif not user.is_verified and is_verified:
        user.is_verified = True
        db.commit()
        db.refresh(user)
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}, expires_delta=access_token_expires
    )
    
    user_data = UserResponse.model_validate(user).model_dump()
    user_data["created_at"] = user_data["created_at"].isoformat() if user_data["created_at"] else None
    if user_data["updated_at"]:
        user_data["updated_at"] = user_data["updated_at"].isoformat()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_data
    )

# --- GOOGLE OAUTH ---

@router.post("/google/mobile", response_model=TokenResponse)
def google_auth_mobile(payload: GoogleToken, db: Session = Depends(get_db)):
    idinfo = verify_google_token(payload.token)
    if not idinfo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")
    
    email = idinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided in Google token")

    return handle_user_login(db, email, idinfo.get("name"), idinfo.get("picture"), is_verified=True)

@router.post("/google/web", response_model=TokenResponse)
async def google_auth_web(payload: GoogleWebToken, db: Session = Depends(get_db)):
    if not payload.token and not payload.code:
        raise HTTPException(status_code=400, detail="Please provide either 'token' or 'code'")

    idinfo = None
    if payload.token:
        idinfo = verify_google_token(payload.token)
    elif payload.code:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": payload.code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": "postmessage",
                    "grant_type": "authorization_code"
                }
            )
            data = response.json()
            if "id_token" not in data:
                raise HTTPException(status_code=400, detail=f"Failed to exchange code: {data.get('error_description', 'Unknown error')}")
            idinfo = verify_google_token(data["id_token"])

    if not idinfo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token or code")
    
    email = idinfo.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email not provided in Google credential")

    return handle_user_login(db, email, idinfo.get("name"), idinfo.get("picture"), is_verified=True)


# --- CREDENTIALS AUTH ---

@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_password = get_password_hash(payload.password)
    
    new_user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hashed_password,
        is_verified=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Generate verification token
    verification_token = create_verification_token(new_user.email)
    
    # Kirim email verifikasi ke user
    from utils.email import send_verification_email
    send_verification_email(new_user.email, verification_token)
    
    return {
        "message": "User registered successfully. Please verify your email."
    }

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    
    if not user or not user.hashed_password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        
    if not user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Please verify your email first")
        
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}, expires_delta=access_token_expires
    )
    
    user_data = UserResponse.model_validate(user).model_dump()
    user_data["created_at"] = user_data["created_at"].isoformat() if user_data["created_at"] else None
    if user_data["updated_at"]:
        user_data["updated_at"] = user_data["updated_at"].isoformat()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_data
    )

@router.post("/resend-verification")
def resend_verification(payload: ResendVerificationRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email is already verified")
        
    verification_token = create_verification_token(user.email)
    
    from utils.email import send_verification_email
    send_verification_email(user.email, verification_token)
    
    return {
        "message": "Verification email resent"
    }

@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    email = verify_email_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.is_verified:
        return {"message": "Email is already verified"}
        
    user.is_verified = True
    db.commit()
    
    return {"message": "Email verified successfully. You can now login."}
