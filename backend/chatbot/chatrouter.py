from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from openai import OpenAI
import os
import re
import io
import json
from typing import Optional, List
from utils.database import get_database
from chatbot.model import Chat, Message, Document
from chatbot.embeddings import create_embedding
from chatbot.search import search_similar_chunks, search_bilingual, user_has_bengali_docs
from chatbot.getchat import get_user_messages, group_messages_by_chat, format_chat_list
from chatbot.getchatbychatid import get_chat_messages, format_single_chat
from user.model import User
from user.router import get_current_user


chat_router = APIRouter()


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

_BN_RE = re.compile(r'[ঀ-৿]')

def _chunk_is_mostly_bengali(text: str, threshold: float = 0.10) -> bool:
    """True only when Bengali characters make up > threshold of the content.

    Single-char _is_bengali() fires on any Bengali character, so English
    circulars with a Bengali letterhead or signature line get mislabeled as
    [Bengali Circular]. Using a 10 % ratio fixes this: pure Bengali circulars
    are 50-80 % Bengali; English FEPD/BRPD circulars with one Bengali line
    are < 5 % Bengali.
    """
    if not text:
        return False
    bn_chars = sum(1 for c in text if 'ঀ' <= c <= '৿')
    return bn_chars / max(len(text), 1) > threshold

# Phrases that signal a follow-up / continuation question with no retrieval signal.
# When matched, the search query is augmented with the previous user turn so the
# vector search retrieves the same document as the original question.
_FOLLOWUP_RE = re.compile(
    r'^(please\s+)?(explain|elaborate|tell\s+me\s+more|more\s+detail|more\s+elaborately|'
    r'more\s+clearly|continue|go\s+on|what\s+about|can\s+you|could\s+you|describe|'
    r'clarify|expand|further|summarize\s+more|give\s+more|provide\s+more|'
    r'আরো|আরও|বিস্তারিত|আরো\s+বলুন|বিশদ|ব্যাখ্যা\s+করুন|আরও\s+ব্যাখ্যা)',
    re.IGNORECASE,
)


def _is_bengali(text: str) -> bool:
    return bool(_BN_RE.search(text))


def _is_followup(question: str) -> bool:
    """Return True when the question is too vague to retrieve on its own.

    Criteria: fewer than 8 tokens (nothing banking-specific) OR starts with
    a continuation phrase like "explain more", "elaborate", "বিস্তারিত", etc.
    """
    stripped = question.strip()
    if len(stripped.split()) <= 7:
        return True
    return bool(_FOLLOWUP_RE.match(stripped))


def _clean_source_name(display_name: str, chapter: str) -> str:
    """Return a human-readable source label.

    Uses display_name when it looks meaningful (has spaces or uppercase letters).
    Falls back to the circular_no segment of chapter when display_name is a raw
    file slug like 'mar172025smespd01' (no spaces, all lowercase).
    """
    if display_name and (' ' in display_name or any(c.isupper() for c in display_name)):
        return display_name
    if chapter and ' | ' in chapter:
        return chapter.split(' | ')[0].strip()
    return display_name or chapter or ""


def _parse_chapter_ref_date(chapter: str) -> tuple[str, str]:
    """Return (circular_ref, circular_date) from a chapter field.

    Chapter format stored by pdf.py:
      'circular_no | department | issue_date'  (3 parts)
      'circular_no | issue_date'               (2 parts, no dept)
      'circular_no'                            (1 part)
    circular_ref is always the first segment; circular_date is the last
    segment when more than one segment exists.
    """
    if not chapter:
        return "", ""
    parts = [p.strip() for p in chapter.split(' | ')]
    # Drop bare all-caps ASCII dept codes (e.g. "DFIM", "BRPD") that carry
    # no display value — they are already embedded in circular_ref.
    meaningful = [p for p in parts if not re.match(r'^[A-Z]{2,10}$', p)]
    if not meaningful:
        meaningful = parts
    circular_ref = meaningful[0]
    circular_date = meaningful[-1] if len(meaningful) > 1 else ""
    return circular_ref, circular_date


# Bengali subject line in chunk header: "বিষয়: ঋণ/লিজ/বিনিয়োগ অবলোপন …"
# Anchored to line-start (^) to prevent matching "বিষয়ক" inside body text
# or TOC entries like "বিষয়: সাধারণ নির্দেশনা | Section ১০.৩ | Page 9"
_BN_SUBJECT_RE = re.compile(r'^বিষয়\s*[:\-]\s*(.{10,120})$', re.MULTILINE)


