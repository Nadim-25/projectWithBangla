import asyncio
import tempfile
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from sqlalchemy import text as sql_text

from utils.database import get_database, engine
from utils.storage import download_file, file_exists
from chatbot.model import Document
from chatbot.pdf import chunk_hierarchical
from chatbot.embeddings import create_embedding
from user.model import User
from utils.get_current_user import get_current_user

_log = logging.getLogger(__name__)
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
            # force=True: purge old embeddings and reset processed flag.
            # Must use engine.begin() (not the request session) so the DELETE
            # and reset are committed before new embeddings are inserted.
            # The request session is never committed (get_database just closes
            # it), so session.flush() alone would be silently rolled back.
            with engine.begin() as conn:
                conn.execute(
                    sql_text("DELETE FROM embeddings WHERE document_id = :doc_id"),
                    {"doc_id": document_id},
                )
                conn.execute(
                    sql_text("UPDATE document SET processed = false WHERE id = :doc_id"),
                    {"doc_id": document_id},
                )

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
            # Run in a thread so the async event loop is not blocked during
            # CPU-intensive OCR (can take 60-120 s for image-only PDFs).
            chunk_dicts = await asyncio.to_thread(
                chunk_hierarchical, tmp_path, strategy=doc.chunk_strategy
            )
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass  # Windows: pypdfium2 may still hold the handle; temp dir cleans up

        _log.info("[process] doc_id=%d chunks_after_filter=%d", document_id, len(chunk_dicts))

        if not chunk_dicts:
            _log.warning("[process] doc_id=%d — no usable content extracted", document_id)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No content could be extracted from the document",
            )

        # =========================
        # 5. Embeddings
        # =========================
        contents = [c["content"] for c in chunk_dicts]
        # Run in a thread so the event loop is free during the OpenAI API call.
        embeddings = await asyncio.to_thread(create_embedding, contents)

        if not embeddings:
            _log.error("[process] doc_id=%d — embedding generation returned empty", document_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Embedding generation failed",
            )

        _log.info("[process] doc_id=%d embeddings_returned=%d", document_id, len(embeddings))

        # =========================
        # 6. Insert into DB
        # =========================
        # Use fresh engine connections in batches rather than the request's
        # session, which may have its SSL connection dropped by PostgreSQL after
        # sitting idle for 60+ seconds during vision API / embedding calls above.
        _BATCH = 50
        pairs = list(zip(chunk_dicts, embeddings))
        for batch_start in range(0, len(pairs), _BATCH):
            batch = pairs[batch_start : batch_start + _BATCH]
            with engine.begin() as conn:
                for chunk_dict, emb in batch:
                    embedding_str = "[" + ",".join(map(str, emb)) + "]"
                    conn.execute(
                        sql_text("""
                            INSERT INTO embeddings
                                (document_id, content, embedding, chunk_type, chapter, section, page_num, subject)
                            VALUES
                                (:document_id, :content, :embedding, :chunk_type, :chapter, :section, :page_num, :subject)
                        """),
                        {
                            "document_id": document_id,
                            "content": chunk_dict["content"],
                            "embedding": embedding_str,
                            "chunk_type": chunk_dict["type"],
                            "chapter": chunk_dict["chapter"],
                            "section": chunk_dict["section"],
                            "page_num": chunk_dict["page"],
                            "subject": chunk_dict.get("subject") or "",
                        },
                    )

        _log.info("[process] doc_id=%d — all %d embeddings inserted", document_id, len(pairs))

        # =========================
        # 7. Mark processed
        # =========================
        with engine.begin() as conn:
            conn.execute(
                sql_text("UPDATE document SET processed = true WHERE id = :doc_id"),
                {"doc_id": document_id},
            )

        _log.info("[process] doc_id=%d — marked processed=true", document_id)

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
