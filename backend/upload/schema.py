from pydantic import BaseModel
from typing import Optional


class DocumentResponse(BaseModel):
    id: int
    displayName: str
    division: str
    department: str
    fileName: str
    fileExt: str
    processed: bool
    chunk_strategy: Optional[str] = None