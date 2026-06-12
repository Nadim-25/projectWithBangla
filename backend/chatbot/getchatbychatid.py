from sqlmodel import select
from chatbot.model import Message, Chat

def get_chat_messages(session, user_id: int, chat_id: int):
    statement = (
        select(Message)
        .join(Chat, Message.chat_id == Chat.id)
        .where(
            Chat.user_id == user_id,   # ✅ user filter
            Chat.id == chat_id         # ✅ chat filter
        )
        .order_by(Message.created_at)
    )

    return session.exec(statement).all()

def format_single_chat(messages):
    result = []

    for msg in messages:
        if msg.role == "user":
            result.append({
                "question": msg.content,
                "answer": None
            })

        elif msg.role == "assistant":
            if result and result[-1]["answer"] is None:
                result[-1]["answer"] = msg.content

    return result