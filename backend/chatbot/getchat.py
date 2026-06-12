from sqlmodel import Session, select
from chatbot.model import Message
from collections import defaultdict


from sqlmodel import select
from chatbot.model import Message, Chat


def get_user_messages(session, user_id: int):
    statement = (
        select(Message)
        .join(Chat, Message.chat_id == Chat.id)  # ✅ JOIN
        .where(Chat.user_id == user_id)          # ✅ filter on Chat
        .order_by(Message.chat_id, Message.created_at)
    )

    return session.exec(statement).all()


def group_messages_by_chat(messages):
    grouped = defaultdict(list)

    for msg in messages:
        grouped[msg.chat_id].append({
            "role": msg.role,
            "content": msg.content,
            "time": msg.created_at
        })

    return grouped

def format_chat_history(grouped_messages):
    result = {}

    for chat_id, messages in grouped_messages.items():
        conversation = []

        for msg in messages:
            if msg["role"] == "user":
                conversation.append({
                    "question": msg["content"]
                })

            elif msg["role"] == "assistant":
                # attach answer to last question
                if conversation:
                    conversation[-1]["answer"] = msg["content"]

        result[chat_id] = conversation

    return result


def format_chat_list(grouped_messages):
    chats = []

    for chat_id, messages in grouped_messages.items():

        # ✅ first user question
        first_question = next(
            (m["content"] for m in messages if m["role"] == "user"),
            "New Chat"
        )

        chats.append({
            "chatId": chat_id,
            "title": first_question[:30],
            "messageCount": len(messages),
            "lastMessage": messages[-1]["content"] if messages else "",
            "createdAt": messages[0]["time"] if messages else None
        })

    # ✅ latest first
    chats.sort(key=lambda x: x["createdAt"], reverse=True)

    return chats

def format_single_chat(messages):
    result = []

    for m in messages:
        result.append({
            "role": "user",
            "content": m.question
        })
        result.append({
            "role": "assistant",
            "content": m.answer
        })

    return result