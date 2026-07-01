from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import timedelta, date

from database.database import get_db
from models.user import User
from models.face_data import FaceData
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
from utils.logger import log_action

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _build_user_dict(user: User, db: Optional[Session] = None) -> dict:
    has_face = False
    if db is not None:
        has_face = db.query(FaceData).filter(FaceData.user_id == user.id).first() is not None

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
        "has_face": has_face,
        "role": getattr(user, 'role', 'user'),
    }


def _build_token_response(user: User, db: Optional[Session] = None) -> TokenResponse:
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=_build_user_dict(user, db),
    )


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
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

    log_action(new_user.id, "register", "/auth/register", f"email={new_user.email}", request.client.host)

    return {
        "message": "Registration successful. Please check your email to verify your account.",
        "user": {"id": new_user.id, "full_name": new_user.full_name, "email": new_user.email, "is_verified": False},
    }


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified. Please check your inbox.", headers={"X-Error-Code": "EMAIL_NOT_VERIFIED"})
    log_action(user.id, "login", "/auth/login", f"email={user.email}", request.client.host)
    return _build_token_response(user, db)


@router.post("/verify-email")
def verify_email(payload: VerifyEmailRequest, request: Request, db: Session = Depends(get_db)):
    email = verify_email_token(payload.token, SALT_VERIFY)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        return {"message": "Email is already verified."}
    user.is_verified = True
    db.commit()
    db.refresh(user)
    log_action(user.id, "verify_email", "/auth/verify-email", f"email={user.email}", request.client.host)
    return _build_token_response(user, db)


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
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        token = generate_email_token(user.email, SALT_RESET)
        from utils.email import send_password_reset_email
        send_password_reset_email(user.email, token)
        log_action(user.id, "forgot_password", "/auth/forgot-password", f"email={user.email}", request.client.host)
    return {"message": "If that email exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    email = verify_email_token(payload.token, SALT_RESET)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    log_action(user.id, "reset_password", "/auth/reset-password", f"email={user.email}", request.client.host)
    return {"message": "Password has been reset successfully. Please log in."}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/verify-email", response_class=HTMLResponse)
def verify_email_page(token: str = Query(...), db: Session = Depends(get_db)):
    try:
        email = verify_email_token(token, SALT_VERIFY)
    except HTTPException as e:
        return HTMLResponse(
            f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Verifikasi Email</title>
<style>body{{font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f4f4f4}} .card{{background:#fff;padding:40px;border-radius:12px;text-align:center;max-width:400px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}} h2{{margin:0 0 8px}} p{{color:#666}}</style>
</head><body><div class="card"><h2>❌ Gagal</h2><p>{e.detail}</p></div></body></html>""",
            status_code=400,
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        return HTMLResponse(
            """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Verifikasi Email</title>
<style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f4f4f4} .card{background:#fff;padding:40px;border-radius:12px;text-align:center;max-width:400px;box-shadow:0 2px 10px rgba(0,0,0,0.1)} h2{margin:0 0 8px} p{color:#666}</style>
</head><body><div class="card"><h2>❌ Gagal</h2><p>User tidak ditemukan.</p></div></body></html>""",
            status_code=404,
        )

    if user.is_verified:
        return HTMLResponse(
            """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Verifikasi Email</title>
<style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f4f4f4} .card{background:#fff;padding:40px;border-radius:12px;text-align:center;max-width:400px;box-shadow:0 2px 10px rgba(0,0,0,0.1)} h2{margin:0 0 8px} p{color:#666}</style>
</head><body><div class="card"><h2>✅ Sudah Terverifikasi</h2><p>Email kamu sudah diverifikasi sebelumnya. Silakan login di aplikasi.</p></div></body></html>""",
        )

    user.is_verified = True
    db.commit()
    db.refresh(user)

    return HTMLResponse(
        """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Verifikasi Email</title>
<style>body{font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f4f4f4} .card{background:#fff;padding:40px;border-radius:12px;text-align:center;max-width:400px;box-shadow:0 2px 10px rgba(0,0,0,0.1)} h2{margin:0 0 8px} p{color:#666}</style>
</head><body><div class="card"><h2>✅ Verifikasi Berhasil!</h2><p>Email kamu sudah berhasil diverifikasi. Silakan login di aplikasi.</p></div></body></html>""",
    )


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_page(token: str = Query(...)):
    return HTMLResponse(
        f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reset Password</title>
<style>body{{font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f4f4f4}} .card{{background:#fff;padding:40px;border-radius:12px;max-width:400px;box-shadow:0 2px 10px rgba(0,0,0,0.1)}} h2{{margin:0 0 12px;text-align:center}} input{{width:100%;padding:10px;margin:8px 0;border:1px solid #ddd;border-radius:8px;box-sizing:border-box}} button{{width:100%;padding:12px;background:#0056FF;color:#fff;border:none;border-radius:8px;font-size:16px;cursor:pointer;margin-top:8px}} .msg{{text-align:center;color:green;display:none;margin-top:12px}} .err{{text-align:center;color:red;display:none;margin-top:12px}}</style>
</head><body><div class="card"><h2>Reset Password</h2><form id="form"><input type="password" id="pw" placeholder="Password baru" minlength="6" required><input type="password" id="cpw" placeholder="Konfirmasi password baru" minlength="6" required><button type="submit">Reset Password</button></form><p class="msg" id="msg">Password berhasil direset! Silakan login di aplikasi.</p><p class="err" id="err"></p></div>
<script>document.getElementById('form').addEventListener('submit',async function(e){{e.preventDefault();var pw=document.getElementById('pw').value;var cpw=document.getElementById('cpw').value;if(pw!==cpw){{document.getElementById('err').style.display='block';document.getElementById('err').textContent='Password tidak cocok!';return}}var r=await fetch('/auth/reset-password',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{token:'{token}',new_password:pw}})}});var d=await r.json();if(r.ok){{document.getElementById('form').style.display='none';document.getElementById('msg').style.display='block'}}else{{document.getElementById('err').style.display='block';document.getElementById('err').textContent=d.detail||'Gagal'}}}});</script></body></html>""",
    )
