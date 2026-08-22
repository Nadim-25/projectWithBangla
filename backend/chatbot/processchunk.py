import tempfile
import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy import text as sql_text

from utils.database import get_database
from utils.storage import download_file, file_exists
from chatbot.model import Document
from chatbot.pdf import chunk_hierarchical
from chatbot.embeddings import create_embedding
from user.model import User
from utils.get_current_user import get_current_user

process_router = APIRouter()


@process_router.post("/{document_id}")
async def process_document(
    document_id: int,
    force: bool = False,
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
            if not force:
                return {"message": "Already processed"}
            # force=True: purge old embeddings and reprocess
            session.execute(
                sql_text("DELETE FROM embeddings WHERE document_id = :doc_id"),
                {"doc_id": document_id},
            )
            doc.processed = False
            session.add(doc)
            session.flush()

        if not doc.storedFileName or not doc.fileExt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File metadata missing")

        # =========================
        # 2. Check file exists
        # =========================
        if not file_exists(doc.storedFileName):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found in storage. Please re-upload the document.",
            )

        # =========================
        # 3. Download to temp file
        # =========================
        file_bytes = download_file(doc.storedFileName)

        with tempfile.NamedTemporaryFile(suffix=doc.fileExt, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            # =========================
            # 4. Hierarchical chunking
            # =========================
            chunk_dicts = chunk_hierarchical(tmp_path, strategy=doc.chunk_strategy)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass  # Windows: pypdfium2 may still hold the handle; temp dir cleans up

        if not chunk_dicts:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No content could be extracted from the document",
            )

        # =========================
        # 5. Embeddings
        # =========================
        contents = [c["content"] for c in chunk_dicts]
        embeddings = create_embedding(contents)

        if not embeddings:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Embedding generation failed",
            )

        # =========================
        # 6. Insert into DB
        # =========================
        for chunk_dict, embedding in zip(chunk_dicts, embeddings):
            embedding_str = "[" + ",".join(map(str, embedding)) + "]"
            session.execute(
                sql_text("""
                    INSERT INTO embeddings
                        (document_id, content, embedding, chunk_type, chapter, section, page_num)
                    VALUES
                        (:document_id, :content, :embedding, :chunk_type, :chapter, :section, :page_num)
                """),
                {
                    "document_id": document_id,
                    "content": chunk_dict["content"],
                    "embedding": embedding_str,
                    "chunk_type": chunk_dict["type"],
                    "chapter": chunk_dict["chapter"],
                    "section": chunk_dict["section"],
                    "page_num": chunk_dict["page"],
                },
            )

        # =========================
        # 7. Mark processed
        # =========================
        doc.processed = True
        session.add(doc)
        session.commit()

        from collections import Counter
        type_counts = Counter(c["type"] for c in chunk_dicts)

        return {
            "message": "Processing completed",
            "chunks": len(chunk_dicts),
            "chunk_breakdown": dict(type_counts),
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
