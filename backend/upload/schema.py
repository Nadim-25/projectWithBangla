from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class DocumentResponse(BaseModel):
    id: int
    displayName: str
    division: str
    department: str
    fileName: str
    fileExt: str
    processed: bool
    chunk_strategy: Optional[str] = None
    subject: Optional[str] = None
    published_date: Optional[date] = None
    createdAt: Optional[datetime] = None
