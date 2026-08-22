import pdfplumber
from docx import Document as DocxDocument
import os
import re
from collections import Counter

# Auto-locate Tesseract on Windows when it is not on PATH
def _configure_tesseract() -> None:
    try:
        import shutil
        import pytesseract as _pt
        if shutil.which(_pt.pytesseract.tesseract_cmd):
            return
        for candidate in [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]:
            if os.path.isfile(candidate):
                _pt.pytesseract.tesseract_cmd = candidate
                return
    except Exception:
        pass

_configure_tesseract()


# ── constants ─────────────────────────────────────────────────────────────────

# Chapter-based documents (long, English)
CHAPTER_RE = re.compile(r'^(Chapter\s+\d+\s*[:\-]?\s*.+)', re.IGNORECASE)
SECTION_RE = re.compile(r'^(\d+\.\d+(?:\.\d+)*)\s+(\S.{2,80})$')

# Bengali circulars
_BN_RANGE = 'ঀ-৿'
BN_CHAR_RE = re.compile(f'[{_BN_RANGE}]')
# Numbered Bengali sections: ২.৩ or ২.৩.১  (also matches ASCII digit variants)
BN_SECTION_RE = re.compile(
    r'^([০-৯\d]+(?:\.[০-৯\d]+)+)\s*[:\-–]?\s*(.{0,80})'
)
# Top-level Bengali section numbers without a sub-number: ১. or ০২।
# Checked BEFORE BN_SECTION_RE (which requires at least one decimal).
BN_TOPLEVEL_RE = re.compile(
    r'^([০-৯\d]{1,2})[।.]\s+(\S.{2,60})$'
)
# Bengali clause markers: ক) খ) গ) … also ক। form
# (\s|$) so markers that appear alone on their own line also match.
BN_CLAUSE_RE = re.compile(
    r'^([কখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহড়ঢ়য়ৎ][\)।])(\s|$)'
)

# English BB circular numbered paragraphs: 01. 02. 03. …
_EN_PARA_RE = re.compile(r'^(0?[1-9]\d?)\.\s+(.{0,80})')
# Garbled font-substitution detector: Greek (U+0370–U+03FF) and Cyrillic
# (U+0400–U+04FF) characters that appear when pdfplumber can't decode a
# Bengali PDF's custom font map.  A ratio > 5 % of total chars means the
# text is garbled and the document must be OCR-processed.
GARBLED_FONT_RE = re.compile(r'[Ͱ-ϿЀ-ӿ]')

# Bijoy/SutonnyMJ Latin-encoding markers: † (U+2020) and ‡ (U+2021) are
# assigned to Bengali characters in the Bijoy ASCII font layout. These
# typographic dagger symbols almost never appear in genuine English text,
# so a ratio > 0.5 % reliably flags a Bijoy-encoded Bengali PDF that must
# be OCR-processed to recover clean Unicode output.
BIJOY_LATIN_RE = re.compile(r'[†‡]')

# Bijoy/SutonnyMJ-encoded PDFs decode to wrong Bengali codepoints: dependent
# vowel signs (া ি ী ু ূ ৃ ে ৈ ো ৌ ্) appear at word-starts, which is
# impossible in well-formed Unicode Bengali (they must follow a consonant).
_BN_DEP_VOWELS = frozenset('ািীুূৃৄ'
                            'েৈোৌ্')

# ASCII digit → Bengali digit translation table.
# Tesseract ben+eng often emits ASCII 0-9 where the source document has Bengali
# digits ০-৯. Bengali circulars use Bengali numerals exclusively for dates,
# section numbers, and percentages, so converting all ASCII digits is safe.
# English acronyms (CMSME, SMESPD, ADR, IDR …) contain no digits and are
# unaffected.
_ASCII_TO_BN_DIGIT = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')

# Bijoy-encoded PDFs store digit characters as ASCII in the PDF stream, so
# pdfplumber extracts "4%" correctly even when Bengali text is garbled.
# Tesseract OCR reads the rendered Bijoy font glyph instead and misreads ৪
# (four) as 8, ৩ as 8, etc. _normalize_ocr_bn then promotes the wrong ASCII
# digit to a wrong Bengali digit (e.g. "8" → "৮").
# The patterns below are used by _patch_ocr_percentages to correct this.
_BN_TO_ASCII_DIGIT = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')
# Matches percentages with ASCII or Bengali digits (pdfplumber may give either)
_PLUMBER_PCT_RE = re.compile(r'([\d০-৯]+(?:[.,][\d০-৯]+)?)\s*%')
# Matches percentages with Bengali digits only (OCR output after _normalize_ocr_bn)
_OCR_PCT_RE     = re.compile(r'([০-৯]+(?:[.,][০-৯]+)?)\s*%')
# Matches ASCII-only digit percentages — used on RAW Tesseract output before normalization
_ASCII_PCT_RE   = re.compile(r'(\d+(?:[.,]\d+)?)\s*%')

# Bengali month names used to anchor date-context letter→digit fixes.
_BN_MONTH_PAT = (
    'জানুয়ারি|ফেব্রুয়ারি|মার্চ|এপ্রিল|মে|জুন|'
    'জুলাই|আগস্ট|সেপ্টেম্বর|অক্টোবর|নভেম্বর|ডিসেম্বর'
)
# Matches a 1–2 char day token (digits OR look-alike letters) before a Bengali month.
# Only letter→digit substitution happens here — nowhere else — so English words
# like "be", "ob", "lb" are safe everywhere except immediately before a month name.
_DATE_FIX_RE = re.compile(r'\b([oOiIlLbBqQ0-9]{1,2})\s+(' + _BN_MONTH_PAT + r')\b')

# Letter→digit map applied ONLY within _DATE_FIX_RE matches:
#   o/O → 0   (oval shapes confused with zero)
#   i/I/l/L → 1  (thin strokes confused with one)
#   b/B → 8   (Bengali ৮ has two bumps; sometimes OCR'd as b/B)
#   q/Q → 9   (Bengali ৯ curl resembles q)
_DATE_LETTER_FIX = str.maketrans('oOiIlLbBqQ', '0011118899')


def _normalize_ocr_bn(text: str) -> str:
    """Post-process Tesseract ben+eng output for Bengali circulars.

    Step 1 — date-context letter fix:
      Correct day numbers immediately before Bengali month names where
      Tesseract misread digit glyphs as look-alike Latin letters.
      e.g.  "ob জুন ২০২৬"  →  "০৮ জুন ২০২৬"
      The letter→digit map is applied ONLY inside the date regex match
      so English words elsewhere are never touched.

    Step 2 — global ASCII digit normalization:
      Convert all remaining ASCII 0-9 to Bengali ০-৯.
      e.g.  "নং-04"  →  "নং-০৪"
    """
    def _fix_day(m: re.Match) -> str:
        day = m.group(1).translate(_DATE_LETTER_FIX).translate(_ASCII_TO_BN_DIGIT)
        return day + ' ' + m.group(2)

    text = _DATE_FIX_RE.sub(_fix_day, text)
    return text.translate(_ASCII_TO_BN_DIGIT)


