from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from models.user import User
from models.notification import Notification
from schemas.analytics import NotificationListResponse, NotificationItem
from utils.dependencies import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifs = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).limit(50).all()

    items = [NotificationItem.model_validate(n) for n in notifs]
    unread = sum(1 for n in notifs if not n.is_read)
    return NotificationListResponse(unread_count=unread, notifications=items)


@router.put("/{notification_id}/read")
def mark_read(notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    n = db.query(Notification).filter(
        Notification.id == notification_id, Notification.user_id == current_user.id
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"message": "Notification marked as read."}


@router.put("/read-all")
def mark_all_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read."}
