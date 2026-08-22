"""
One-time script: force-reprocess all Bengali/CID-heavy PDFs with working OCR.

Run AFTER restarting the server (or run standalone):
    cd backend
    python reprocess_bengali.py
"""
import sys, io, os, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from sqlmodel import create_engine, Session, select
from sqlalchemy import text as sql_text
import user.model  # registers User mapper before Document relationship resolves
from chatbot.model import Document
from chatbot.pdf import chunk_hierarchical, _bijoy_garble_ratio, GARBLED_FONT_RE
from chatbot.embeddings import create_embedding
from utils.storage import download_file, file_exists
import pdfplumber

engine = create_engine(os.getenv("DATABASE_URL"))


def needs_ocr(file_path: str) -> bool:
    """Mirror the detection logic in _chunk_circular_bn (8-page sample, 1% threshold)."""
    try:
        with pdfplumber.open(file_path) as pdf:
            sample = "\n".join(
                (p.extract_text() or "") for p in pdf.pages[:min(8, len(pdf.pages))]
            )
        cid = sample.count("(cid:")
        greek = len(GARBLED_FONT_RE.findall(sample))
        safe = max(len(sample), 1)
        return cid >= 20 or greek / safe > 0.05 or _bijoy_garble_ratio(sample) > 0.01
    except Exception:
        return False


def reprocess(doc: Document, session: Session) -> str:
    if not file_exists(doc.storedFileName):
        return "SKIP (file missing)"

    file_bytes = download_file(doc.storedFileName)
    with tempfile.NamedTemporaryFile(suffix=doc.fileExt, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        if not needs_ocr(tmp_path):
            return "SKIP (no OCR needed)"

        # Delete old embeddings
        session.execute(
            sql_text("DELETE FROM embeddings WHERE document_id = :id"),
            {"id": doc.id},
        )
        doc.processed = False
        session.add(doc)
        session.flush()

        chunk_dicts = chunk_hierarchical(tmp_path, strategy=doc.chunk_strategy)
        if not chunk_dicts:
            return "FAIL (no chunks)"

        contents = [c["content"] for c in chunk_dicts]
        embeddings = create_embedding(contents)

        for chunk_dict, emb in zip(chunk_dicts, embeddings):
            emb_str = "[" + ",".join(map(str, emb)) + "]"
            session.execute(
                sql_text("""
                    INSERT INTO embeddings
                        (document_id, content, embedding, chunk_type, chapter, section, page_num)
                    VALUES
                        (:document_id, :content, :embedding, :chunk_type, :chapter, :section, :page_num)
                """),
                {
                    "document_id": doc.id,
                    "content": chunk_dict["content"],
                    "embedding": emb_str,
                    "chunk_type": chunk_dict["type"],
                    "chapter": chunk_dict["chapter"],
                    "section": chunk_dict["section"],
                    "page_num": chunk_dict["page"],
                },
            )

        doc.processed = True
        session.add(doc)
        session.commit()
        return "OK ({} chunks)".format(len(chunk_dicts))

    except Exception as e:
        session.rollback()
        return "ERROR: {}".format(e)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass  # Windows: file handle may still be held; temp dir cleans up on reboot


with Session(engine) as session:
    docs = session.exec(select(Document).where(Document.fileExt == ".pdf")).all()
    sys.stdout.write("Found {} PDF documents\n\n".format(len(docs)))
    for doc in docs:
        result = reprocess(doc, session)
        sys.stdout.write("[{}] {} (id={}) → {}\n".format(
            doc.displayName or doc.fileName, doc.storedFileName[:8], doc.id, result
        ))
        sys.stdout.flush()

sys.stdout.write("\nDone.\n")
