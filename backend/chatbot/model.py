from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Column, ForeignKey


if TYPE_CHECKING:
    from user.model import User

class Chat(SQLModel, table=True):
    __tablename__ = "chat"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(
    sa_column=Column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False)
    )
    user: Optional["User"] = Relationship(back_populates="chats")
    messages: List["Message"] = Relationship(
        back_populates="chat",
        sa_relationship_kwargs={"cascade": "all, delete"}
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"name": "createdAt"}
    )
    


class Message(SQLModel, table=True):
    __tablename__ = "message"

    id: Optional[int] = Field(default=None, primary_key=True)
    chat_id: int = Field(
    sa_column=Column(
        ForeignKey("chat.id", ondelete="CASCADE"),
        nullable=False
    )
    )
    role: str
    content: str
    chat: Optional["Chat"] = Relationship(back_populates="messages")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"name": "createdAt"}
    )
    


CHUNK_STRATEGIES = {"auto", "circular_bn", "circular_en", "chapter_doc", "industry_analysis"}


class Document(SQLModel, table=True):
    __tablename__ = "document"

    id: int | None = Field(default=None, primary_key=True)
    userId: int = Field(foreign_key="users.id", index=True)
    division: str = Field(default="SME")
    department: str = Field(default="CRM")
    displayName: str
    fileName: str
    storedFileName: str
    fileExt: str
    processed: bool = Field(default=False)
    chunk_strategy: Optional[str] = Field(default=None)
    createdAt: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
