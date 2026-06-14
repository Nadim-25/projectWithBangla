from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime, timezone
from typing import List, TYPE_CHECKING, Optional
from chatbot.model import Chat


if TYPE_CHECKING:
    from chatbot.model import Chat


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    fullName: str
    userName: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    hashedPassword: str
    role: str = Field(default="user")
    division: str = Field(default="SME")
    department: str = Field(default="CRM")
    isVerified: bool = Field(default=False)
    isActive: bool = Field(default=True)
    refreshToken: Optional[str] = None
    accessToken: Optional[str] = None
    accessTokenExpiry: Optional[datetime] = None
    requiresPasswordChange: bool = Field(default=False, nullable= True)
    createdAt: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updatedAt: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    chats: List["Chat"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

