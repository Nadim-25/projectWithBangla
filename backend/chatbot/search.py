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
        lang_filter = """
            AND (
                e.chunk_type IN ('circular_section', 'circular_narrative', 'circular_page')
                OR e.content ~ '[ঀ-৿]'
            )
        """
    elif english_only:
        lang_filter = "AND e.content !~ '[ঀ-৿]'"

    result = session.exec(
        text(f"""
            SELECT e.content, e.chapter, e.page_num, d."displayName"
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
        {"content": row[0], "chapter": row[1] or "", "page_num": row[2], "display_name": row[3] or ""}
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
                    SELECT e.content, e.chapter, e.page_num, d."displayName"
                    FROM embeddings e
                    JOIN document d ON e.document_id = d.id
                    WHERE d."userId" = :user_id
                      AND (
                        e.chunk_type IN ('circular_section', 'circular_narrative', 'circular_page')
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
                    results.append({"content": row[0], "chapter": row[1] or "", "page_num": row[2], "display_name": row[3] or ""})
        except Exception:
            pass

    # Phase 1: bigrams
    for i in range(min(len(words) - 1, 3)):
        _run(words[i] + " " + words[i + 1])

    if results:
        return results[:limit]

    # Phase 2: single OR query across all unique words (≥ 3 chars).
    # OCR often garbles conjuncts (্) so conjunct-heavy words may not match,
    # but simple words like 'নারী' will — and ORDER BY section ensures the
    # definitional section (১.৬) appears before later usage sections.
    unique_words = list(dict.fromkeys(w for w in words if len(w) >= 3))[:8]
    if not unique_words:
        return []

    conditions = " OR ".join(f"e.content ILIKE :w{i}" for i in range(len(unique_words)))
    or_params: dict = {"user_id": user_id, "limit": limit}
    for i, w in enumerate(unique_words):
        or_params[f"w{i}"] = f"%{w}%"

    try:
        # Note: no DISTINCT here — dedup is handled by `seen`.
        # DISTINCT + ORDER BY non-selected column is a PostgreSQL error.
        rows = session.exec(
            text(f"""
                SELECT e.section, e.content, e.chapter, e.page_num, d."displayName"
                FROM embeddings e
                JOIN document d ON e.document_id = d.id
                WHERE d."userId" = :user_id
                  AND (
                    e.chunk_type IN ('circular_section', 'circular_narrative', 'circular_page')
                    OR e.content ~ '[ঀ-৿]'
                  )
                  AND ({conditions})
                ORDER BY e.section
                LIMIT :limit
            """),
            params=or_params,
        )
        for row in rows.fetchall():
            content = row[1]
            if content not in seen:
                seen.add(content)
                results.append({"content": content, "chapter": row[2] or "", "page_num": row[3], "display_name": row[4] or ""})
    except Exception:
        session.rollback()

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

    # Keyword supplement: at most 2 results so they don't crowd out English.
    # These are placed first so definitional sections (১.৬) get seen by the LLM
    # even when vector similarity ranks them below the top per_lang results.
    kw_results = _keyword_search_bn(session, bn_query_text, user_id, limit=2) if bn_query_text else []

    seen: set[str] = set()
    merged: list[dict] = []

    # Fill keyword slots first (max 2), then Bengali vector, then English
    for chunk in kw_results[:2] + bn_results + en_results:
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
                    e.chunk_type IN ('circular_section', 'circular_narrative', 'circular_page')
                    OR e.content ~ '[ঀ-৿]'
                  )
                LIMIT 1
            )
        """),
        params={"user_id": user_id},
    )
    return bool(result.scalar())
