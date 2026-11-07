from sqlmodel import Session, text
from typing import List
import re as _re

# Bengali Unicode range for content detection
_BN_WORD_RE = _re.compile(r'[ঀ-৿]{3,}')


def _run_search(
    session: Session,
    embedding: list[float],
    user_id: int,
    limit: int,
    bengali_only: bool = False,
    english_only: bool = False,
) -> List[dict]:
    """
    Single vector search with user isolation and optional language filter.
    Returns dicts with content, chapter, page_num, and display_name.

    bengali_only  — restrict to chunks that contain Bengali Unicode characters
                    or have a Bengali circular chunk_type (circular_section /
                    circular_narrative). Used when querying with a Bengali
                    translation.
    english_only  — exclude chunks that contain Bengali Unicode characters.
                    Used when querying with the original English text so
                    Bengali circular chunks don't compete.
    """
    embedding_str = "[" + ",".join(map(str, embedding)) + "]"
    params: dict = {"embedding": embedding_str, "limit": limit, "user_id": user_id}

    lang_filter = ""
    if bengali_only:
        # Content-based only: require actual Bengali characters in the chunk text.
        # The old chunk_type IN (...) OR condition incorrectly included English
        # circular pages (chunk_type='circular_page') in Bengali search results,
        # causing them to be labeled [Bengali Circular] and answered in Bengali.
        lang_filter = "AND e.content ~ '[ঀ-৿]'"
    elif english_only:
        lang_filter = "AND e.content !~ '[ঀ-৿]'"

    result = session.exec(
        text(f"""
            SELECT e.content, e.chapter, e.page_num, d."displayName", d.id, e.chunk_type,
                   COALESCE(NULLIF(e.subject,''), d.subject, '') AS subject,
                   d.chunk_strategy
            FROM embeddings e
            JOIN document d ON e.document_id = d.id
            WHERE d."userId" = :user_id
              {lang_filter}
            ORDER BY e.embedding <-> CAST(:embedding AS vector)
            LIMIT :limit
        """),
        params=params,
    )
    return [
        {
            "content": row[0],
            "chapter": row[1] or "",
            "page_num": row[2],
            "display_name": row[3] or "",
            "document_id": row[4],
            "chunk_type": row[5] or "",
            "subject": row[6] or "",
            "doc_strategy": row[7] or "",
        }
        for row in result.fetchall()
    ]


def _keyword_search_bn(
    session: Session,
    bn_query_text: str,
    user_id: int,
    limit: int = 5,
) -> List[dict]:
    """
    Keyword-based supplement for Bengali queries.
    Returns dicts with content, chapter, page_num, and display_name.

    Strategy (handles OCR-garbled text where consonant conjuncts are dropped):
    1. Try bigrams first — most specific, best signal-to-noise.
    2. If bigrams find nothing, issue a single OR query across ALL extracted
       Bengali words so that correctly-OCR'd simple words (e.g. 'নারী') can
       still match even when conjunct-heavy words (e.g. 'উদ্যোগ' → 'উেদাগ')
       are garbled.
    3. Results are sorted by section so definitional sections (১.৬) surface
       before later usage sections (৭.১, ১১.১).
    """
    words = _BN_WORD_RE.findall(bn_query_text)
    if not words:
        return []

    seen: set[str] = set()
    results: list[dict] = []

    def _run(term: str) -> None:
        try:
            rows = session.exec(
                text("""
                    SELECT e.content, e.chapter, e.page_num, d."displayName", d.id, e.chunk_type,
                           COALESCE(NULLIF(e.subject,''), d.subject, '') AS subject,
                           d.chunk_strategy
                    FROM embeddings e
                    JOIN document d ON e.document_id = d.id
                    WHERE d."userId" = :user_id
                      AND (
                        e.chunk_type IN ('circular_section', 'circular_narrative', 'circular_page', 'table_vision')
                        OR e.content ~ '[ঀ-৿]'
                      )
                      AND e.content ILIKE :term
                    ORDER BY e.section
                    LIMIT :limit
                """),
                params={"user_id": user_id, "term": f"%{term}%", "limit": limit},
            )
            for row in rows.fetchall():
                if row[0] not in seen:
                    seen.add(row[0])
                    results.append({"content": row[0], "chapter": row[1] or "", "page_num": row[2], "display_name": row[3] or "", "document_id": row[4], "chunk_type": row[5] or "", "subject": row[6] or "", "doc_strategy": row[7] or ""})
        except Exception:
            pass

    # Phase 1: bigrams
    for i in range(min(len(words) - 1, 3)):
        _run(words[i] + " " + words[i + 1])

    if results:
        return results[:limit]

    # Phase 2: per-word search with multi-word scoring.
    #
    # The old single OR query sorted by section ASC which caused page-wise
    # chunks (section='') from other documents to rank first, crowding out
    # the actually relevant section-based chunk. Instead, run one query per
    # unique word and count how many query words each chunk matches — a chunk
    # matching 4/5 query words almost certainly has the answer, while a chunk
    # matching 1/5 is an incidental hit. OCR errors are tolerated because
    # well-OCR'd words (e.g. 'মাঝারি', 'সর্বোচ্চ', 'বিনিয়োগ') still match
    # even when garbled words (e.g. 'ঝণ' for 'ঋণ') miss.
    unique_words = list(dict.fromkeys(w for w in words if len(w) >= 4))[:8]
    if not unique_words:
        return []

    hit_scores: dict[str, int] = {}      # content → number of matching words
    hit_data: dict[str, dict] = {}        # content → row data

    for word in unique_words:
        try:
            rows = session.exec(
                text("""
                    SELECT e.content, e.chapter, e.page_num, d."displayName", d.id, e.chunk_type,
                           COALESCE(NULLIF(e.subject,''), d.subject, '') AS subject,
                           d.chunk_strategy
                    FROM embeddings e
                    JOIN document d ON e.document_id = d.id
                    WHERE d."userId" = :user_id
                      AND (
                        e.chunk_type IN ('circular_section', 'circular_narrative', 'circular_page', 'table_vision')
                        OR e.content ~ '[ঀ-৿]'
                      )
                      AND e.content ILIKE :term
                    LIMIT 20
                """),
                params={"user_id": user_id, "term": f"%{word}%"},
            )
            for row in rows.fetchall():
                c = row[0]
                hit_scores[c] = hit_scores.get(c, 0) + 1
                if c not in hit_data:
                    hit_data[c] = {
                        "content": c,
                        "chapter": row[1] or "",
                        "page_num": row[2],
                        "display_name": row[3] or "",
                        "document_id": row[4],
                        "chunk_type": row[5] or "",
                        "subject": row[6] or "",
                        "doc_strategy": row[7] or "",
                    }
        except Exception:
            session.rollback()

    # Return chunks ordered by score (most matching query words first)
    for content in sorted(hit_scores, key=lambda c: -hit_scores[c]):
        if content not in seen:
            seen.add(content)
            results.append(hit_data[content])

    return results[:limit]