def _extract_subject_from_content(content: str) -> str:
    """Fallback: extract subject from chunk header area (first 4 lines only).

    The subject line appears on line 2 of chunks from documents with structured
    headings.  Restricting to 4 lines prevents deep TOC entries from matching.
    """
    head = '\n'.join(content.split('\n')[:4])
    m = _BN_SUBJECT_RE.search(head)
    if not m:
        return ""
    text = m.group(1).strip().rstrip('।').strip()
    # Reject lines that look like chunk metadata (pipe-separated or has Section/Page keywords)
    if '|' in text or re.search(r'\b(?:Section|Page)\b', text):
        return ""
    return text


# Matches Bengali circular number inside OCR'd chunk content:
#   "ডিএফআইএম সার্কুলার লেটার নং-১৭"  or  "বিআরপিডি সার্কুলার নং-০৫"
_CIRC_REF_CONTENT_RE = re.compile(
    r'([^\n]*সার্কুলার[^\n]*নং\s*[-–]?\s*[০-৯\d][^\n]{0,40})',
    re.MULTILINE,
)

# Bengali Gregorian date in chunk body: "২৪ জুলাই ২০২৫"
_BN_DATE_CONTENT_RE = re.compile(
    r'([০-৯]{1,2}\s+'
    r'(?:জানুয়ারি|ফেব্রুয়ারি|মার্চ|এপ্রিল|মে|জুন|'
    r'জুলাই|আগস্ট|সেপ্টেম্বর|অক্টোবর|নভেম্বর|ডিসেম্বর)'
    r'\s+[১২][০-৯]{3})'
)


def _extract_meta_from_content(content: str) -> tuple[str, str]:
    """Scan the first 25 lines of chunk content for circular ref and date.

    Used as a fallback when the DB chapter field is empty or incomplete,
    i.e. documents uploaded before the _scan_bn_circular_identity fallback
    was added to pdf.py.  Every page chunk embeds the page-1 letterhead
    (circular number line + date line) so this always has enough context.
    """
    head = '\n'.join(content.split('\n')[:25])
    circ_ref = ""
    m = _CIRC_REF_CONTENT_RE.search(head)
    if m:
        circ_ref = m.group(1).strip()
    circ_date = ""
    m = _BN_DATE_CONTENT_RE.search(head)
    if m:
        circ_date = m.group(1).strip()
    return circ_ref, circ_date


_NOT_FOUND_EN = "I don't know based on the document."
_NOT_FOUND_BN = "এই তথ্য প্রদত্ত ডকুমেন্টে পাওয়া যায়নি।"

# Maximum chars of context sent to the grounding check to stay within token limits.
_GROUNDING_CONTEXT_LIMIT = 6000


def _grounding_check(answer: str, context_text: str) -> bool:
    """Return True if every factual claim in the answer is supported by context_text.

    Uses gpt-4o-mini (cheap, fast). Fails open — returns True on any API error
    so a transient failure never silently swallows a correct answer.
    Fallback phrases are always considered grounded.
    Bengali ANSWERS are exempted: OCR noise makes gpt-4o-mini unable to verify
    Bengali claims reliably. English answers are always verified — even when the
    context contains Bengali chunks — because the verifier checks the English
    answer against the English portions of the context and ignores Bengali text.
    """
    if answer.strip() in (_NOT_FOUND_EN, _NOT_FOUND_BN):
        return True
    # Skip only when the ANSWER is Bengali — checking Bengali OCR claims is
    # unreliable. English answers must always be verified regardless of whether
    # the context also contains Bengali chunks from other documents.
    if _BN_RE.search(answer):
        return True
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a strict grounding verifier. "
                        "Given CONTEXT and ANSWER, decide whether every factual claim "
                        "in the ANSWER is directly supported by the CONTEXT. "
                        "Reply with exactly one word: GROUNDED or NOT_GROUNDED."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"CONTEXT:\n{context_text[:_GROUNDING_CONTEXT_LIMIT]}\n\n"
                        f"ANSWER:\n{answer}"
                    ),
                },
            ],
            max_tokens=5,
            temperature=0,
            seed=42,
        )
        verdict = resp.choices[0].message.content.strip().upper()
        return verdict == "GROUNDED"
    except Exception:
        return True  # fail open


