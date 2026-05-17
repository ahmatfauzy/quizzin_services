import json
import math

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database.database import get_db
from models.user import User
from models.face_data import FaceData
from schemas.face_auth import FaceRegisterRequest, FaceLoginRequest
from utils.dependencies import get_current_user
from utils.security import create_access_token
from config.settings import settings
from datetime import timedelta
from utils.logger import log_action

router = APIRouter(prefix="/auth", tags=["Face Authentication"])

FACE_SIMILARITY_THRESHOLD = 0.65


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


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
        "has_face": True,
    }


@router.post("/register-face")
def register_face(
    payload: FaceRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(FaceData).filter(FaceData.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Face data already registered")

    face_data = FaceData(
        user_id=current_user.id,
        embedding=json.dumps(payload.embedding),
    )
    db.add(face_data)
    db.commit()

    return {"message": "Face registered successfully"}


@router.post("/login-face")
def login_face(
    payload: FaceLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    all_faces = db.query(FaceData).all()
    best_score = 0.0
    best_user = None

    for face in all_faces:
        stored_embedding = json.loads(face.embedding)
        score = _cosine_similarity(payload.embedding, stored_embedding)
        if score > best_score:
            best_score = score
            best_user = face.user

    if best_score < FACE_SIMILARITY_THRESHOLD or best_user is None:
        raise HTTPException(status_code=401, detail="Face not recognized")

    log_action(best_user.id, "login_face", "/auth/login-face", f"score={best_score:.4f}", request.client.host)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(best_user.id)},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": _build_user_dict(best_user),
    }


@router.get("/has-face")
def has_face(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(FaceData).filter(FaceData.user_id == current_user.id).first()
    return {"has_face": existing is not None}
