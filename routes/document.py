from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date

from database.database import get_db
from models.user import User
from models.document import Document, DocumentStatus
from models.chapter_mastery import ChapterMastery
from models.quiz_attempt import QuizAttempt
from models.chapter import Chapter
from models.notification import Notification
from schemas.document import (
    DocumentUploadResponse, DocumentStatusResponse, DocumentDetailResponse,
    DocumentListResponse, DocumentListItem,
)
from utils.dependencies import get_current_user
from utils.cloudinary_service import upload_pdf, delete_file
from utils.adaptive import calc_activity_score
from utils.logger import log_action

router = APIRouter(prefix="/documents", tags=["Documents"])

MAX_FILE_SIZE = 10 * 1024 * 1024
LOCK_THRESHOLD = 60


def process_pdf(document_id: int, pdf_bytes: bytes):
    from database.database import SessionLocal
    from models.chapter import Chapter
    from utils.pdf_service import extract_chapters
    from utils.nlp_service import generate_summary, generate_knowledge_graph, generate_questions
    from models.question import Question, QuestionType, Difficulty

    db = SessionLocal()
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        db.close()
        return
    try:
        if not pdf_bytes or len(pdf_bytes) < 100:
            raise Exception(f"PDF bytes too small ({len(pdf_bytes)} bytes)")

        import fitz
        pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
        doc.total_pages = len(pdf)

        chapters = extract_chapters(pdf_bytes)
        for i, ch in enumerate(chapters, start=1):
            kg = generate_knowledge_graph(ch["text"])
            summary = generate_summary(ch["text"])
            chapter = Chapter(
                document_id=document_id, chapter_number=i,
                title=ch["title"], raw_text=ch["text"],
                summary=summary, knowledge_graph=kg,
                page_start=ch["page_start"], page_end=ch["page_end"],
            )
            db.add(chapter)
            db.flush()  # Ensure chapter gets an ID

            for diff in ["easy", "medium", "hots"]:
                questions_raw = generate_questions(ch["text"], diff, count=20)
                for q in questions_raw:
                    qtype_raw = str(q.get("question_type", "multiple_choice")).lower().strip()
                    if "essay" in qtype_raw:
                        qtype = QuestionType.essay
                    elif "short_answer" in qtype_raw:
                        qtype = QuestionType.short_answer
                    else:
                        qtype = QuestionType.multiple_choice

                    question = Question(
                        chapter_id=chapter.id, subject_tag=q.get("subject_tag"),
                        question_text=q["question_text"],
                        question_description=q.get("question_description"),
                        hint=q.get("hint"),
                        question_type=qtype, difficulty=Difficulty(diff),
                        options=q.get("options"), correct_answer=q.get("correct_answer"),
                        reference_facts=q.get("reference_facts", []),
                    )
                    db.add(question)

        doc.status = DocumentStatus.ready
        db.commit()
    except Exception as e:
        doc.status = DocumentStatus.failed
        db.commit()
        print(f"PDF processing failed for {document_id}: {e}")
    finally:
        db.close()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    request: Request,
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Max size is 10MB")

    upload_result = upload_pdf(file_bytes, current_user.id, file.filename or "document.pdf")
    doc = Document(
        user_id=current_user.id, title=title,
        original_filename=file.filename,
        cloudinary_url=upload_result["secure_url"],
        cloudinary_public_id=upload_result["public_id"],
        status=DocumentStatus.processing,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    background_tasks.add_task(process_pdf, doc.id, file_bytes)
    log_action(current_user.id, "upload_document", "/documents/upload", f"title={title}, file={file.filename}", request.client.host)
    return doc


def _uploaded_label(dt):
    if not dt:
        return ""
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


def _action_label(mastery): return "Review Concepts" if mastery >= 100 else ("Continue Exploring" if mastery > 0 else "Explore Concepts")


def _status_icon(mastery, is_locked): return "locked" if is_locked else ("completed" if mastery >= 100 else ("in_progress" if mastery > 0 else "not_started"))


def _is_locked(cn, mmap): return False if cn == 1 else mmap.get(cn - 1, 0) < LOCK_THRESHOLD


@router.get("/", response_model=DocumentListResponse)
def list_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    items = []
    for d in docs:
        cc = len(d.chapters) if d.chapters else 0
        items.append(DocumentListItem(
            id=d.id, title=d.title, original_filename=d.original_filename,
            total_pages=d.total_pages, total_chapters=cc,
            status=d.status.value if d.status else "processing",
            created_at=d.created_at, uploaded_label=_uploaded_label(d.created_at),
        ))
    return {"documents": items}


@router.get("/shared/{document_id}", response_model=DocumentDetailResponse)
def get_shared_document(document_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    from schemas.document import ChapterSummaryItem
    chapters_out = []
    for ch in doc.chapters:
        chapters_out.append(ChapterSummaryItem(
            id=ch.id, chapter_number=ch.chapter_number, title=ch.title,
            mastery_percentage=0.0, is_completed=False, is_locked=False,
            status_icon="not_started", action_label="Explore Concepts",
            page_start=ch.page_start, page_end=ch.page_end,
        ))

    return DocumentDetailResponse(
        id=doc.id, title=doc.title, original_filename=doc.original_filename,
        total_pages=doc.total_pages, total_chapters=len(doc.chapters),
        status=doc.status.value if doc.status else "processing",
        created_at=doc.created_at, chapters=chapters_out,
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(document_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    mastery_map = {}
    for ch in doc.chapters:
        m = db.query(ChapterMastery).filter(ChapterMastery.user_id == current_user.id, ChapterMastery.chapter_id == ch.id).first()
        mastery_map[ch.chapter_number] = m.mastery_percentage if m else 0.0

    from schemas.document import ChapterSummaryItem
    chapters_out = []
    for ch in doc.chapters:
        mp = mastery_map.get(ch.chapter_number, 0.0)
        locked = _is_locked(ch.chapter_number, mastery_map)
        chapters_out.append(ChapterSummaryItem(
            id=ch.id, chapter_number=ch.chapter_number, title=ch.title,
            mastery_percentage=mp, is_completed=mp >= 100, is_locked=locked,
            status_icon=_status_icon(mp, locked),
            action_label=_action_label(mp),
            page_start=ch.page_start, page_end=ch.page_end,
        ))

    return DocumentDetailResponse(
        id=doc.id, title=doc.title, original_filename=doc.original_filename,
        total_pages=doc.total_pages, total_chapters=len(doc.chapters),
        status=doc.status.value if doc.status else "processing",
        created_at=doc.created_at, chapters=chapters_out,
    )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
def get_status(document_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentStatusResponse(
        id=doc.id, status=doc.status.value if doc.status else "processing",
        total_chapters=len(doc.chapters) if doc.chapters else 0,
        total_pages=doc.total_pages,
    )


@router.delete("/{document_id}")
def delete_document(document_id: int, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == document_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.cloudinary_public_id:
        delete_file(doc.cloudinary_public_id, "raw")
    db.delete(doc)
    db.commit()
    log_action(current_user.id, "delete_document", f"/documents/{document_id}", f"title={doc.title}", request.client.host)
    return {"message": "Document deleted successfully."}
