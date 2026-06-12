from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: int
    displayName: str
    division: str
    department: str
    fileName: str
    fileExt: str
    processed: bool