def _patch_ocr_pct_ascii(raw_ocr: str, plumber_text: str) -> str:
    """
    Fix percentage digit errors in RAW Tesseract output BEFORE _normalize_ocr_bn.

    Tesseract (ben+eng) outputs ASCII digits: it emits '8' for the Bengali
    ৪ glyph because the shapes are visually similar, and pdfplumber reads the
    PDF stream's ASCII '4' correctly from Bijoy-encoded documents.

    Working in ASCII digit space avoids Bengali normalisation ambiguity:
    compare pdfplumber's ASCII '4' directly against Tesseract's ASCII '8'.
    After correction here, _normalize_ocr_bn converts '4' → '৪' correctly.

    Strategy — Counter diff, tolerates multi-percentage pages:
    - Count each digit% in pdfplumber (trusted) and in raw OCR.
    - If there is exactly one digit value in OCR that exceeds its pdfplumber
      count AND exactly one digit value that is under-represented, replace the
      last (excess count) occurrences of the wrong value with the correct one.
      The last-occurrence heuristic works because Bangladesh Bank circulars
      state the directive cap at the end of the paragraph, after describing
      the problem (e.g. "current spreads are 8% … please keep within 4%").
    - If the Counter diff is ambiguous, fall back to set-based single-swap.
    """
    try:
        if not plumber_text:
            return raw_ocr

        plumber_c: Counter[str] = Counter(m.group(1) for m in _ASCII_PCT_RE.finditer(plumber_text))
        if not plumber_c:
            return raw_ocr

        ocr_pct_all = list(_ASCII_PCT_RE.finditer(raw_ocr))
        if not ocr_pct_all:
            return raw_ocr

        ocr_c: Counter[str] = Counter(m.group(1) for m in ocr_pct_all)

        extra   = {k: ocr_c[k] - plumber_c[k] for k in ocr_c if ocr_c[k] > plumber_c[k]}
        missing = {k: plumber_c[k] - ocr_c[k] for k in plumber_c if plumber_c[k] > ocr_c[k]}

        if len(extra) == 1 and len(missing) == 1:
            wrong   = next(iter(extra))    # e.g. "8"
            correct = next(iter(missing))  # e.g. "4"
            n = extra[wrong]
            positions = [(m.start(), m.end())
                         for m in re.finditer(re.escape(wrong) + r'\s*%', raw_ocr)]
            if len(positions) >= n:
                chars = list(raw_ocr)
                for s, e in reversed(positions[-n:]):
                    chars[s:e] = list(correct + '%')
                return ''.join(chars)

        # Fallback: simple set-based swap (single unambiguous pair)
        extra_s   = set(ocr_c) - set(plumber_c)
        missing_s = set(plumber_c) - set(ocr_c)
        if len(extra_s) == 1 and len(missing_s) == 1:
            wrong   = next(iter(extra_s))
            correct = next(iter(missing_s))
            return re.sub(re.escape(wrong) + r'\s*%', correct + '%', raw_ocr)

        return raw_ocr
    except Exception:
        return raw_ocr


def _patch_ocr_percentages(ocr_text: str, plumber_text: str) -> str:
    """
    Correct percentage values in OCR text using pdfplumber-extracted digits.

    In Bijoy-encoded PDFs the digit characters are ASCII in the PDF stream, so
    pdfplumber reads "4%" correctly even when Bengali text is garbled. Tesseract
    OCR reads the rendered Bijoy font glyph and misreads ৪ (four) as 8.
    _normalize_ocr_bn then converts "8" → "৮", so the chunk says "৮%" instead
    of "৪%".

    Strategy — set-based diff, tolerates page-level count mismatches:
      1. Build the set of valid Bengali percentages from pdfplumber.
      2. Find OCR percentages not in the valid set (discrepant) and valid
         percentages absent from OCR (missing).
      3. If there is exactly one discrepant/missing pair, replace all
         occurrences of the discrepant value with the missing (correct) one.
         If the pair is ambiguous (more than one mismatch on either side),
         leave the text unchanged to avoid wrong substitutions.
    """
    try:
        def _to_bn_pct(digits: str) -> str:
            """Normalise digit string (ASCII or Bengali) to Bengali + '%'."""
            ascii_digits = digits.translate(_BN_TO_ASCII_DIGIT)
            return ascii_digits.translate(_ASCII_TO_BN_DIGIT) + '%'

        # Valid percentages from pdfplumber, normalised to Bengali
        plumber_bn: set[str] = set()
        for m in _PLUMBER_PCT_RE.finditer(plumber_text):
            plumber_bn.add(_to_bn_pct(m.group(1)))

        if not plumber_bn:
            return ocr_text

        # Percentages found in OCR text (Bengali digits from _normalize_ocr_bn)
        ocr_pct_matches = list(_OCR_PCT_RE.finditer(ocr_text))
        if not ocr_pct_matches:
            return ocr_text

        ocr_bn_set: set[str] = {m.group(1) + '%' for m in ocr_pct_matches}

        # Discrepant: in OCR but NOT confirmed by pdfplumber
        discrepant = ocr_bn_set - plumber_bn
        # Missing: pdfplumber says it exists but OCR didn't produce it
        missing = plumber_bn - ocr_bn_set

        # Counter diff: handles pages where document has both "4%" and "8%"
        # and OCR shows two "৮%"s (one correctly read, one misread from ৪).
        plumber_c: Counter[str] = Counter()
        for bn_pct in plumber_bn:
            plumber_c[bn_pct] += 1
        # Re-build plumber_c from the full finditer for accurate counts
        plumber_c = Counter()
        for m in _PLUMBER_PCT_RE.finditer(plumber_text):
            plumber_c[_to_bn_pct(m.group(1))] += 1

        ocr_c: Counter[str] = Counter(m.group(1) + '%' for m in ocr_pct_matches)

        extra_c   = {k: ocr_c[k] - plumber_c[k] for k in ocr_c if ocr_c[k] > plumber_c[k]}
        missing_c = {k: plumber_c[k] - ocr_c[k] for k in plumber_c if plumber_c[k] > ocr_c[k]}

        if len(extra_c) == 1 and len(missing_c) == 1:
            wrong   = next(iter(extra_c))
            correct = next(iter(missing_c))
            n = extra_c[wrong]
            positions = [(m.start(), m.end())
                         for m in re.finditer(re.escape(wrong.rstrip('%')) + r'\s*%', ocr_text)]
            if len(positions) >= n:
                chars = list(ocr_text)
                for s, e in reversed(positions[-n:]):
                    chars[s:e] = list(correct)
                return ''.join(chars)

        # Simple set-based fallback for the single unambiguous swap
        if not discrepant or not missing or len(discrepant) != 1 or len(missing) != 1:
            return ocr_text

        wrong   = next(iter(discrepant))
        correct = next(iter(missing))
        wrong_digits = re.escape(wrong.rstrip('%'))
        return re.sub(wrong_digits + r'\s*%', correct, ocr_text)

    except Exception:
        return ocr_text  # never corrupt the text on unexpected errors


