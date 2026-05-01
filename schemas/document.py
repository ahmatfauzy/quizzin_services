from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DocumentResponse(BaseModel):
    id: int
    user_id: int
    title: str
    file_url: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    preview_text: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
