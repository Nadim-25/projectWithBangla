from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from openai import OpenAI
import os
from typing import Optional, List
from utils.database import get_database
from chatbot.model import Chat, Message
from chatbot.embeddings import create_embedding
from chatbot.search import search_similar_chunks
from chatbot.getchat import get_user_messages, group_messages_by_chat, format_chat_list
from chatbot.getchatbychatid import get_chat_messages, format_single_chat
from user.model import User
from user.router import get_current_user


chat_router = APIRouter()


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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
        raw_embeddings = create_embedding([question])
        if not raw_embeddings:
            raise HTTPException(status_code=500, detail="Failed to generate query embedding")
        query_embedding = raw_embeddings[0]

        contexts = search_similar_chunks(
            session,
            query_embedding=query_embedding,
            limit=5
        )

        context_text = "\n\n".join(contexts)

        # =========================
        # SYSTEM PROMPT
        # =========================
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful AI assistant. "
                    "Use ONLY the provided context. "
                    "If answer is not in context, say: 'I don't know based on the document.'"
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
        messages.append({
            "role": "user",
            "content": f"""
Context:
{context_text}

Question:
{question}
"""
        })

        # =========================
        # OPENAI CALL
        # =========================
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )

        answer = response.choices[0].message.content

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
            "answer": answer
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