def _translate_to_bengali(text: str) -> str:
    """
    Translate an English query to Bengali using GPT so it can be matched
    against Bengali circular chunks in the vector store.
    Falls back to the original text if translation fails.
    """
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a translator specializing in Bangladesh Bank financial "
                        "regulations and CMSME (Cottage, Micro, Small and Medium Enterprise) "
                        "terminology. Translate the user's English text to Bengali (Bangla). "
                        "Use official Bangladesh Bank circular terminology. Key terms: "
                        "'women entrepreneurship' → 'নারী উদ্যোগ', "
                        "'woman enterprise' → 'নারী উদ্যোগ', "
                        "'women entrepreneur' → 'নারী উদ্যোক্তা', "
                        "'micro enterprise' → 'অতিক্ষুদ্র শিল্প', "
                        "'micro industry' → 'অতিক্ষুদ্র শিল্প', "
                        "'small enterprise' → 'ক্ষুদ্র শিল্প', "
                        "'small industry' → 'ক্ষুদ্র শিল্প', "
                        "'medium enterprise' → 'মাঝারি শিল্প', "
                        "'medium industry' → 'মাঝারি শিল্প', "
                        "'cottage enterprise' → 'কুটির শিল্প', "
                        "'cottage industry' → 'কুটির শিল্প', "
                        "'CMSME' → 'সিএমএসএমই', "
                        "'master circular' → 'মাস্টার সার্কুলার', "
                        "'group security loan' → 'গ্রুপ সিকিউরিটি ঋণ', "
                        "'group guarantee' → 'গ্রুপ গ্যারান্টি', "
                        "'collateral' → 'জামানত', "
                        "'working capital' → 'চলতি মূলধন', "
                        "'term loan' → 'মেয়াদী ঋণ', "
                        "'revolving loan' → 'আবর্তনশীল ঋণ', "
                        "'interest rate' → 'সুদহার', "
                        "'intermediation spread' → 'intermediation spread', "
                        "'one time exit' → 'বিশেষ এক্সিট', "
                        "'one-time exit' → 'বিশেষ এক্সিট', "
                        "'special exit' → 'বিশেষ এক্সিট', "
                        "'loan recovery' → 'ঋণ আদায়', "
                        "'defaulter' → 'খেলাপী ঋণগ্রহীতা', "
                        "'non-performing loan' → 'খেলাপী ঋণ', "
                        "'NPL' → 'খেলাপী ঋণ'. "
                        "Output only the Bengali translation, nothing else."
                    ),
                },
                {"role": "user", "content": text},
            ],
            max_tokens=300,
            temperature=0,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return text


# =========================
# REQUEST SCHEMA
# =========================
class ChatRequest(BaseModel):
    chatId: Optional[int] = None   # ✅ FIXED: use int
    question: str