def search_similar_chunks(
    session: Session,
    query_embedding: list[float],
    user_id: int,
    limit: int = 5,
) -> List[dict]:
    """Standard single-language search scoped to the user's documents."""
    return _run_search(session, query_embedding, user_id, limit)


def search_bilingual(
    session: Session,
    en_embedding: list[float],
    bn_embedding: list[float],
    user_id: int,
    limit: int = 5,
    bn_query_text: str = "",
) -> List[dict]:
    """
    Hybrid dual-language search combining vector similarity with keyword
    matching for Bengali circular content.
    Returns dicts with content, chapter, page_num, and display_name.

    Slot allocation (guarantees English documents always get representation):
      - keyword  : up to 2 slots  (pins definitional Bengali sections)
      - Bengali  : up to bn_budget slots  (vector similarity)
      - English  : fills remaining slots up to `limit`

    With limit=8: keyword≤2, Bengali≤5, English fills to 8.
    This ensures PPG / English policy docs are never crowded out entirely.
    """
    per_lang = max(limit // 2, 3)   # balanced budget for each language

    bn_results = _run_search(session, bn_embedding, user_id, per_lang, bengali_only=True)
    en_results = _run_search(session, en_embedding, user_id, per_lang, english_only=True)

    # Keyword supplement: at most 4 results — keyword matching is more reliable
    # than vector similarity for table data and specific values (e.g. loan limits).
    # Placed first so definitional/tabular sections get seen by the LLM even when
    # vector similarity ranks them below the top per_lang results.
    kw_results = _keyword_search_bn(session, bn_query_text, user_id, limit=4) if bn_query_text else []

    # Guarantee at least half the slots for English results.
    # Without this, keyword (up to 4) + Bengali vector (per_lang) fill the
    # list first, leaving only 2 English slots — English-only circulars get
    # crowded out and the LLM says "not found" for valid English questions.
    en_min = limit // 2  # 6 for limit=12

    seen: set[str] = set()
    merged: list[dict] = []

    # 1. Fill English up to en_min guaranteed slots
    for chunk in en_results:
        if len(merged) >= en_min:
            break
        if chunk["content"] not in seen:
            seen.add(chunk["content"])
            merged.append(chunk)

    # 2. Fill keyword + Bengali vector in remaining slots
    for chunk in kw_results[:4] + bn_results:
        if len(merged) >= limit:
            break
        if chunk["content"] not in seen:
            seen.add(chunk["content"])
            merged.append(chunk)

    return merged[:limit]


def user_has_bengali_docs(session: Session, user_id: int) -> bool:
    """
    Returns True if this user has at least one Bengali circular chunk.

    Detects Bengali two ways so it works for both old chunks (CID-mixed
    text stored before the new chunker) and new chunks (clean OCR text):
    - chunk_type check for new-style circular chunks
    - Bengali Unicode regex for any chunk containing Bengali characters
    """
    result = session.exec(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM embeddings e
                JOIN document d ON e.document_id = d.id
                WHERE d."userId" = :user_id
                  AND (
                    e.chunk_type IN ('circular_section', 'circular_narrative', 'circular_page', 'table_vision')
                    OR e.content ~ '[ঀ-৿]'
                  )
                LIMIT 1
            )
        """),
        params={"user_id": user_id},
    )
    return bool(result.scalar())
