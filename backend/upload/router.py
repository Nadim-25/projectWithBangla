import os
import magic
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
from typing import Optional
from sqlmodel import Session, select
from datetime import datetime, timezone
from utils.database import get_database
from utils.storage import upload_file, delete_file
from chatbot.model import Document, CHUNK_STRATEGIES
import uuid
from user.model import User
from utils.get_current_user import get_current_user
from upload.schema import DocumentResponse

upload_router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

MIME_TO_CONTENT_TYPE = {
    "application/pdf": "application/pdf",
    "application/msword": "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def validate_file_bytes(data: bytes):
    mime = magic.from_buffer(data[:2048], mime=True)
    if mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Invalid file type: {mime}",
        )
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (max 10 MB)",
        )
    return mime


# =========================
# UPLOAD
# =========================
@upload_router.post("/")
async def upload_file_endpoint(
    file: UploadFile = File(...),
    displayName: str = Form(...),
    division: str = Form(...),
    department: str = Form(...),
    chunk_strategy: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_database),
):
    if chunk_strategy and chunk_strategy not in CHUNK_STRATEGIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid chunk_strategy. Choose from: {', '.join(sorted(CHUNK_STRATEGIES))}",
        )

    try:
        data = await file.read()
        mime = validate_file_bytes(data)

        ext = os.path.splitext(file.filename)[1].lower()
        original_name = os.path.splitext(file.filename)[0]
        unique_name = f"{uuid.uuid4()}{ext}"

        upload_file(data, unique_name, MIME_TO_CONTENT_TYPE.get(mime, "application/octet-stream"))

        # Treat "auto" selection same as None (let chunker decide)
        resolved_strategy = None if chunk_strategy in (None, "auto") else chunk_strategy

        new_doc = Document(
            userId=current_user.id,
            division=division,
            department=department,
            displayName=displayName,
            storedFileName=unique_name,
            fileName=original_name,
            processed=False,
            fileExt=ext,
            chunk_strategy=resolved_strategy,
            createdAt=datetime.now(timezone.utc),
        )

        session.add(new_doc)
        session.commit()
        session.refresh(new_doc)

        return {"message": "File uploaded successfully", "documentId": new_doc.id}

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# =========================
# DELETE
# =========================
@upload_router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_database),
):
    document = session.exec(
        select(Document).where(
            Document.id == document_id,
            Document.userId == current_user.id,
        )
    ).first()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    delete_file(document.storedFileName)

    session.delete(document)
    session.commit()

    return {"message": "Document deleted successfully", "deletedId": document_id}


# =========================
# UPDATE STRATEGY
# =========================
@upload_router.patch("/{document_id}/strategy")
async def update_strategy(
    document_id: int,
    chunk_strategy: str = Form(...),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_database),
):
    if chunk_strategy not in CHUNK_STRATEGIES and chunk_strategy != "auto":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid chunk_strategy. Choose from: {', '.join(sorted(CHUNK_STRATEGIES))}",
        )

    doc = session.exec(
        select(Document).where(
            Document.id == document_id,
            Document.userId == current_user.id,
        )
    ).first()

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    doc.chunk_strategy = None if chunk_strategy == "auto" else chunk_strategy
    session.add(doc)
    session.commit()

    return {"message": "Strategy updated", "chunk_strategy": doc.chunk_strategy}


# =========================
# GET ALL DOCS
# =========================
@upload_router.get("/getalldocs", response_model=list[DocumentResponse])
def getAllDocs(
    session: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    docs = session.exec(
        select(Document).where(Document.userId == current_user.id)
    ).all()
    return docs