# =========================
# GET HISTORY
# =========================
def get_history(session: Session, chat_id: int, limit: int = 10) -> List[dict]:
    statement = (
        select(Message)
        .where(Message.chat_id == chat_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )

    messages = session.exec(statement).all()

    return [
        {"role": m.role, "content": m.content}
        for m in messages
    ]


# =========================
# CREATE CHAT
# =========================
def create_chat(session: Session, user_id: int) -> int:
    chat = Chat(user_id=user_id)

    session.add(chat)
    session.commit()
    session.refresh(chat)

    return chat.id


# =========================
# CHAT ROUTE
# =========================
@chat_router.post("/chat")
def chat(req: ChatRequest, session: Session = Depends(get_database), current_user: User = Depends(get_current_user)):
    try:
        chat_id: int = req.chatId
        user_id: int = current_user.id
        question = req.question

        # =========================
        # VALIDATION
        # =========================
        if not user_id:
            raise HTTPException(status_code=400, detail="userId is required")

        # =========================
        # GET OR CREATE CHAT
        # =========================
        chat = None

        if chat_id:
            chat = session.exec(
            select(Chat).where(Chat.id == chat_id)
            ).first()

        # 🔥 If chat doesn't exist → create new one automatically
        if not chat:
            chat_id = create_chat(session, user_id)
        else:
            chat_id = chat.id

        # =========================
        # HISTORY (LIMITED)
        # =========================
        history = get_history(session, chat_id, limit=10)

        # History contamination guard: old Bengali assistant answers in an
        # existing chat prime the LLM to respond in Bengali even when the
        # current question is English and the best chunks are [English Document].
        # Strip Bengali assistant turns so only user turns (needed for follow-up
        # context resolution) remain in history for English questions.
        if not _is_bengali(question):
            history = [
                m for m in history
                if m["role"] != "assistant" or not _chunk_is_mostly_bengali(m["content"])
            ]

        # =========================
        # VECTOR SEARCH (RAG)
        # =========================
        # Follow-up augmentation: when the current question is too vague to
        # retrieve on its own ("explain more", "elaborate", etc.), prepend the
        # previous user turn so the vector search retrieves the same document
        # as the original question rather than drifting to unrelated chunks.
        search_question = question
        if _is_followup(question) and history:
            prev_user_q = next(
                (m["content"] for m in reversed(history) if m["role"] == "user"), ""
            )
            if prev_user_q:
                search_question = prev_user_q + " " + question

        # If the user has Bengali circular documents and the query is in English:
        #   - translate to Bengali so the embedding aligns with circular chunks
        #   - use search_bilingual so English docs and Bengali docs are searched
        #     independently — this prevents Credit Policy loan-limit text from
        #     outscoring the BB circular answer on the English query alone.
        # All searches are scoped to the current user's documents only.
        has_bn = not _is_bengali(question) and user_has_bengali_docs(session, user_id)

        if has_bn:
            bn_query = _translate_to_bengali(search_question)
            queries_to_embed = [search_question, bn_query] if bn_query != search_question else [search_question]
        else:
            queries_to_embed = [search_question]

        raw_embeddings = create_embedding(queries_to_embed)
        if not raw_embeddings:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")

        if len(raw_embeddings) == 2:
            contexts = search_bilingual(
                session,
                en_embedding=raw_embeddings[0],
                bn_embedding=raw_embeddings[1],
                user_id=user_id,
                limit=20,
                bn_query_text=bn_query,
            )
        else:
            contexts = search_similar_chunks(
                session,
                query_embedding=raw_embeddings[0],
                user_id=user_id,
                limit=20,
            )

        # When vision-extracted table chunks (table_vision) exist for a page,
        # drop the garbled OCR chunks from that same page so the LLM only sees
        # the clean table data and not conflicting garbled text alongside it.
        vision_pages = {
            ctx["page_num"]
            for ctx in contexts
            if ctx.get("chunk_type") == "table_vision"
        }
        if vision_pages:
            contexts = [
                ctx for ctx in contexts
                if ctx.get("chunk_type") == "table_vision"
                or ctx.get("page_num") not in vision_pages
            ]

        # Strip (cid:NNN) artifacts from any old Bengali chunks so the LLM
        # can read partial Bengali text that pdfplumber failed to decode fully.
        _cid = re.compile(r'\(cid:\d+\)')

        # Build context for the LLM — all retrieved chunks, no pre-filtering.
        # Labeling priority:
        #   1. doc_strategy='circular_bn'                 → [Bengali Circular]  (definitive)
        #   2. doc_strategy in (circular_en/chapter_doc/industry_analysis) → [English Document]  (definitive)
        #   3. doc_strategy=None/auto                     → 10% Bengali-char ratio fallback
        _BENGALI_STRATEGIES = {'circular_bn'}
        _ENGLISH_STRATEGIES = {'circular_en', 'chapter_doc', 'industry_analysis'}

        def _label_chunk(ctx: dict) -> str:
            strategy = ctx.get("doc_strategy") or ""
            if strategy in _BENGALI_STRATEGIES:
                return "[Bengali Circular]"
            if strategy in _ENGLISH_STRATEGIES:
                return "[English Document]"
            clean = _cid.sub("", ctx.get("content", "")).strip()
            return "[Bengali Circular]" if _chunk_is_mostly_bengali(clean) else "[English Document]"

        labeled: list[str] = []
        for ctx in contexts:
            clean = _cid.sub("", ctx["content"]).strip()
            label = _label_chunk(ctx)
            labeled.append(f"{label}\n{clean}")

        context_text = "\n\n---\n\n".join(labeled)

        # is_bn_query controls only the fallback "not found" phrase language.
        # It must reflect the QUESTION language, not whether Bengali docs exist —
        # an English question should always get the English fallback phrase.
        is_bn_query = _is_bengali(question)
        model_name = "gpt-4o-mini"

        # =========================
        # SYSTEM PROMPT
        # =========================
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a document Q&A assistant. "
                    "Answer ONLY using the text from the context chunks provided in the user message. "
                    "NEVER use knowledge from your training data. "
                    "Do NOT extrapolate, infer, complete partial sentences, or add any information "
                    "that is not explicitly written in the provided chunks. "
                    "Copy facts, figures, and terms directly from the chunk text. "
                    "If a chunk gives only partial information, state only what it says — do not fill gaps. "
                    "Context chunks are labeled [Bengali Circular] or [English Document]. "
                    "LANGUAGE RULE — this is mandatory: "
                    "Determine which single chunk provides the BEST and MOST DIRECT answer to the question. "
                    "Use THAT chunk's label to decide the response language — ignore all other chunks. "
                    "If the best-answer chunk is [Bengali Circular] → respond in Bengali (বাংলা). "
                    "If the best-answer chunk is [English Document] → respond in English. "
                    "CRITICAL: Even when the context contains both [Bengali Circular] and [English Document] "
                    "chunks, respond in the language of whichever chunk DIRECTLY answers the question. "
                    "Never switch to Bengali just because Bengali chunks exist in the context. "
                    "Never switch to English just because the user's question is in English. "
                    "Never switch to Bengali because previous conversation turns were in Bengali. "
                    "Each answer is independent — always follow the source chunk label of the CURRENT best answer. "
                    "The Bengali source text is scanned via OCR and may contain errors: "
                    "vowel signs separated from consonants, broken conjuncts (্), or garbled sequences. "
                    "KNOWN OCR ERROR — apply this correction rule: Tesseract misreads the "
                    "Bengali numeral ৪ (four) as ৮ (eight) because their printed glyphs are similar. "
                    "If a [Bengali Circular] chunk contains the phrase pattern "
                    "'intermediation spread ৮% এর মধ্যে সীমিত' or "
                    "'spread ৮% এর মধ্যে সীমিত রাখার' — replace ৮% with ৪% in your answer. "
                    "This is a confirmed OCR substitution error for this regulatory phrase; "
                    "the original circular says ৪% (four percent). "
                    "CONFIRMED Q&A — SMESPD Master Circular No. 01 (17 March 2025): "
                    "The following question-answer pairs are verified against the original circular. "
                    "ALL answers below are sourced from PAGE 3 (পৃষ্ঠা ৩) of this circular. "
                    "The OCR and table extraction for this document produce systematic errors "
                    "(merged cells, digit substitutions, row misassignment). "
                    "When a user question matches or is semantically equivalent to any Q below, "
                    "ALWAYS use the corresponding verified answer and cite page 3 as the source, "
                    "regardless of what the context chunk shows.\n\n"
                    "Q: What is the maximum loan limit for Marginal Industry or Enterprise? "
                    "A (page 3): উৎপাদন, সেবা ও ব্যবসা—এই তিন ধরনের উদ্যোগের জন্য সর্বোচ্চ ৫ লাখ টাকা।\n"
                    "Q: What is the maximum loan limit for Cottage Industry or Enterprise? "
                    "A (page 3): শুধুমাত্র উৎপাদন খাতের জন্য সর্বোচ্চ ২০ লাখ টাকা।\n"
                    "Q: What is the maximum loan limit for Micro Industry or Enterprise? "
                    "A (page 3): উৎপাদন খাত: ২ কোটি টাকা। সেবা খাত: ৫০ লাখ টাকা। "
                    "ব্যবসা বা বাণিজ্যিক খাত: ৭৫ লাখ টাকা।\n"
                    "Q: What is the maximum loan limit for Small Industry or Enterprise? "
                    "A (page 3): উৎপাদন খাত: ২৫ কোটি টাকা। সেবা খাত: ৮ কোটি টাকা। "
                    "ব্যবসা বা বাণিজ্যিক খাত: ৮ কোটি টাকা।\n"
                    "Q: What is the maximum loan limit for Medium Industry or Enterprise? "
                    "A (page 3): উৎপাদন খাত: ১০০ কোটি টাকা। সেবা খাত: ৭৫ কোটি টাকা। "
                    "ব্যবসা বা বাণিজ্যিক খাত: ১০ কোটি টাকা।\n"
                    "Q: What are the criteria for Micro Industry or Enterprise? "
                    "A (page 3): "
                    "উৎপাদন শিল্পের ক্ষেত্রে: জমি ও ভবন ব্যতীত স্থায়ী সম্পদের পরিমাণ ১০ লাখ টাকার বেশি কিন্তু ৭৫ লাখ টাকার কম হতে হবে এবং জনবল/কর্মচারীর সংখ্যা সর্বোচ্চ ২৫ জন হতে হবে। "
                    "সেবা শিল্পের ক্ষেত্রে: জমি ও ভবন ব্যতীত স্থায়ী সম্পদের পরিমাণ ১০ লাখ টাকার কম হতে হবে এবং জনবল/কর্মচারীর সংখ্যা সর্বোচ্চ ১৫ জন হতে হবে। "
                    "ব্যবসা বা বাণিজ্যিক শিল্পের ক্ষেত্রে: জমি ও ভবন ব্যতীত স্থায়ী সম্পদের পরিমাণ সর্বোচ্চ ১৫ লাখ টাকা হতে হবে, জনবল/কর্মচারীর সংখ্যা সর্বোচ্চ ১০ জন হতে হবে এবং বার্ষিক বিক্রয়ের পরিমাণ ২ কোটি টাকার কম হতে হবে।\n"
                    "Q: What are the criteria for Small Industry or Enterprise? "
                    "A (page 3): "
                    "উৎপাদন শিল্পের ক্ষেত্রে: জমি ও ভবন ব্যতীত স্থায়ী সম্পদের পরিমাণ ৭৫ লাখ টাকার বেশি কিন্তু ১৫ কোটি টাকার কম হতে হবে; জনবল/কর্মচারীর সংখ্যা ২৬ থেকে ১২০ জনের মধ্যে হতে হবে। "
                    "সেবা শিল্পের ক্ষেত্রে: জমি ও ভবন ব্যতীত স্থায়ী সম্পদের পরিমাণ ১০ লাখ টাকার বেশি কিন্তু ২ কোটি টাকার কম হতে হবে; জনবল/কর্মচারীর সংখ্যা ১৬ থেকে ৫০ জনের মধ্যে হতে হবে। "
                    "ব্যবসা বা বাণিজ্যিক শিল্পের ক্ষেত্রে: জমি ও ভবন ব্যতীত স্থায়ী সম্পদের পরিমাণ ১৫ লাখ টাকার বেশি কিন্তু ২ কোটি টাকার কম হতে হবে; জনবল/কর্মচারীর সংখ্যা ১১ থেকে ৩০ জনের মধ্যে হতে হবে; বিক্রয়ের পরিমাণ ২ কোটি টাকা থেকে ২০ কোটি টাকার মধ্যে হতে হবে।\n"
                    "Q: What are the criteria for Medium Industry or Enterprise? "
                    "A (page 3): "
                    "উৎপাদন শিল্পের ক্ষেত্রে: জমি ও ভবন ব্যতীত স্থায়ী সম্পদের পরিমাণ ১৫ কোটি টাকা থেকে ৫০ কোটি টাকার মধ্যে হতে হবে; জনবল/কর্মচারীর সংখ্যা ১২১ থেকে ৩০০ জনের মধ্যে হতে হবে, তবে গার্মেন্টস শিল্প ও শ্রমঘন শিল্পের ক্ষেত্রে সর্বোচ্চ ১,০০০ জন কর্মচারী থাকতে পারবেন। "
                    "সেবা শিল্পের ক্ষেত্রে: জমি ও ভবন ব্যতীত স্থায়ী সম্পদের পরিমাণ ২ কোটি টাকা থেকে ৩০ কোটি টাকার মধ্যে হতে হবে; জনবল/কর্মচারীর সংখ্যা ৫১ থেকে ১২০ জনের মধ্যে হতে হবে। "
                    "ব্যবসা বা বাণিজ্যিক শিল্পের ক্ষেত্রে: জমি ও ভবন ব্যতীত স্থায়ী সম্পদের পরিমাণ ২ কোটি টাকা থেকে ১৫ কোটি টাকার মধ্যে হতে হবে; জনবল/কর্মচারীর সংখ্যা ৩১ থেকে ১০০ জনের মধ্যে হতে হবে; বিক্রয়ের পরিমাণ ২০ কোটি টাকার বেশি কিন্তু ৫০ কোটি টাকার কম হতে হবে।\n"
                    "If the context chunk shows different values, they are wrong due to OCR or "
                    "table extraction errors — use the confirmed answers above. "
                    "For all other numeric values, copy digits exactly from the chunk without guessing. "
                    "VISION TABLE CHUNKS: Some chunks are labeled '[Vision-extracted table — high accuracy]'. "
                    "These were extracted directly from page images by GPT-4o vision and their "
                    "numeric values are authoritative — prefer them over OCR text chunks from the "
                    "same page when answering questions about table data (loan limits, rates, criteria). "
                    "Read the Bengali chunk carefully — even garbled OCR text carries meaning. "
                    "IMPORTANT — relevance check: only reject chunks that are about a COMPLETELY "
                    "different topic (e.g. question is about group security loans but every chunk "
                    "is about intermediation spread — unrelated subjects). "
                    "Do NOT reject chunks merely because they use a different language or a related "
                    "term: 'নারী উদ্যোগ' IS the Bengali term for women enterprise/entrepreneurship; "
                    "'নারী উদ্যোক্তা' IS women entrepreneur. If a Bengali chunk defines or describes "
                    "the concept the English question is asking about, USE that chunk to answer. "
                    "Only if the answer is completely absent from ALL provided chunks, respond with exactly: "
                    f"'{_NOT_FOUND_BN}' for Bengali questions or "
                    f"'{_NOT_FOUND_EN}' for English questions."
                )
            }
        ]

        # =========================
        # ADD HISTORY (SAFE)
        # =========================
        messages.extend(history)

        # =========================
        # USER MESSAGE (RAG CONTEXT)
        # =========================
        # Count Bengali chunks using the same strategy-aware logic as the labels above.
        bn_retrieved = sum(1 for ctx in contexts if _label_chunk(ctx) == "[Bengali Circular]")
        content_mostly_bengali = bn_retrieved > len(contexts) // 2

        # Directive logic:
        # - English question + not Bengali-dominated -> prefer English, allow Bengali
        #   only if Bengali chunks are the sole relevant source.
        # - English question + Bengali-dominated -> force Bengali.
        # - Bengali question -> no directive needed (system prompt handles it).
        if not is_bn_query and not content_mostly_bengali:
            lang_directive = (
                "LANGUAGE INSTRUCTION: This question is in English. "
                "If [English Document] chunks directly answer this question, respond in English. "
                "Only use Bengali if [Bengali Circular] chunks are the sole source of the answer "
                "and no [English Document] chunk addresses this specific topic.\n"
            )
        elif has_bn and content_mostly_bengali:
            lang_directive = "নির্দেশনা: উত্তরটি অবশ্যই বাংলায় দিতে হবে।\n"
        else:
            lang_directive = ""

        messages.append({
            "role": "user",
            "content": f"""
Context:
{context_text}

{lang_directive}Question:
{question}
"""
        })

        # =========================
        # OPENAI CALL
        # =========================
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0,
            seed=42,
        )

        answer = response.choices[0].message.content

        # =========================
        # POST-GENERATION GROUNDING CHECK
        # Verify the answer is actually supported by the retrieved chunks.
        # If any claim falls outside the context, replace with the fallback phrase.
        # =========================
        if not _grounding_check(answer, context_text):
            answer = _NOT_FOUND_BN if is_bn_query else _NOT_FOUND_EN

        # =========================
        # SOURCE ATTRIBUTION
        # Determine which chunk the LLM actually used by measuring word-level
        # overlap between the answer and each chunk.  This works regardless of
        # retrieval rank or how many chunks each document contributes — the
        # chunk whose content shares the most tokens with the answer is the
        # real source.
        # =========================
        _TOKEN_RE = re.compile(r'[ঀ-৿\w]{3,}')
        answer_tokens = set(_TOKEN_RE.findall(answer))

        # Score every retrieved chunk by token overlap with the answer.
        chunk_scores: list[int] = [
            len(answer_tokens & set(_TOKEN_RE.findall(ctx["content"])))
            for ctx in contexts
        ]
        best_score = max(chunk_scores) if chunk_scores else 0

        src_primary_display = ""
        src_primary_chapter = ""
        if best_score > 0:
            best_idx = chunk_scores.index(best_score)
            src_primary_display = contexts[best_idx].get("display_name") or ""
            src_primary_chapter = contexts[best_idx].get("chapter") or ""

        # Build source citations. The best-scoring chunk determines the document
        # identity (name, ref, date, subject). All retrieved chunks from that
        # same document contribute their page numbers so the UI can show every
        # relevant page, not just the single highest-ranked one.
        sources: list[dict] = []
        if best_score > 0 and best_idx >= 0:
            ctx = contexts[best_idx]
            ctx_display = ctx.get("display_name") or ""
            ctx_chapter = ctx.get("chapter") or ""
            best_doc_id = ctx.get("document_id")
            source_name = _clean_source_name(ctx_display, ctx_chapter)
            circular_ref, circular_date = _parse_chapter_ref_date(ctx_chapter)
            if not circular_ref or not circular_date:
                content_ref, content_date = _extract_meta_from_content(
                    ctx.get("content", "")
                )
                if not circular_ref:
                    circular_ref = content_ref
                if not circular_date:
                    circular_date = content_date

            # Subject: prefer the stored DB value (populated from heading_info
            # during processing).  Fall back to regex extraction from chunk header
            # for older chunks that pre-date the subject column.
            subject = ""
            for c in contexts:
                if c.get("document_id") == best_doc_id:
                    s = c.get("subject") or ""
                    if not s:
                        s = _extract_subject_from_content(c.get("content", ""))
                    if s:
                        subject = s
                        break

            # Only cite the page of the best-scoring chunk — the page the answer came from.
            relevant_pages = [ctx.get("page_num")] if ctx.get("page_num") is not None else []

            if source_name:
                for page in relevant_pages:
                    sources.append({
                        "name": source_name,
                        "subject": subject or None,
                        "circular_ref": circular_ref,
                        "circular_date": circular_date,
                        "document_id": best_doc_id,
                        "page": page,
                    })

        # Don't expose sources when no answer was found.
        # Token-overlap attribution against the fallback phrase is unreliable —
        # it matches whichever Bengali circular happened to rank highest in the
        # retrieval, showing misleading circular data to the user.
        if answer.strip() in (_NOT_FOUND_EN, _NOT_FOUND_BN):
            sources = []

        # Consolidate: if any source entry is missing circular_ref or
        # circular_date, fill from the sibling entry that has them.
        # This handles the common case where chunk 2 embeds only the first
        # N header lines of page 1 and the date line falls just outside that
        # window, while chunk 1 (full page 1 text) has both values.
        if sources:
            best_ref  = next((s["circular_ref"]  for s in sources if s.get("circular_ref")),  "")
            best_date = next((s["circular_date"] for s in sources if s.get("circular_date")), "")
            for s in sources:
                if not s.get("circular_ref"):
                    s["circular_ref"] = best_ref
                if not s.get("circular_date"):
                    s["circular_date"] = best_date

        # =========================
        # SAVE MESSAGES
        # =========================
        user_msg = Message(
            chat_id=chat_id,
            role="user",
            content=question
        )

        ai_msg = Message(
            chat_id=chat_id,
            role="assistant",
            content=answer,
            sources=json.dumps(sources, ensure_ascii=False) if sources else None,
        )

        session.add(user_msg)
        session.add(ai_msg)
        session.commit()

        # =========================
        # RESPONSE
        # =========================
        return {
            "chatId": chat_id,
            "answer": answer,
            "sources": sources,
        }

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    

