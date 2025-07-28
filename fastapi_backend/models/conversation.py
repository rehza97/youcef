from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class Conversation(Base):
    """Conversation model for messaging"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)  # For group conversations
    conversation_type = Column(String(50), default="direct")  # direct, group
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    # Additional conversation data
    conversation_metadata = Column(JSON, nullable=True)

    # Relationships
    participants = relationship(
        "ConversationParticipant", back_populates="conversation")
    messages = relationship("Message", back_populates="conversation")


class ConversationParticipant(Base):
    """Conversation participants relationship"""
    __tablename__ = "conversation_participants"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey(
        'conversations.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    is_admin = Column(Boolean, default=False)  # For group conversations
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    left_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="participants")
    user = relationship("User", back_populates="conversations")

# Pydantic models for API


class ConversationBase(BaseModel):
    name: Optional[str] = None
    conversation_type: str = "direct"
    conversation_metadata: Optional[Dict[str, Any]] = None


class ConversationCreate(ConversationBase):
    participant_ids: List[int]


class ConversationUpdate(BaseModel):
    name: Optional[str] = None
    conversation_type: Optional[str] = None
    is_active: Optional[bool] = None
    conversation_metadata: Optional[Dict[str, Any]] = None


class ConversationResponse(ConversationBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    participant_count: Optional[int] = None

    class Config:
        from_attributes = True


class ConversationParticipantCreate(BaseModel):
    conversation_id: int
    user_id: int
    is_admin: bool = False


class ConversationParticipantResponse(BaseModel):
    id: int
    conversation_id: int
    user_id: int
    is_admin: bool
    joined_at: datetime
    left_at: Optional[datetime] = None

    class Config:
        from_attributes = True
