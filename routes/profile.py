from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request
from sqlalchemy.orm import Session
from database.database import get_db
from models.user import User
from schemas.auth import ProfileUpdateRequest, ChangePasswordRequest
from schemas.user import ProfileResponse
from utils.dependencies import get_current_user
from utils.security import verify_password, get_password_hash
from utils.cloudinary_service import upload_avatar
from utils.logger import log_action, LOG_FILE
import os

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("", response_model=ProfileResponse)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("")
def update_profile(payload: ProfileUpdateRequest, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.academic_level is not None:
        current_user.academic_level = payload.academic_level
    if payload.major is not None:
        current_user.major = payload.major
    db.commit()
    db.refresh(current_user)
    log_action(current_user.id, "update_profile", "/profile", "fields=full_name,academic_level,major", request.client.host)
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
async def update_avatar(request: Request, file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        raise HTTPException(status_code=400, detail="Only image files are supported")
    file_bytes = await file.read()
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max size is 5MB")
    avatar_url = upload_avatar(file_bytes)
    current_user.avatar_url = avatar_url
    db.commit()
    log_action(current_user.id, "update_avatar", "/profile/avatar", f"file={file.filename}", request.client.host)
    return {"message": "Avatar updated successfully.", "avatar_url": avatar_url}


@router.put("/change-password")
def change_password(payload: ChangePasswordRequest, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not current_user.hashed_password or not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.", headers={"X-Error-Code": "WRONG_PASSWORD"})
    current_user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    log_action(current_user.id, "change_password", "/profile/change-password", "", request.client.host)
    return {"message": "Password changed successfully."}


@router.delete("")
def delete_account(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id
    db.delete(current_user)
    db.commit()
    log_action(user_id, "delete_account", "/profile", "", request.client.host)
    return {"message": "Account deleted successfully."}


def get_activity_description(action, detail):
    if action == "login":
        return "Anda berhasil masuk ke dalam akun."
    elif action == "login_face":
        return "Anda berhasil masuk menggunakan pemindaian wajah."
    elif action == "register":
        return "Anda berhasil mendaftarkan akun baru."
    elif action == "forgot_password":
        return "Anda melakukan permintaan reset kata sandi."
    elif action == "update_profile":
        return "Anda memperbarui data profil akun Anda."
    elif action == "update_avatar":
        return "Anda mengubah foto profil akun Anda."
    elif action == "change_password":
        return "Anda berhasil mengubah kata sandi akun."
    elif action == "upload_document":
        title = ""
        if detail and "title=" in detail:
            title = detail.split("title=")[1].split(",")[0].strip()
        if title:
            return f"Anda mengunggah dokumen pembelajaran '{title}'."
        return "Anda mengunggah dokumen pembelajaran baru."
    elif action == "generate_quiz":
        chapter = ""
        if detail and "chapter=" in detail:
            chapter = detail.split("chapter=")[1].split(",")[0].strip()
        if chapter:
            return f"Anda membuat kuis latihan baru dari '{chapter}'."
        return "Anda membuat kuis latihan baru."
    elif action == "delete_account":
        return "Anda menghapus akun dari sistem."
    
    formatted_action = str(action).replace("_", " ").title() if action else "Aktivitas"
    return f"Anda melakukan: {formatted_action}."


@router.get("/activities")
def get_activities(current_user: User = Depends(get_current_user)):
    if not os.path.exists(LOG_FILE):
        return {"activities": []}
    
    user_activities = []
    with open(LOG_FILE, "r") as f:
        for line in f:
            if f"user_id={current_user.id} " in line or f"user_id={current_user.id}\n" in line or f"user_id={current_user.id}|" in line.replace(" ", ""):
                # To be safer about substring matching like user_id=4 vs user_id=40
                parts = [p.strip() for p in line.split("|")]
                if any(p == f"user_id={current_user.id}" for p in parts):
                    timestamp = parts[0]
                    action = None
                    detail = None
                    for part in parts:
                        if part.startswith("action="):
                            action = part.split("=", 1)[1]
                        elif part.startswith("detail="):
                            detail = part.split("=", 1)[1]
                    
                    description = get_activity_description(action, detail)
                    
                    user_activities.append({
                        "timestamp": timestamp,
                        "action": action,
                        "description": description,
                        "detail": detail
                    })
    
    user_activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"activities": user_activities}
