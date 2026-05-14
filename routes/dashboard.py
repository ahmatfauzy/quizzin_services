from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import date, timedelta

from database.database import get_db
from models.user import User
from models.document import Document
from models.chapter_mastery import ChapterMastery
from models.quiz_attempt import QuizAttempt
from schemas.analytics import DashboardResponse, WeeklyActivityItem, RecentDocumentItem
from utils.dependencies import get_current_user
from utils.adaptive import calc_activity_score
from utils.nlp_service import generate_tutor_suggestion

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _uploaded_label(dt):
    if not dt:
        return ""
    from datetime import datetime
    delta = datetime.utcnow() - dt.replace(tzinfo=None)
    if delta.days == 0:
        return "Today"
    if delta.days == 1:
        return "1 day ago"
    if delta.days < 7:
        return f"{delta.days} days ago"
    if delta.days < 30:
        return f"{delta.days // 7} weeks ago"
    return dt.strftime("%b %d, %Y")


@router.get("", response_model=DashboardResponse)
def dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    greeting = {
        "full_name": current_user.full_name or "Learner",
        "message": "Ready to master your subjects today?",
    }

    mastery_records = db.query(ChapterMastery).filter(
        ChapterMastery.user_id == current_user.id
    ).all()
    total_mastery = sum(m.mastery_percentage for m in mastery_records)
    avg_mastery = round(total_mastery / len(mastery_records)) if mastery_records else 0

    overall_progress = {
        "percentage": avg_mastery,
        "xp_points": current_user.xp_points or 0,
        "subjects_mastered": current_user.subjects_mastered or 0,
    }

    today = date.today()
    start = today - timedelta(days=today.weekday())
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekly = []
    for i in range(7):
        d = start + timedelta(days=i)
        day_attempts = db.query(QuizAttempt).filter(
            QuizAttempt.user_id == current_user.id,
            QuizAttempt.completed_at >= d,
            QuizAttempt.completed_at < d + timedelta(days=1),
        ).all()
        cnt = len(day_attempts)
        avg = sum(a.total_score or 0 for a in day_attempts) / cnt if cnt else 0
        weekly.append(WeeklyActivityItem(day=days[i], quiz_count=cnt, activity_score=calc_activity_score(cnt, avg)))

    recent_docs = db.query(Document).filter(
        Document.user_id == current_user.id
    ).order_by(Document.created_at.desc()).limit(5).all()
    recent = []
    for d in recent_docs:
        recent.append(RecentDocumentItem(
            id=d.id, title=d.title, original_filename=d.original_filename,
            total_pages=d.total_pages,
            status=d.status.value if d.status else "processing",
            has_chapters=bool(d.chapters),
            uploaded_at=d.created_at, uploaded_label=_uploaded_label(d.created_at),
        ))

    mastered_titles = [m.chapter.title for m in mastery_records if m.mastery_percentage >= 100 and m.chapter and m.chapter.title]
    suggestion_text = generate_tutor_suggestion(mastered_titles)

    return DashboardResponse(
        greeting=greeting,
        overall_progress=overall_progress,
        weekly_activity=weekly,
        recent_documents=recent,
        tutor_suggestion={"message": suggestion_text},
    )