def _bijoy_garble_ratio(text: str) -> float:
    """Return fraction of whitespace-separated tokens that show Bijoy visual-order
    encoding. Two signals are checked:

    1. Word starts with a dependent vowel sign (ি, ে, া …) — impossible in
       logical Unicode Bengali where vowel signs always follow a consonant.
       e.g.  িবষয় (visual) → বিষয় (logical)

    2. Two consecutive dependent vowel signs anywhere inside a word — also
       impossible in logical Unicode. Catches mid-word Bijoy errors like
       সুিবধা (ু+ি consecutive) which start with a consonant and evade signal 1.
    """
    words = text.split()
    if not words:
        return 0.0
    garble = 0
    for w in words:
        if not w:
            continue
        if w[0] in _BN_DEP_VOWELS:
            garble += 1
        elif any(
            w[i] in _BN_DEP_VOWELS and w[i - 1] in _BN_DEP_VOWELS
            for i in range(1, len(w))
        ):
            # Two adjacent matras: e.g. ু immediately followed by ি.
            # In correct Unicode this never happens without an intervening consonant.
            garble += 1
    return garble / len(words)


def _bijoy_latin_ratio(text: str) -> float:
    """Fraction of characters that are Bijoy ASCII font markers (†, ‡).
    Values above ~0.5 % indicate a Bijoy-encoded Bengali PDF."""
    if not text:
        return 0.0
    return len(BIJOY_LATIN_RE.findall(text)) / len(text)


# Chunk size limits
MAX_NARRATIVE_CHARS = 2400   # chapter_doc / English circular narrative
MAX_BN_CHARS        = 1500   # Bengali section/clause blocks
OVERLAP_CHARS       = 200

# Maximum header lines extracted from page 1 and repeated in continuation chunks
# for short (≤ 3 page) circulars.
_CIRCULAR_HEADER_LINES = 8


# ── text extraction ───────────────────────────────────────────────────────────

def extract_doc_text(file_path: str):
    import pypandoc
    return pypandoc.convert_file(file_path, 'plain')


def extract_text_ocr(file_path: str, lang: str = 'eng') -> str:
    import pypdfium2 as pdfium
    import pytesseract

    text = ""
    pdf = pdfium.PdfDocument(file_path)
    try:
        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=2)
            pil_image = bitmap.to_pil()
            page_text = pytesseract.image_to_string(pil_image, lang=lang)
            if page_text:
                text += page_text + "\n"
    finally:
        pdf.close()
    return text.strip()


def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    text = ""

    try:
        if ext == ".pdf":
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
            if not text.strip():
                text = extract_text_ocr(file_path)

        elif ext == ".docx":
            doc = DocxDocument(file_path)
            for para in doc.paragraphs:
                if para.text:
                    text += para.text + "\n"

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


# ── shared helpers ────────────────────────────────────────────────────────────

def _serialize_table(table: list, section_title: str = "") -> str:
    if not table:
        return ""
    lines = []
    if section_title:
        lines.append(f"[TABLE: {section_title}]")
    header = [str(c).strip().replace("\n", " ") if c else "" for c in table[0]]
    lines.append(" | ".join(header))
    lines.append("-" * 60)
    for row in table[1:]:
        if row:
            cells = [str(c).strip().replace("\n", " ") if c else "" for c in row]
            if any(cells):
                lines.append(" | ".join(cells))
    return "\n".join(lines)


def _split_serialized_table(serialized: str, max_chars: int) -> list[str]:
    """
    Split a serialized table string into sub-strings each under max_chars,
    repeating the header (first 2 rows) in every continuation part.
    """
    rows = serialized.split("\n")
    if len(serialized) <= max_chars:
        return [serialized]
    header_rows = rows[:2]
    header_str = "\n".join(header_rows)
    parts = []
    sub_buf = header_str
    for row in rows[2:]:
        candidate = sub_buf + "\n" + row
        if len(candidate) > max_chars and len(sub_buf) > len(header_str):
            parts.append(sub_buf)
            sub_buf = header_str + "\n" + row
        else:
            sub_buf = candidate
    if sub_buf.strip() and sub_buf.strip() != header_str.strip():
        parts.append(sub_buf)
    return parts or [serialized]


def _make_prefix(chapter: str, section_num: str, section_title: str) -> str:
    parts = []
    if chapter:
        parts.append(chapter)
    if section_num and section_title:
        parts.append(f"Section {section_num}: {section_title}")
    elif section_num:
        parts.append(f"Section {section_num}")
    return "[" + " | ".join(parts) + "]\n" if parts else ""


def _flush_narrative(
    buf: str,
    chapter: str,
    section_num: str,
    section_title: str,
    page: int,
    chunks: list,
    overlap: str,
) -> str:
    text = buf.strip()
    if not text:
        return overlap
    prefix = _make_prefix(chapter, section_num, section_title)
    full_text = (overlap.strip() + " " + text).strip() if overlap.strip() else text
    chunks.append({
        "content": prefix + full_text,
        "type": "narrative",
        "chapter": chapter,
        "section": section_num,
        "page": page,
    })
    sentences = re.split(r'(?<=[.!?])\s+', text)
    tail = " ".join(sentences[-2:]) if len(sentences) >= 2 else text
    return tail[-OVERLAP_CHARS:]


# ── page-wise chunkers for short circulars (≤ 3 pages) ────────────────────────

def _extract_circular_header(page1_text: str, max_lines: int = _CIRCULAR_HEADER_LINES) -> str:
    """Return the first max_lines non-empty lines from page 1 of a circular.

    These lines capture the letterhead, circular number, date, addressee,
    and salutation — enough to re-identify the document on every page chunk.
    """
    header_lines = []
    for line in page1_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        header_lines.append(line)
        if len(header_lines) >= max_lines:
            break
    return "\n".join(header_lines)


def _chunk_bn_page_wise(
    page_texts: list[dict],
    heading_info: "dict | None",
    circular_ref: str,
    page_tables: dict,
) -> list:
    """
    Page-wise chunker for short Bengali circulars (≤ 8 pages).

    Exactly one chunk per page. Pages 2+ carry the page-1 header block
    (letterhead + addressee + salutation) so every chunk is self-contained.
    Tables are NOT emitted as separate chunks: for Bijoy-encoded PDFs the
    pdfplumber table data is garbled Latin anyway, and the OCR text already
    covers the full page visually.
    """
    chunks: list = []
    page1_text = page_texts[0]["text"] if page_texts else ""
    header = _extract_circular_header(page1_text)

    def _prefix(page_num: int) -> tuple[str, str]:
        if heading_info:
            meta = heading_info["chapter"]
            return f"[{meta} | Page {page_num}]\nবিষয়: {heading_info['subject']}\n", meta
        if circular_ref:
            return f"[{circular_ref} | Page {page_num}]\n", circular_ref
        return f"[Page {page_num}]\n", ""

    for page_info in page_texts:
        page_num = page_info["page"]
        text = page_info["text"].strip()
        if not text:
            continue

        if page_num > 1 and header:
            body = f"[Circular Header — Page 1]\n{header}\n---\n[Page {page_num} Content]\n{text}"
        else:
            body = text

        prefix, chapter_val = _prefix(page_num)
        chunks.append({
            "content": prefix + body,
            "type": "circular_page",
            "chapter": chapter_val,
            "section": "",
            "page": page_num,
        })

    return chunks


