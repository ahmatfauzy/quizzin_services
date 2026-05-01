from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Form
from sqlalchemy.orm import Session
from database.database import get_db
from models.user import User
from models.document import Document
from schemas.document import DocumentResponse
from utils.dependencies import get_current_user
import cloudinary.uploader
import cloudinary
import fitz # PyMuPDF
from config.settings import settings

router = APIRouter(prefix="/documents", tags=["Documents"])

# Configure cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True
)

MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    file_bytes = await file.read()
    file_size = len(file_bytes)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max size is 10MB")
        
    # Upload to Cloudinary
    try:
        upload_result = cloudinary.uploader.upload(
            file_bytes,
            resource_type="raw",
            folder="quizzin/documents",
            filename=file.filename
        )
        file_url = upload_result.get("secure_url")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading to storage: {str(e)}")
        
    # Extract text with PyMuPDF
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text_content = ""
        for page in doc:
            text_content += page.get_text() + "\n"
            
        preview = text_content[:500] if text_content else ""
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text from PDF: {str(e)}")
        
    # Save to database
    db_document = Document(
        user_id=current_user.id,
        title=title,
        file_url=file_url,
        file_type="application/pdf",
        file_size=file_size,
        extracted_text=text_content,
        preview_text=preview
    )
    
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    return db_document