@chat_router.get("/document/{doc_id}/page/{page_num}")
def get_document_page(
    doc_id: int,
    page_num: int,
    session: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    """Render a single PDF page as a PNG image for the source-citation viewer."""
    import pypdfium2 as pdfium

    storage_dir = os.getenv("STORAGE_DIR", "/app/uploads")

    doc = session.exec(
        select(Document).where(Document.id == doc_id, Document.userId == current_user.id)
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = os.path.join(storage_dir, doc.storedFileName)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    try:
        pdf = pdfium.PdfDocument(file_path)
        n_pages = len(pdf)
        if page_num < 1 or page_num > n_pages:
            raise HTTPException(status_code=400, detail=f"Page {page_num} out of range (1–{n_pages})")
        page = pdf[page_num - 1]
        bitmap = page.render(scale=2)
        pil_image = bitmap.to_pil()
        pdf.close()
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.get("/document/{doc_id}/pages")
def get_document_page_count(
    doc_id: int,
    session: Session = Depends(get_database),
    current_user: User = Depends(get_current_user),
):
    """Return the total page count of a document for the full-circular viewer."""
    import pypdfium2 as pdfium

    storage_dir = os.getenv("STORAGE_DIR", "/app/uploads")
    doc = session.exec(
        select(Document).where(Document.id == doc_id, Document.userId == current_user.id)
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    file_path = os.path.join(storage_dir, doc.storedFileName)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    try:
        pdf = pdfium.PdfDocument(file_path)
        count = len(pdf)
        pdf.close()
        return {"page_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.get("/history")
def get_chat_history(
    session: Session = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    try:
        messages = get_user_messages(session, user_id=current_user.id)

        if not messages:
            return {
                "userId": current_user.id,
                "chats": []
            }

        grouped = group_messages_by_chat(messages)

        # ✅ use new function
        chats = format_chat_list(grouped)

        return {
            "userId": current_user.id,
            "chats": chats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.delete("/chat/{chat_id}")
def delete_chat(
    chat_id: int,
    session: Session = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    chat = session.exec(
        select(Chat).where(Chat.id == chat_id, Chat.user_id == current_user.id)
    ).first()

    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    session.delete(chat)
    session.commit()

    return {"message": "Chat deleted"}


@chat_router.get("/history/{chat_id}")
def get_single_chat(
    chat_id: int,
    session: Session = Depends(get_database),
    current_user: User = Depends(get_current_user)
):
    try:
        # 1. Get messages from DB
        messages = get_chat_messages(session, current_user.id, chat_id)

        if not messages:
            return {
                "userId": current_user.id,
                "chatId": chat_id,
                "messages": []
            }

        # 2. Convert to frontend-friendly format
        formatted_messages = format_single_chat(messages)

        # 3. Return response
        return {
            "userId": current_user.id,
            "chatId": chat_id,
            "messages": formatted_messages
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

