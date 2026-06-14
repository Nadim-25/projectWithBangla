import pdfplumber
from docx import Document as DocxDocument
import os

def extract_doc_text(file_path: str):
    import pypandoc

    text = pypandoc.convert_file(file_path, 'plain')
    return text

def extract_text_ocr(file_path: str) -> str:
    """OCR fallback for scanned/image-based PDFs using pypdfium2 + pytesseract."""
    import pypdfium2 as pdfium
    import pytesseract

    text = ""
    pdf = pdfium.PdfDocument(file_path)
    for i in range(len(pdf)):
        page = pdf[i]
        # Scale 2x for better OCR accuracy
        bitmap = page.render(scale=2)
        pil_image = bitmap.to_pil()
        page_text = pytesseract.image_to_string(pil_image)
        if page_text:
            text += page_text + "\n"
    return text.strip()

def extract_text(file_path: str):
    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    try:
        # =========================
        # PDF
        # =========================
        if ext == ".pdf":
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"

            # Scanned PDF fallback — use OCR
            if not text.strip():
                text = extract_text_ocr(file_path)

        # =========================
        # DOCX
        # =========================
        elif ext == ".docx":
            doc = DocxDocument(file_path)
            for para in doc.paragraphs:
                if para.text:
                    text += para.text + "\n"

        # =========================
        # DOC (convert first)
        # =========================
        elif ext == ".doc":
            text = extract_doc_text(file_path)

        else:
            raise Exception("Unsupported file format")

    except Exception as e:
        raise Exception(f"Error extracting text: {str(e)}")

    return text.strip()

def chunk_by_paragraph(text, max_length=800):
    paragraphs = text.split("\n")
    chunks = []
    buffer = ""

    for p in paragraphs:
        p = p.strip()
        if not p:
            continue

        if len(buffer) + len(p) < max_length:
            buffer += p + "\n"
        else:
            chunks.append(buffer.strip())
            buffer = p + "\n"

    if buffer:
        chunks.append(buffer.strip())

    return chunks