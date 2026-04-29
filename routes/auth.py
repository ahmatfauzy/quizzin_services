from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import timedelta
from authlib.integrations.starlette_client import OAuth

from database.database import get_db
from models.user import User
from schemas.auth import GoogleToken, TokenResponse
from schemas.user import UserResponse
from utils.security import verify_google_token, create_access_token
from config.settings import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Setup Authlib OAuth untuk Web
oauth = OAuth()
oauth.register(
    name='google',
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

def handle_user_login(db: Session, email: str, full_name: str, picture: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            full_name=full_name,
            picture=picture
        )
        db.add(user)
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

# 1. MOBILE OAUTH VERIFICATION (Verifikasi token dari Flutter)
@router.post("/google/mobile", response_model=TokenResponse)
def google_auth_mobile(payload: GoogleToken, db: Session = Depends(get_db)):
    idinfo = verify_google_token(payload.token)
    if not idinfo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email = idinfo.get("email")
    full_name = idinfo.get("name")
    picture = idinfo.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="Email not provided in Google token")

    return handle_user_login(db, email, full_name, picture)


# 2. WEB OAUTH LOGIN FLOW (Redirect Frontend ke Google)
@router.get("/google/web/login")
async def google_auth_web_login(request: Request):
    redirect_uri = request.url_for('google_auth_web_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)


# 3. WEB OAUTH CALLBACK (Callback dari Google ke Backend)
@router.get("/google/web/callback")
async def google_auth_web_callback(request: Request, db: Session = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    userinfo = token.get('userinfo')
    if not userinfo:
        raise HTTPException(status_code=400, detail="No user info found")
    
    email = userinfo.get("email")
    full_name = userinfo.get("name")
    picture = userinfo.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="Email not provided in Google token")

    return handle_user_login(db, email, full_name, picture)
