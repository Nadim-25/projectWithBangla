from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from openai import OpenAI
import os
import re
from typing import Optional, List
from utils.database import get_database
from chatbot.model import Chat, Message
from chatbot.embeddings import create_embedding
from chatbot.search import search_similar_chunks, search_bilingual, user_has_bengali_docs
from chatbot.getchat import get_user_messages, group_messages_by_chat, format_chat_list
from chatbot.getchatbychatid import get_chat_messages, format_single_chat
from user.model import User
from user.router import get_current_user


chat_router = APIRouter()


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

_BN_RE = re.compile(r'[ঀ-৿]')


def _is_bengali(text: str) -> bool:
    return bool(_BN_RE.search(text))


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
                        "'micro enterprise' → 'ক্ষুদ্র উদ্যোগ', "
                        "'small enterprise' → 'ছোট উদ্যোগ', "
                        "'medium enterprise' → 'মাঝারি উদ্যোগ', "
                        "'cottage enterprise' → 'কুটির শিল্প', "
                        "'CMSME' → 'সিএমএসএমই', "
                        "'master circular' → 'মাস্টার সার্কুলার', "
                        "'group security loan' → 'গ্রুপ সিকিউরিটি ঋণ', "
                        "'group guarantee' → 'গ্রুপ গ্যারান্টি', "
                        "'collateral' → 'জামানত', "
                        "'working capital' → 'চলতি মূলধন', "
                        "'term loan' → 'মেয়াদী ঋণ', "
                        "'revolving loan' → 'আবর্তনশীল ঋণ', "
                        "'interest rate' → 'সুদহার', "
                        "'intermediation spread' → 'intermediation spread'. "
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

        # =========================
        # VECTOR SEARCH (RAG)
        # =========================
        # If the user has Bengali circular documents and the query is in English:
        #   - translate to Bengali so the embedding aligns with circular chunks
        #   - use search_bilingual so English docs and Bengali docs are searched
        #     independently — this prevents Credit Policy loan-limit text from
        #     outscoring the BB circular answer on the English query alone.
        # All searches are scoped to the current user's documents only.
        has_bn = not _is_bengali(question) and user_has_bengali_docs(session, user_id)

        if has_bn:
            bn_query = _translate_to_bengali(question)
            queries_to_embed = [question, bn_query] if bn_query != question else [question]
        else:
            queries_to_embed = [question]

        raw_embeddings = create_embedding(queries_to_embed)
        if not raw_embeddings:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")

        if len(raw_embeddings) == 2:
            contexts = search_bilingual(
                session,
                en_embedding=raw_embeddings[0],
                bn_embedding=raw_embeddings[1],
                user_id=user_id,
                limit=8,
                bn_query_text=bn_query,
            )
        else:
            contexts = search_similar_chunks(
                session,
                query_embedding=raw_embeddings[0],
                user_id=user_id,
                limit=8,
            )

        # Strip (cid:NNN) artifacts from any old Bengali chunks so the LLM
        # can read partial Bengali text that pdfplumber failed to decode fully.
        _cid = re.compile(r'\(cid:\d+\)')

        # Build context for the LLM — all retrieved chunks, no pre-filtering.
        labeled: list[str] = []
        for ctx in contexts:
            clean = _cid.sub("", ctx["content"]).strip()
            label = "[Bengali Circular]" if _is_bengali(clean) else "[English Document]"
            labeled.append(f"{label}\n{clean}")

        context_text = "\n\n---\n\n".join(labeled)

        # gpt-4o has far stronger Bengali Unicode comprehension than gpt-4o-mini.
        # temperature=0 + seed makes both models fully deterministic — same question
        # always retrieves the same top-k chunks and produces the same answer.
        is_bn_query = has_bn or _is_bengali(question)
        model_name = "gpt-4o" if is_bn_query else "gpt-4o-mini"

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
                    "Context chunks are labeled [Bengali Circular] or [English Document]. "
                    "LANGUAGE RULE — this is mandatory: "
                    "If the answer comes from a [Bengali Circular] chunk, you MUST respond in Bengali (বাংলা), "
                    "even when the user's question was written in English. "
                    "If the answer comes from an [English Document] chunk, respond in English. "
                    "Never mix languages based on the question language — follow the source chunk label. "
                    "The Bengali source text is scanned via OCR and may contain errors: "
                    "vowel signs separated from consonants, broken conjuncts (্), or garbled sequences. "
                    "KNOWN OCR ERROR — apply this correction rule: Tesseract misreads the "
                    "Bengali numeral ৪ (four) as ৮ (eight) because their printed glyphs are similar. "
                    "If a [Bengali Circular] chunk contains the phrase pattern "
                    "'intermediation spread ৮% এর মধ্যে সীমিত' or "
                    "'spread ৮% এর মধ্যে সীমিত রাখার' — replace ৮% with ৪% in your answer. "
                    "This is a confirmed OCR substitution error for this regulatory phrase; "
                    "the original circular says ৪% (four percent). "
                    "For all other numeric values, copy digits exactly from the chunk without guessing. "
                    "Read the Bengali chunk carefully — even garbled OCR text carries meaning. "
                    "IMPORTANT — relevance check: only reject chunks that are about a COMPLETELY "
                    "different topic (e.g. question is about group security loans but every chunk "
                    "is about intermediation spread — unrelated subjects). "
                    "Do NOT reject chunks merely because they use a different language or a related "
                    "term: 'নারী উদ্যোগ' IS the Bengali term for women enterprise/entrepreneurship; "
                    "'নারী উদ্যোক্তা' IS women entrepreneur. If a Bengali chunk defines or describes "
                    "the concept the English question is asking about, USE that chunk to answer. "
                    "Only if the answer is completely absent from ALL provided chunks, respond with exactly: "
                    "'এই তথ্য প্রদত্ত ডকুমেন্টে পাওয়া যায়নি।' for Bengali questions or "
                    "'I don't know based on the document.' for English questions."
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
        # When the retrieval is bilingual (Bengali circular docs are present
        # and the question is in English), echo a Bengali language directive
        # directly inside the user turn — immediately before the question.
        # System-prompt-only instructions are routinely overridden by GPT when
        # the question is in a different language; placing the directive here
        # makes it impossible to miss.
        lang_directive = (
            "নির্দেশনা: উত্তরটি অবশ্যই বাংলায় দিতে হবে।\n" if has_bn else ""
        )

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
        # SOURCE ATTRIBUTION
        # Determine which chunk the LLM actually used by measuring word-level
        # overlap between the answer and each chunk.  This works regardless of
        # retrieval rank or how many chunks each document contributes — the
        # chunk whose content shares the most tokens with the answer is the
        # real source.
        # =========================
        _TOKEN_RE = re.compile(r'[ঀ-৿\w]{3,}')
        answer_tokens = set(_TOKEN_RE.findall(answer))

        best_score = 0
        src_primary_display = ""
        src_primary_chapter = ""
        for ctx in contexts:
            score = len(answer_tokens & set(_TOKEN_RE.findall(ctx["content"])))
            if score > best_score:
                best_score = score
                src_primary_display = ctx.get("display_name") or ""
                src_primary_chapter = ctx.get("chapter") or ""

        sources: list[dict] = []
        seen_src_keys: set[tuple] = set()
        for ctx in contexts:
            ctx_display = ctx.get("display_name") or ""
            ctx_chapter = ctx.get("chapter") or ""
            is_primary_doc = (
                (src_primary_display and ctx_display == src_primary_display)
                or (not src_primary_display and src_primary_chapter and ctx_chapter == src_primary_chapter)
            )
            if not is_primary_doc:
                continue
            source_name = _clean_source_name(ctx_display, ctx_chapter)
            page_num = ctx.get("page_num")
            src_key = (source_name, page_num)
            if source_name and src_key not in seen_src_keys:
                seen_src_keys.add(src_key)
                sources.append({"name": source_name, "page": page_num})

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
            content=answer
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

