import enum
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.database import Base


class DocumentStatus(str, enum.Enum):
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    original_filename = Column(String, nullable=True)
    cloudinary_url = Column(String, nullable=False)
    cloudinary_public_id = Column(String, nullable=True)
    total_pages = Column(Integer, nullable=True)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.processing)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="documents")
    chapters = relationship("Chapter", back_populates="document", cascade="all, delete-orphan")
