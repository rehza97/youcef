from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class Message(Base):
    """Message model for messaging"""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey(
        "conversations.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)  # Now encrypted
    # text, image, file, audio, video
    message_type = Column(String(50), default="text")
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    # Additional message data (file info, etc.) - also encrypted
    message_metadata = Column(JSON, nullable=True)
    # New security fields
    content_hash = Column(String(64), nullable=True)  # SHA-256 hash for integrity
    encryption_version = Column(String(10), default="v1")  # Track encryption version
    reply_to_id = Column(Integer, ForeignKey("messages.id"), nullable=True)  # Message threading
    thread_id = Column(String(36), nullable=True)  # Thread grouping
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    sender = relationship("User", foreign_keys=[
                          sender_id], back_populates="sent_messages")
    reactions = relationship("MessageReaction", back_populates="message")
    # Self-referential relationship for threading
    replies = relationship("Message", remote_side=[id], backref="parent_message")
    read_receipts = relationship("MessageReadReceipt", back_populates="message")


class MessageReaction(Base):
    """Message reactions model"""
    __tablename__ = "message_reactions"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # emoji or reaction type
    reaction_type = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("Message", back_populates="reactions")
    user = relationship("User")


class MessageReadReceipt(Base):
    """Message read receipts model"""
    __tablename__ = "message_read_receipts"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    read_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("Message", back_populates="read_receipts")
    user = relationship("User")

# Pydantic models for API


class MessageBase(BaseModel):
    content: str
    message_type: str = "text"
    message_metadata: Optional[Dict[str, Any]] = None


class MessageCreate(MessageBase):
    conversation_id: int


class MessageUpdate(BaseModel):
    content: Optional[str] = None
    message_type: Optional[str] = None
    message_metadata: Optional[Dict[str, Any]] = None
    is_edited: Optional[bool] = None


class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    sender_id: int
    is_edited: bool
    is_deleted: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    sender_username: Optional[str] = None
    reactions_count: Optional[int] = None

    class Config:
        from_attributes = True


class MessageReactionCreate(BaseModel):
    message_id: int
    reaction_type: str


class MessageReactionResponse(BaseModel):
    id: int
    message_id: int
    user_id: int
    reaction_type: str
    created_at: datetime
    user_username: Optional[str] = None

    class Config:
        from_attributes = True


class MessageWithReactions(MessageResponse):
    reactions: List[MessageReactionResponse] = []
