from sqlalchemy import Column, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.connection import Base
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserBlock(Base):
    """User blocking model"""
    __tablename__ = "user_blocks"

    id = Column(Integer, primary_key=True, index=True)
    blocker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    blocked_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    blocker = relationship("User", foreign_keys=[
                           blocker_id], back_populates="blocked_users")
    blocked = relationship("User", foreign_keys=[
                           blocked_id], back_populates="blocked_by")

# Pydantic models for API


class UserBlockCreate(BaseModel):
    blocked_id: int
    reason: Optional[str] = None


class UserBlockResponse(BaseModel):
    id: int
    blocker_id: int
    blocked_id: int
    reason: Optional[str] = None
    created_at: datetime
    blocker_username: Optional[str] = None
    blocked_username: Optional[str] = None

    class Config:
        from_attributes = True
