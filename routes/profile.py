from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from database.database import get_db
from models.user import User
from schemas.auth import ProfileUpdateRequest, ChangePasswordRequest
from schemas.user import ProfileResponse
from utils.dependencies import get_current_user
from utils.security import verify_password, get_password_hash
from utils.cloudinary_service import upload_avatar

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("")
def update_profile(payload: ProfileUpdateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.academic_level is not None:
        current_user.academic_level = payload.academic_level
    if payload.major is not None:
        current_user.major = payload.major
    db.commit()
    db.refresh(current_user)
    return {
        "message": "Profile updated successfully.",
        "user": {
            "id": current_user.id,
            "full_name": current_user.full_name,
            "email": current_user.email,
            "avatar_url": current_user.avatar_url,
            "academic_level": current_user.academic_level,
            "major": current_user.major,
        },
    }


@router.put("/avatar")
async def update_avatar(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        raise HTTPException(status_code=400, detail="Only image files are supported")
    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max size is 5MB")
    avatar_url = upload_avatar(file_bytes)
    current_user.avatar_url = avatar_url
    db.commit()
    return {"message": "Avatar updated successfully.", "avatar_url": avatar_url}


@router.put("/change-password")
def change_password(payload: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.hashed_password or not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.", headers={"X-Error-Code": "WRONG_PASSWORD"})
    current_user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully."}
