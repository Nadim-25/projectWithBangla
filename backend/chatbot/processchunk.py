from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy import text as sql_text
import os

from utils.database import get_database
from chatbot.model import Document
from chatbot.pdf import extract_text, chunk_by_paragraph
from chatbot.embeddings import create_embedding
from user.model import User
from utils.get_current_user import get_current_user

process_router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")


@process_router.post("/{document_id}")
async def process_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_database)
):
    try:
        # =========================
        # 1. Get document
        # =========================
        statement = select(Document).where(
            Document.id == document_id,
            Document.userId == current_user.id
        )

        doc = session.exec(statement).first()

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        if doc.processed:
            return {
                "message": "Already processed"
            }

        # =========================
        # 2. Validate metadata
        # =========================
        if not doc.storedFileName or not doc.fileExt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File metadata missing"
            )

        file_path = os.path.join(UPLOAD_DIR, doc.storedFileName)

        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found on server"
            )

        # =========================
        # 3. Extract text
        # =========================
        text = extract_text(file_path)

        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No text found"
            )

        # =========================
        # 4. Chunk text
        # =========================
        chunks = chunk_by_paragraph(text)

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Chunking failed"
            )

        # =========================
        # 5. Create embeddings
        # =========================
        embeddings = create_embedding(chunks)

        if not embeddings:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Embedding failed"
            )

        # =========================
        # 6. Insert embeddings
        # =========================
        for chunk, embedding in zip(chunks, embeddings):

            embedding_str = "[" + ",".join(
                map(str, embedding)
            ) + "]"

            session.execute(
                sql_text("""
                    INSERT INTO embeddings
                    (document_id, content, embedding)
                    VALUES
                    (:document_id, :content, :embedding)
                """),
                {
                    "document_id": document_id,
                    "content": chunk,
                    "embedding": embedding_str,
                }
            )

        # =========================
        # 7. Mark processed
        # =========================
        doc.processed = True

        session.add(doc)
        session.commit()

        return {
            "message": "Processing completed",
            "chunks": len(chunks)
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