def _chunk_en_page_wise(
    page_texts: list[dict],
    circular_ref: str,
    page_tables: dict,
) -> list:
    """
    Page-wise chunker for short English circulars (≤ 8 pages).

    Exactly one chunk per page. Pages 2+ carry the page-1 header block so
    every chunk is self-contained. Any tables on a page are serialized and
    appended to that page's chunk body rather than emitted separately.
    """
    chunks: list = []
    page1_text = page_texts[0]["text"] if page_texts else ""
    header = _extract_circular_header(page1_text)

    def _prefix(page_num: int) -> tuple[str, str]:
        if circular_ref:
            return f"[{circular_ref} | Page {page_num}]\n", circular_ref
        return f"[Page {page_num}]\n", ""

    for page_info in page_texts:
        page_num = page_info["page"]
        text = page_info["text"].strip()
        if not text:
            continue

        if page_num > 1 and header:
            base = f"[Circular Header — Page 1]\n{header}\n---\n[Page {page_num} Content]\n{text}"
        else:
            base = text

        # Inline any tables into the page body — one chunk per page.
        table_parts = [
            _serialize_table(tbl, "")
            for tbl in page_tables.get(page_num, [])
            if _serialize_table(tbl, "").strip()
        ]
        body = base + ("\n\n" + "\n\n".join(table_parts) if table_parts else "")

        prefix, chapter_val = _prefix(page_num)
        chunks.append({
            "content": prefix + body,
            "type": "circular_page",
            "chapter": chapter_val,
            "section": "",
            "page": page_num,
        })

    return chunks


# ── document type detection ───────────────────────────────────────────────────

def _detect_doc_type(file_path: str) -> str:
    """
    Classifies a PDF as one of four types:

    - 'circular_bn'  Bengali bank circular — Bengali chars or heavy CID encoding
    - 'circular_en'  Short English BB circular — numbered paragraphs, no Bengali
    - 'chapter_doc'  Long policy/manual with Chapter / X.Y.Z section structure
    """
    try:
        with pdfplumber.open(file_path) as pdf:
            n_pages = len(pdf.pages)
            bengali_chars = 0
            garbled_chars = 0
            bijoy_latin_chars = 0
            total_chars = 0
            cid_seqs = 0
            has_chapter = False

            for page in pdf.pages[:min(5, n_pages)]:
                text = page.extract_text() or ""
                total_chars += len(text)
                bengali_chars += len(BN_CHAR_RE.findall(text))
                garbled_chars += len(GARBLED_FONT_RE.findall(text))
                bijoy_latin_chars += len(BIJOY_LATIN_RE.findall(text))
                cid_seqs += text.count("(cid:")
                if CHAPTER_RE.search(text):
                    has_chapter = True
    except Exception:
        return 'chapter_doc'

    safe_chars = max(total_chars, 1)
    # Pure image scan: pdfplumber extracted no text at all → must use OCR
    if total_chars == 0:
        return 'circular_bn'
    # Bengali ratio > 15% OR ≥ 20 CID sequences per page → Bengali circular
    if bengali_chars / safe_chars > 0.15 or cid_seqs / max(n_pages, 1) >= 20:
        return 'circular_bn'
    # Greek/Cyrillic font-substitution artifacts > 5% → garbled Bengali PDF,
    # must OCR. pdfplumber maps unmapped Bengali glyphs to Greek/Cyrillic
    # codepoints in some PDFs instead of emitting (cid:NNN) sequences.
    if garbled_chars / safe_chars > 0.05:
        return 'circular_bn'
    # Bijoy ASCII font encoding: dagger characters (†, ‡) used as Bengali
    # glyph substitutes appear at > 0.5 % of total chars.
    if bijoy_latin_chars / safe_chars > 0.005:
        return 'circular_bn'
    # Fallback: detect Bengali section numbering (e.g. ১.৬, ২.৩.১) even when
    # the overall Bengali char ratio is low (e.g. mixed Bengali/English cover pages).
    try:
        with pdfplumber.open(file_path) as pdf:
            sample = "\n".join(
                (p.extract_text() or "") for p in pdf.pages[:min(10, len(pdf.pages))]
            )
        if BN_SECTION_RE.search(sample):
            return 'circular_bn'
    except Exception:
        pass
    if has_chapter or n_pages > 15:
        return 'chapter_doc'
    # Short English circular (no Bengali, no chapter headings, ≤ 15 pages)
    return 'circular_en'


# ── chapter_doc chunker ───────────────────────────────────────────────────────

def _chunk_pdf(file_path: str) -> list:
    """
    Hierarchical chunker for chapter-structured policy documents.
    - Chapter / X.Y.Z headings drive split boundaries.
    - Tables are serialized as atomic chunks.
    - Narrative carries overlap context across splits.
    """
    chunks: list = []
    chapter = ""
    section_num = ""
    section_title = ""
    narrative_buf = ""
    overlap = ""
    last_page = 1

    with pdfplumber.open(file_path) as pdf:
        last_page = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages, start=1):
            page_table_objs = page.find_tables()
            table_bboxes = [t.bbox for t in page_table_objs]

            if table_bboxes:
                def _outside(obj, bboxes=table_bboxes):
                    for x0, top, x1, bottom in bboxes:
                        if (obj.get("x0", 0) >= x0 - 2
                                and obj.get("x1", 0) <= x1 + 2
                                and obj.get("top", 0) >= top - 2
                                and obj.get("bottom", 0) <= bottom + 2):
                            return False
                    return True
                page_text = page.filter(_outside).extract_text() or ""
            else:
                page_text = page.extract_text() or ""

            for line in page_text.split("\n"):
                line = line.strip()
                if not line:
                    continue

                ch_match = CHAPTER_RE.match(line)
                sec_match = SECTION_RE.match(line)

                if ch_match:
                    overlap = _flush_narrative(
                        narrative_buf, chapter, section_num, section_title,
                        page_num, chunks, overlap,
                    )
                    narrative_buf = ""
                    # Strip TOC dot-leaders: "Chapter 1: PRELIMINARY ...... 5" → clean
                    chapter = re.sub(r'\s*\.{2,}[\s\d]*$', '', ch_match.group(1)).strip()
                    section_num = ""
                    section_title = ""

                elif sec_match:
                    overlap = _flush_narrative(
                        narrative_buf, chapter, section_num, section_title,
                        page_num, chunks, overlap,
                    )
                    narrative_buf = ""
                    section_num = sec_match.group(1)
                    # Strip TOC dot-leaders: "GUIDELINE FOR CAR LOAN ..... 33" → clean
                    section_title = re.sub(r'\s*\.{2,}[\s\d]*$', '', sec_match.group(2)).strip()

                else:
                    narrative_buf += line + " "
                    if len(narrative_buf) > MAX_NARRATIVE_CHARS:
                        overlap = _flush_narrative(
                            narrative_buf, chapter, section_num, section_title,
                            page_num, chunks, overlap,
                        )
                        narrative_buf = ""

            for table_obj in page_table_objs:
                table_data = table_obj.extract()
                if not table_data or len(table_data) < 2:
                    continue
                if narrative_buf.strip():
                    overlap = _flush_narrative(
                        narrative_buf, chapter, section_num, section_title,
                        page_num, chunks, overlap,
                    )
                    narrative_buf = ""
                    overlap = ""

                prefix = _make_prefix(chapter, section_num, section_title)
                serialized = _serialize_table(table_data, section_title)
                for part in _split_serialized_table(serialized, MAX_NARRATIVE_CHARS):
                    chunks.append({
                        "content": prefix + part,
                        "type": "table",
                        "chapter": chapter,
                        "section": section_num,
                        "page": page_num,
                    })

    if narrative_buf.strip():
        _flush_narrative(
            narrative_buf, chapter, section_num, section_title,
            last_page, chunks, overlap,
        )

    return chunks


