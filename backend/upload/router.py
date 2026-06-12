import os
import magic
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
from sqlmodel import Session, select
from datetime import datetime, timezone
from utils.database import get_database
from chatbot.model import Document
import uuid
from user.model import User
from utils.get_current_user import get_current_user
from upload.schema import DocumentResponse

upload_router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# =========================
# CONFIG
# =========================

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


# =========================
# VALIDATION FUNCTIONS
# =========================

def validate_file_content(file: UploadFile):
    header = file.file.read(2048)
    mime = magic.from_buffer(header, mime=True)
    file.file.seek(0)

    if mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Invalid file type: {mime}"
        )


def validate_file_size(file: UploadFile):
    size = 0
    chunk_size = 1024 * 1024  # 1MB

    while chunk := file.file.read(chunk_size):
        size += len(chunk)
        if size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large (max 10MB)"
            )

    file.file.seek(0)


def validate_file(file: UploadFile):
    validate_file_content(file)
    validate_file_size(file)


# =========================
# UPLOAD ENDPOINT
# =========================
@upload_router.post("/")
async def upload_file(
    file: UploadFile = File(...),
    displayName: str = Form(...),
    division: str = Form(...),
    department: str = Form(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_database)
):
    file_path = None

    try:
        # =========================
        # STEP 1: VALIDATION
        # =========================
        validate_file(file)

        # =========================
        # STEP 2: SAFE FILENAMES
        # =========================
        original_name = os.path.splitext(file.filename)[0]
        ext = os.path.splitext(file.filename)[1].lower()

        unique_name = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        # =========================
        # STEP 3: SAVE FILE
        # =========================
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)

        # =========================
        # STEP 4: SAVE DB RECORD
        # =========================
        new_doc = Document(
            userId=current_user.id,
            division=division,
            department=department,
            displayName=displayName,
            storedFileName=unique_name,
            fileName=original_name,
            processed=False,
            fileExt=ext,
            createdAt=datetime.now(timezone.utc)
        )

        session.add(new_doc)
        session.commit()
        session.refresh(new_doc)

        return {
            "message": "File uploaded successfully",
            "documentId": new_doc.id
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =========================
# DELETE ENDPOINT
# =========================
@upload_router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_database)
):
    statement = select(Document).where(
        Document.id == document_id,
        Document.userId == current_user.id
    )

    document = session.exec(statement).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    file_path = os.path.join(UPLOAD_DIR, document.storedFileName)

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error deleting file: {str(e)}"
            )

    session.delete(document)
    session.commit()

    return {
        "message": "Document deleted successfully",
        "deletedId": document_id
    }


# =========================
# GET ALL DOCS (current user only)
# =========================
@upload_router.get(
    "/getalldocs",
    response_model=list[DocumentResponse]
)
def getAllDocs(
    session: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    docs = session.exec(
        select(Document).where(Document.userId == current_user.id)
    ).all()

    return docs
