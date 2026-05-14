from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.database import get_db
from models.user import User
from models.chapter import Chapter
from models.chapter_mastery import ChapterMastery
from utils.dependencies import get_current_user

router = APIRouter(prefix="/chapters", tags=["Chapters"])


@router.get("/{chapter_id}")
def get_chapter(chapter_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    mastery = db.query(ChapterMastery).filter(
        ChapterMastery.user_id == current_user.id,
        ChapterMastery.chapter_id == chapter_id,
    ).first()
    mp = mastery.mastery_percentage if mastery else 0.0

    return {
        "id": chapter.id,
        "chapter_number": chapter.chapter_number,
        "title": chapter.title,
        "document_id": chapter.document_id,
        "document_title": chapter.document.title if chapter.document else None,
        "summary": chapter.summary,
        "mastery_percentage": mp,
        "page_start": chapter.page_start,
        "page_end": chapter.page_end,
        "knowledge_graph": chapter.knowledge_graph,
    }