# ── English circular chunker ──────────────────────────────────────────────────

def _chunk_circular_en(file_path: str) -> list:
    """
    Chunker for short English BB circulars (FEPD / BRPD / DOS circular letters).

    Strategy:
    - Extract text via pdfplumber (digital English, no OCR needed).
    - Pull circular identity from page 1 (department + circular number).
    - Split on numbered top-level paragraphs: 01., 02., 03. …
    - Sub-clauses (a), (b) … and nested (i), (ii) … stay inside their parent
      paragraph chunk — they are too short to retrieve independently.
    - Tables are serialized as separate circular_table chunks.
    """
    chunks: list = []

    with pdfplumber.open(file_path) as pdf:
        page_texts = [
            {"page": i + 1, "text": (page.extract_text() or "")}
            for i, page in enumerate(pdf.pages)
        ]
        page_tables: dict[int, list] = {}
        for pg_idx, page in enumerate(pdf.pages, 1):
            tbls = [
                tbl.extract()
                for tbl in page.find_tables()
                if tbl.extract() and len(tbl.extract()) >= 2
            ]
            if tbls:
                page_tables[pg_idx] = tbls

    first_text = page_texts[0]["text"] if page_texts else ""
    circular_ref = ""
    circ_match = re.search(
        r'(?:Circular\s+(?:No\.?|Letter)[^\n]{0,60}'
        r'|(?:FEPD|BRPD|DOS|SMESPD|GBCSRD|BFID|CIB|DBRT)[^\n]{0,60})',
        first_text, re.IGNORECASE,
    )
    if circ_match:
        circular_ref = circ_match.group(0).strip()[:80]

    # Short circulars (≤ 8 pages): chunk page-wise, repeating the page-1
    # header in every continuation page so each chunk is self-contained.
    if len(page_texts) <= 8:
        return _chunk_en_page_wise(page_texts, circular_ref, page_tables)

    current_para = ""
    current_title = ""
    buf = ""
    last_page = page_texts[-1]["page"] if page_texts else 1

    def _en_prefix(para: str, title: str) -> tuple[str, str]:
        parts = [p for p in [
            circular_ref,
            f"Para {para}" if para else "",
        ] if p]
        meta = " | ".join(parts)
        return (f"[{meta}]\n" if meta else ""), circular_ref

    def _flush_en(buf_text: str, para: str, title: str, pg: int) -> None:
        text = buf_text.strip()
        if not text:
            return
        prefix, chapter_val = _en_prefix(para, title)
        chunks.append({
            "content": prefix + text,
            "type": "circular_section" if para else "circular_narrative",
            "chapter": chapter_val,
            "section": para,
            "page": pg,
        })

    def _emit_tables_en(pg: int) -> None:
        for table_data in page_tables.get(pg, []):
            prefix, chapter_val = _en_prefix(current_para, current_title)
            serialized = _serialize_table(table_data, current_title)
            if not serialized.strip():
                continue
            for part in _split_serialized_table(serialized, MAX_NARRATIVE_CHARS):
                chunks.append({
                    "content": prefix + part,
                    "type": "circular_table",
                    "chapter": chapter_val,
                    "section": current_para,
                    "page": pg,
                })

    for page_info in page_texts:
        page_num = page_info["page"]
        for line in page_info["text"].split("\n"):
            line = line.strip()
            if not line:
                continue
            para_match = _EN_PARA_RE.match(line)
            if para_match:
                _flush_en(buf, current_para, current_title, page_num)
                buf = ""
                current_para = para_match.group(1).lstrip("0") or "0"
                current_title = para_match.group(2).strip()[:60]
                buf = line + "\n"
            else:
                buf += line + "\n"
                if len(buf) > MAX_NARRATIVE_CHARS:
                    _flush_en(buf, current_para, current_title, page_num)
                    buf = ""
        _emit_tables_en(page_num)

    if buf.strip():
        _flush_en(buf, current_para, current_title, last_page)

    return chunks


# ── Bengali circular chunker ──────────────────────────────────────────────────

_BN_CID_RE = re.compile(r'\(cid:\d+\)')

# Maps patterns found in the circular_no field → canonical department code
_DEPT_PATTERNS: list[tuple[str, str]] = [
    (r'এসএমইএস|smespd',              'SMESPD'),
    (r'বিআরপিডি|ব্রপিড|brpd',        'BRPD'),
    (r'ডিওএস|dos\b',                  'DOS'),
    (r'এফইপিড|fepd',                  'FEPD'),
    (r'বিএফআইডি|bfid',                'BFID'),
    (r'জিবিসিএসআরডি|gbcsrd',          'GBCSRD'),
    (r'সিআইবি|cib\b',                 'CIB'),
    (r'ডিবিআরটি|dbrt',                'DBRT'),
]


def _parse_bn_circular_heading(first_line: str) -> dict | None:
    """
    Parse the user-added heading line of a BB circular.

    Expected format (comma-separated, added as page-1 line 1):
      "Subject, DeptCircularNo, IssueDate"
      e.g. "CMSME খাতে চলিত মূলধন পুনঃ অর্থায়ন তহবিল প্রসঙ্গে,
            এসএমইএসপিডি সার্কুলার নং-০৪, ০৮ জুন ২০২৬"

    Returns a dict {subject, circular_no, department, issue_date, chapter}
    where chapter = "circular_no | department | issue_date" for DB storage.
    Returns None if the line doesn't match the expected pattern.
    """
    # Strip CID artifacts so parsing works on pdfplumber text too
    line = _BN_CID_RE.sub('', first_line).strip()
    parts = [p.strip() for p in line.split(',')]
    if len(parts) < 3:
        return None

    circular_no = parts[1].strip()
    # Second part must look like a circular reference
    if not re.search(r'নং|No\.|circular|সাকু', circular_no, re.IGNORECASE):
        return None

    subject    = parts[0].strip()
    issue_date = ', '.join(parts[2:]).strip()

    department = ""
    for pattern, code in _DEPT_PATTERNS:
        if re.search(pattern, circular_no, re.IGNORECASE):
            department = code
            break

    chapter = ' | '.join(filter(None, [circular_no, department, issue_date]))
    return {
        'subject':     subject,
        'circular_no': circular_no,
        'department':  department,
        'issue_date':  issue_date,
        'chapter':     chapter,
    }


def _ocr_pages_bn(file_path: str, scale: float = 2.5) -> list[dict]:
    """
    OCR each page at high resolution using Tesseract with Bengali + English.
    Falls back to English-only if the Bengali language pack is unavailable.

    Config notes:
    --oem 3        use LSTM + legacy engine (most accurate for mixed script)
    --psm 6        assume a uniform block of text — prevents Tesseract from
                   treating English uppercase blocks (CMSME, SMESPD) as noise
    preserve_interword_spaces=1  keeps gaps between Bengali and English tokens
    """
    import pypdfium2 as pdfium
    import pytesseract

    _cfg = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'

    results = []
    pdf = pdfium.PdfDocument(file_path)
    try:
        for i in range(len(pdf)):
            page = pdf[i]
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()
            try:
                text = pytesseract.image_to_string(pil_image, lang='ben+eng', config=_cfg)
            except pytesseract.TesseractError:
                try:
                    text = pytesseract.image_to_string(pil_image, lang='ben', config=_cfg)
                except pytesseract.TesseractError:
                    text = pytesseract.image_to_string(pil_image, config=_cfg)
            results.append({"page": i + 1, "text": text.strip()})
    finally:
        pdf.close()
    return results


