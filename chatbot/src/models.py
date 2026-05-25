import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Quan hệ một-nhiều với ChatSession
    sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Quan hệ một-nhiều với ChatMessage
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    # Quan hệ nhiều-một với User
    user = relationship("User", back_populates="sessions")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(10), nullable=False)  # "user" hoặc "bot"
    message = Column(Text, nullable=False)
    intent = Column(String(50), nullable=True)     # Intent dự đoán được (chỉ có ở bot)
    confidence = Column(Float, nullable=True)     # Độ tin cậy của dự đoán (chỉ có ở bot)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Quan hệ ngược lại với ChatSession
    session = relationship("ChatSession", back_populates="messages")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    expires_at = Column(DateTime, nullable=False)

    # Quan hệ với User
    user = relationship("User")


class BotResponse(Base):
    __tablename__ = "bot_responses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tag = Column(String(50), unique=True, nullable=False, index=True)
    category = Column(String(50), nullable=False)  # Ví dụ: "general", "sales", "health"
    responses = Column(Text, nullable=False)       # Lưu trữ danh sách câu trả lời dưới dạng chuỗi JSON
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

