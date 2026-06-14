import tempfile
import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy import text as sql_text

from utils.database import get_database
from utils.storage import download_file, file_exists
from chatbot.model import Document
from chatbot.pdf import extract_text, chunk_by_paragraph
from chatbot.embeddings import create_embedding
from user.model import User
from utils.get_current_user import get_current_user

process_router = APIRouter()


@process_router.post("/{document_id}")
async def process_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_database),
):
    try:
        # =========================
        # 1. Get document record
        # =========================
        doc = session.exec(
            select(Document).where(
                Document.id == document_id,
                Document.userId == current_user.id,
            )
        ).first()

        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        if doc.processed:
            return {"message": "Already processed"}

        if not doc.storedFileName or not doc.fileExt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File metadata missing")

        # =========================
        # 2. Check file exists in R2
        # =========================
        if not file_exists(doc.storedFileName):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in storage. Please re-upload the document.",
            )

        # =========================
        # 3. Download from R2 → temp file
        # =========================
        file_bytes = download_file(doc.storedFileName)

        with tempfile.NamedTemporaryFile(suffix=doc.fileExt, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            # =========================
            # 4. Extract text
            # =========================
            text = extract_text(tmp_path)
        finally:
            os.unlink(tmp_path)

        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No text could be extracted from the document",
            )

        # =========================
        # 5. Chunk
        # =========================
        chunks = chunk_by_paragraph(text)

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Chunking failed",
            )

        # =========================
        # 6. Embeddings
        # =========================
        embeddings = create_embedding(chunks)

        if not embeddings:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Embedding generation failed",
            )

        # =========================
        # 7. Insert into DB
        # =========================
        for chunk, embedding in zip(chunks, embeddings):
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            session.execute(
                sql_text("""
                    INSERT INTO embeddings (document_id, content, embedding)
                    VALUES (:document_id, :content, :embedding)
                """),
                {"document_id": document_id, "content": chunk, "embedding": embedding_str},
            )

        # =========================
        # 8. Mark processed
        # =========================
        doc.processed = True
        session.add(doc)
        session.commit()

        return {"message": "Processing completed", "chunks": len(chunks)}

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