def _chunk_circular_bn(file_path: str) -> list:
    """
    Chunker for Bengali bank circulars (Bangladesh Bank / BB).

    Strategy:
    - If pdfplumber produces CID-heavy text (font not decoded), OCR the PDF
      with Tesseract ben+eng for clean Bengali Unicode output.
    - Split on numbered sections (২.৩, ২.৩.১) and Bengali clause letters (ক) খ)).
    - Each section/clause block is kept atomic; buffer flushes at MAX_BN_CHARS.
    - Tables are always extracted via pdfplumber (OCR gives flat text, no
      structure) and emitted as circular_table chunks anchored to the current
      section so retrieval can find rate/limit/criteria tables.
    - Circular reference (BRPD/SMESPD number) extracted from page 1 and
      prepended to every chunk so retrieval can filter by circular identity.
    """
    # Decide: native pdfplumber text vs OCR.
    # BB circulars have an English letterhead on pages 1-2, so Bijoy-garbled
    # Bengali text only appears from page 3 onwards — sample up to 8 pages
    # to catch documents where the body starts late.
    use_ocr = False
    n_pages = 0
    try:
        with pdfplumber.open(file_path) as pdf:
            n_pages = len(pdf.pages)
            sample_text = "\n".join(
                (p.extract_text() or "") for p in pdf.pages[:min(8, n_pages)]
            )
            # ≥ 20 CID sequences → font not decoded at all, use OCR
            if sample_text.count("(cid:") >= 20:
                use_ocr = True
            # Pure image scan: no text layer at all
            elif len(sample_text) == 0:
                use_ocr = True
            elif len(sample_text) > 0:
                # Greek/Cyrillic font-substitution artifacts > 5 %
                garbled = len(GARBLED_FONT_RE.findall(sample_text))
                if garbled / len(sample_text) > 0.05:
                    use_ocr = True
                # Bijoy/SutonnyMJ: Bengali codepoints in visual order.
                # Threshold lowered to 0.01 (1 %) because the English letterhead
                # on page 1 dilutes the ratio — even a small amount of visual-order
                # Bengali in the sample is enough to confirm Bijoy encoding.
                elif _bijoy_garble_ratio(sample_text) > 0.01:
                    use_ocr = True
                # Bijoy ASCII font: dagger/double-dagger markers (†, ‡) used as
                # Bengali glyph substitutes — these PDFs have no Unicode Bengali
                # at all and produce pure Latin gibberish without OCR.
                elif _bijoy_latin_ratio(sample_text) > 0.005:
                    use_ocr = True
    except Exception:
        use_ocr = True

    def _pdfplumber_pages(fp: str) -> list[dict]:
        # Strip (cid:NNN) sequences so the Bengali chars that DID decode
        # are clean when embedded — CID tokens are noise the model can't use.
        _cid = re.compile(r'\(cid:\d+\)')
        with pdfplumber.open(fp) as pdf:
            return [
                {"page": i + 1, "text": _cid.sub("", p.extract_text() or "").strip()}
                for i, p in enumerate(pdf.pages)
            ]

    if use_ocr:
        try:
            # Phase 1 — raw Tesseract output (ASCII digits, no Bengali normalization yet).
            # pdfplumber reads Bijoy PDFs with correct ASCII digits (e.g. '4%') even though
            # Bengali text is garbled.  Tesseract OCR reads the rendered glyph and emits
            # ASCII '8' for the ৪ glyph.  Correct this in ASCII digit space FIRST,
            # then convert all ASCII digits to Bengali via _normalize_ocr_bn.
            raw_pages = _ocr_pages_bn(file_path)   # returns raw Tesseract text now
            plumber_pages = _pdfplumber_pages(file_path)
            plumber_by_page = {p["page"]: p["text"] for p in plumber_pages}

            page_texts = [
                {
                    "page": p["page"],
                    "text": _normalize_ocr_bn(
                        _patch_ocr_pct_ascii(p["text"], plumber_by_page.get(p["page"], ""))
                    ),
                }
                for p in raw_pages
            ]

            # Phase 2 — safety net: if Tesseract emitted Bengali digits directly
            # (rather than ASCII), _patch_ocr_pct_ascii had no effect.
            # Apply the Bengali-level percentage patch on the now-normalised text.
            page_texts = [
                {
                    "page": p["page"],
                    "text": _patch_ocr_percentages(
                        p["text"], plumber_by_page.get(p["page"], "")
                    ),
                }
                for p in page_texts
            ]
        except Exception:
            page_texts = _pdfplumber_pages(file_path)
    else:
        page_texts = _pdfplumber_pages(file_path)

    # ── Extract tables via pdfplumber for every page (always — OCR has none) ──
    _page_tables: dict[int, list] = {}
    try:
        with pdfplumber.open(file_path) as pdf:
            for pg_idx, page in enumerate(pdf.pages, 1):
                tbls = [
                    tbl.extract()
                    for tbl in page.find_tables()
                    if tbl.extract() and len(tbl.extract()) >= 2
                ]
                if tbls:
                    _page_tables[pg_idx] = tbls
    except Exception:
        pass

    # ── Heading extraction ────────────────────────────────────────────────────
    # Try the user-added structured heading (first non-empty line of page 1).
    # Falls back to the old free-text circular-reference regex if not found.
    first_page_text = page_texts[0]["text"] if page_texts else ""
    heading_info: dict | None = None
    circular_ref = ""

    first_line = next(
        (l.strip() for l in first_page_text.split("\n") if l.strip()), ""
    )
    if first_line:
        heading_info = _parse_bn_circular_heading(first_line)

    if not heading_info:
        # Legacy fallback: extract whatever identifier the regex can find
        circ_match = re.search(
            r'(?:সাকু[রু্]*লার\s*(?:নং|No)[^\n]{0,50}'
            r'|Circular\s*(?:No|Letter)[^\n]{0,50}'
            r'|(?:BRPD|SMESPD|DOS|FEPD|GBCSRD|BFID)[^\n]{0,60})',
            first_page_text, re.IGNORECASE,
        )
        if circ_match:
            circular_ref = circ_match.group(0).strip()[:80]

    # Short circulars (≤ 8 pages): chunk page-wise, repeating the page-1
    # header in every continuation page so each chunk is self-contained.
    if 0 < n_pages <= 8:
        return _chunk_bn_page_wise(page_texts, heading_info, circular_ref, _page_tables)

    chunks = []
    current_section = ""
    current_top = ""   # top-level section label e.g. "১. সংজ্ঞা"
    buf = ""
    last_page = page_texts[-1]["page"] if page_texts else 1

    def _bn_prefix(sec: str) -> tuple[str, str]:
        """Return (prefix_str, chapter_val) for the current circular identity."""
        top_part = f" | {current_top}" if current_top else ""
        sec_part = f" | Section {sec}" if sec else ""
        if heading_info:
            meta = heading_info["chapter"]
            return (
                f"[{meta}{top_part}{sec_part}]\nবিষয়: {heading_info['subject']}\n",
                heading_info["chapter"],
            )
        if circular_ref and sec:
            return f"[{circular_ref}{top_part} | Section {sec}]\n", circular_ref
        if circular_ref:
            return f"[{circular_ref}{top_part}]\n", circular_ref
        if sec:
            return f"[{top_part.lstrip(' | ')}Section {sec}]\n", ""
        if current_top:
            return f"[{current_top}]\n", ""
        return "", ""

    def _flush_bn(buf_text: str, sec: str, pg: int) -> None:
        text = buf_text.strip()
        if not text:
            return
        prefix, chapter_val = _bn_prefix(sec)
        chunk_type = "circular_section" if sec else "circular_narrative"
        chunks.append({
            "content": prefix + text,
            "type": chunk_type,
            "chapter": chapter_val,
            "section": sec,
            "page": pg,
        })

    def _emit_tables(pg: int) -> None:
        """Serialize and emit all pdfplumber tables for the given page."""
        for table_data in _page_tables.get(pg, []):
            prefix, chapter_val = _bn_prefix(current_section)
            serialized = _serialize_table(table_data, current_section)
            if not serialized.strip():
                continue
            for part in _split_serialized_table(serialized, MAX_BN_CHARS * 2):
                chunks.append({
                    "content": prefix + part,
                    "type": "circular_table",
                    "chapter": chapter_val,
                    "section": current_section,
                    "page": pg,
                })

    for page_info in page_texts:
        page_num = page_info["page"]
        for line in page_info["text"].split("\n"):
            line = line.strip()
            if not line:
                continue

            sec_match    = BN_SECTION_RE.match(line)
            top_match    = BN_TOPLEVEL_RE.match(line) if not sec_match else None
            clause_match = BN_CLAUSE_RE.match(line)

            if sec_match:
                # Decimal sub-section (১.১, ২.৩.১) → flush and start new section
                _flush_bn(buf, current_section, page_num)
                buf = ""
                current_section = sec_match.group(1).strip()
                buf = line + "\n"

            elif top_match:
                # Top-level section (১., ২., ০৩.) → update chapter context
                _flush_bn(buf, current_section, page_num)
                buf = ""
                current_top = top_match.group(1) + ". " + top_match.group(2).strip()
                current_section = ""
                buf = line + "\n"

            elif clause_match:
                # Each clause letter (ক), খ), …) starts a new retrievable chunk
                _flush_bn(buf, current_section, page_num)
                buf = line + "\n"

            else:
                buf += line + "\n"
                if len(buf) > MAX_BN_CHARS:
                    _flush_bn(buf, current_section, page_num)
                    buf = ""

        # Emit tables for this page after its text is processed
        _emit_tables(page_num)

    if buf.strip():
        _flush_bn(buf, current_section, last_page)

    return chunks


# ── Industry Analysis chunker ─────────────────────────────────────────────────

# Dot-leader lines from table-of-contents pages: "Overview ......... 5"
_IA_TOC_LINE_RE = re.compile(r'\.{4,}')

# Figure captions, source notes, and bare page numbers to skip
_IA_NOISE_RE = re.compile(
    r'^(Figure|Fig\.|Chart|Graph|Source:?|Note:?|NB:?|Exhibit)\s*\d*',
    re.IGNORECASE,
)
_IA_PAGENO_RE = re.compile(r'^\d{1,3}$')

# Running page footer: any line ending with a bare page number after a period
# or pipe — e.g. "Md. Mehedi Hasan, AGM, CRM Central. 17"
_IA_RUNNING_FOOTER_RE = re.compile(r'[.|]\s*\d{1,3}\s*$')

# pdfplumber table-detection settings for reports with no ruling lines.
# Used as a fallback when the default lines strategy finds no tables on a page.
_IA_TEXT_TABLE_SETTINGS = {
    "vertical_strategy":    "text",
    "horizontal_strategy":  "text",
    "snap_tolerance":       3,
    "min_words_vertical":   2,
    "min_words_horizontal": 2,
}


def _ia_is_data_table(table_data: list) -> bool:
    """
    Returns True only when the table has genuine multi-column structure.

    At least half the rows must have ≥ 2 non-empty cells AND at least one
    cell across the whole table must be ≥ 8 chars (rejects purely decorative
    cover-page layouts where pdfplumber fragments titles into tiny pieces).

    When this returns False the caller re-injects the cell text into the
    narrative buffer so numbers stay under the correct section heading rather
    than being lost or mis-attributed.
    """
    if not table_data or len(table_data) < 2:
        return False
    multi_col_rows = sum(
        1 for row in table_data
        if sum(1 for c in row if c and str(c).strip()) >= 2
    )
    if multi_col_rows < max(1, len(table_data) // 2):
        return False
    # At least one cell must have meaningful content (≥ 8 chars).
    # Garbled title-page fragments ("ical", "I", "nd") are all short;
    # real data cells ("Medium:16-22%", "Bangladesh", "12-14%") are longer.
    return any(
        len(str(c).strip()) >= 8
        for row in table_data for c in row
        if c and str(c).strip()
    )


def _ia_extract_tables(page, page_num: int):
    """
    Detect tables using pdfplumber's lines strategy first.
    Falls back to text-column strategy (for borderless / space-aligned tables)
    only from page 3 onward — cover and TOC pages are excluded because the
    text strategy would misread multi-column title layouts as data tables.
    """
    tables = page.find_tables()
    if tables:
        return tables
    if page_num < 3:
        return []
    try:
        return page.find_tables(_IA_TEXT_TABLE_SETTINGS) or []
    except Exception:
        return []


def _ia_emit_table(table_data: list, section: str, page_num: int,
                   chunks: list) -> None:
    prefix = _make_prefix(section, "", "")
    serialized = _serialize_table(table_data, section)
    if not serialized.strip():
        return
    for part in _split_serialized_table(serialized, MAX_NARRATIVE_CHARS):
        chunks.append({
            "content": prefix + part,
            "type": "analysis_table",
            "chapter": section,
            "section": "",
            "page": page_num,
        })


def _is_ia_heading(line: str) -> bool:
    """
    Returns True if line looks like a section heading in an industry report.

    Heuristic (no font-size info from pdfplumber):
    - Must start with an uppercase letter.
    - Must NOT end with a sentence-terminal period, "!", or "?".
    - Must NOT be a running page footer (text ending with bare page number).
    - Must NOT contain a mid-line colon ("Label: Value" data pairs).
    - Must NOT have ≥ 2 numeric tokens (data rows like "China 5,933 6,423 …").
    - Must NOT be garbled single-char text ("O t h e r s").
    - Qualifies as heading when: ≤ 2 words, ends with ":", or 3–10 words
      without trailing sentence punctuation.
    """
    stripped = line.strip()
    if not stripped or not stripped[0].isupper():
        return False
    if _IA_TOC_LINE_RE.search(stripped):
        return False
    if stripped[-1] in '.!?':
        return False
    if _IA_RUNNING_FOOTER_RE.search(stripped):
        return False
    # Mid-line colon → "Label: Value" data, not a heading title
    colon_pos = stripped.find(':')
    if colon_pos != -1 and colon_pos < len(stripped) - 1:
        return False
    words = stripped.split()
    if sum(1 for w in words if re.search(r'\d', w)) >= 2:
        return False
    if words and all(len(w) <= 2 for w in words):
        return False
    if len(words) <= 2 and len(stripped) >= 4:
        return True
    if stripped.endswith(':'):
        return True
    if 3 <= len(words) <= 10 and stripped[-1] not in '.!?,;':
        return True
    return False


def _chunk_industry_analysis(file_path: str) -> list:
    """
    Chunker for industry analysis / sector report PDFs.

    Data accuracy design:
    - pdfplumber text extraction inherently skips embedded images/charts.
    - Tables are detected with a two-strategy approach: PDF ruling-line
      detection first, text-column fallback for borderless tables.
    - Single-column text boxes (highlighted fact blocks) are NOT emitted as
      table chunks.  Their text is re-injected into the narrative buffer so
      the numbers stay under the correct section heading rather than being
      attributed to the last detected heading inside the box itself.
    - Running page headers/footers are stripped before heading detection.
    - TOC pages and sparse cover pages are skipped entirely.
    """
    chunks: list = []
    section = ""
    narrative_buf = ""
    overlap = ""
    last_page = 1

    with pdfplumber.open(file_path) as pdf:
        last_page = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages, start=1):
            # Detect tables on the full page (tables can touch the margin).
            page_table_objs = _ia_extract_tables(page, page_num)
            table_bboxes = [t.bbox for t in page_table_objs]

            # Crop text extraction to the content zone — top 7% and bottom 6%
            # of each page are stripped to exclude running page headers and
            # footers (e.g. "Md. Mehedi Hasan, AGM, CRM Central. 17").
            # Table detection above uses the full page so edge tables are safe.
            ph = page.height
            pw = page.width
            content = page.crop((0, ph * 0.07, pw, ph * 0.94))

            if table_bboxes:
                def _outside(obj, bboxes=table_bboxes):
                    for x0, top, x1, bottom in bboxes:
                        if (obj.get("x0", 0) >= x0 - 2
                                and obj.get("x1", 0) <= x1 + 2
                                and obj.get("top", 0) >= top - 2
                                and obj.get("bottom", 0) <= bottom + 2):
                            return False
                    return True
                page_text = content.filter(_outside).extract_text() or ""
            else:
                page_text = content.extract_text() or ""

            # Skip sparse cover / image-only pages entirely.
            # Tables on near-empty pages are decorative text boxes, not data.
            if len(page_text.strip()) < 80:
                continue

            # Skip TOC pages in the opening section of the document
            lines = page_text.split("\n")
            if page_num <= 5 and sum(1 for l in lines if _IA_TOC_LINE_RE.search(l)) >= 3:
                continue

            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if _IA_TOC_LINE_RE.search(line):
                    continue
                if _IA_NOISE_RE.match(line) or _IA_PAGENO_RE.match(line):
                    continue

                if _is_ia_heading(line):
                    overlap = _flush_narrative(
                        narrative_buf, section, "", "",
                        page_num, chunks, overlap,
                    )
                    narrative_buf = ""
                    section = line.rstrip(':').strip()
                else:
                    narrative_buf += line + " "
                    if len(narrative_buf) > MAX_NARRATIVE_CHARS:
                        overlap = _flush_narrative(
                            narrative_buf, section, "", "",
                            page_num, chunks, overlap,
                        )
                        narrative_buf = ""

            # Process tables detected on this page.
            # Multi-column → analysis_table chunk.
            # Single-column text box → re-inject text into narrative so the
            # numbers stay under the correct section heading with full context.
            for tbl in page_table_objs:
                td = tbl.extract()
                if not td:
                    continue
                if _ia_is_data_table(td):
                    if narrative_buf.strip():
                        overlap = _flush_narrative(
                            narrative_buf, section, "", "",
                            page_num, chunks, overlap,
                        )
                        narrative_buf = ""
                        overlap = ""
                    _ia_emit_table(td, section, page_num, chunks)
                else:
                    # Flatten single-column box cells back into narrative
                    for row in td:
                        for cell in row:
                            if cell:
                                cell_text = str(cell).strip()
                                if cell_text:
                                    narrative_buf += cell_text + " "
                                    if len(narrative_buf) > MAX_NARRATIVE_CHARS:
                                        overlap = _flush_narrative(
                                            narrative_buf, section, "", "",
                                            page_num, chunks, overlap,
                                        )
                                        narrative_buf = ""

    if narrative_buf.strip():
        _flush_narrative(narrative_buf, section, "", "", last_page, chunks, overlap)

    return chunks


# ── public API ────────────────────────────────────────────────────────────────

_VALID_STRATEGIES = {'circular_bn', 'circular_en', 'chapter_doc', 'industry_analysis'}

# Running-footer pattern common in IDLC policy PDFs
_FOOTER_RE = re.compile(r'^Confidential\s+\S.{0,50}\s+\d{1,3}\s*$', re.IGNORECASE)


def _is_useful_chunk(chunk: dict) -> bool:
    """
    Returns False for noise chunks: cover-page layout tables, TOC fragments,
    and page-footer-only narrative blobs.
    """
    content = chunk["content"]
    # Strip the bracketed metadata prefix line so we measure only body content
    body = re.sub(r'^\[[^\]]*\]\n', '', content).strip()
    if len(body) < 60:
        return False
    # Single-line footer: "Confidential IDLC Finance PLC 73"
    if _FOOTER_RE.match(body):
        return False
    return True


def chunk_hierarchical(file_path: str, strategy: str | None = None) -> list:
    """
    Returns a list of chunk dicts: {content, type, chapter, section, page}

    Pass strategy='circular_bn'|'circular_en'|'chapter_doc'|'industry_analysis'
    to skip auto-detection.  strategy=None auto-detects based on content.

    | Type              | Detection                               | Chunker                    |
    |-------------------|-----------------------------------------|----------------------------|
    | circular_bn       | Bengali chars / CID / Bijoy encoding    | _chunk_circular_bn         |
    | circular_en       | Short English circular (≤ 15 pages)     | _chunk_circular_en         |
    | chapter_doc       | Chapter headings or > 15 pages          | _chunk_pdf                 |
    | industry_analysis | Manual selection only                   | _chunk_industry_analysis   |
    | DOCX / DOC        | File extension                          | paragraph fallback         |
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        doc_type = strategy if strategy in _VALID_STRATEGIES else _detect_doc_type(file_path)
        if doc_type == 'circular_bn':
            chunks = _chunk_circular_bn(file_path)
        elif doc_type == 'circular_en':
            chunks = _chunk_circular_en(file_path)
        elif doc_type == 'industry_analysis':
            chunks = _chunk_industry_analysis(file_path)
        else:
            chunks = _chunk_pdf(file_path)
        return [c for c in chunks if _is_useful_chunk(c)]

    # Word documents: paragraph-based fallback
    text = extract_text(file_path)
    return [
        {"content": para, "type": "narrative", "chapter": "", "section": "", "page": 0}
        for para in chunk_by_paragraph(text)
        if len(para.strip()) >= 60
    ]
