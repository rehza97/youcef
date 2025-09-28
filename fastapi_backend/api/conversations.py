from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from database.connection import get_db
from core.security import get_current_user
from models.conversation import (
    Conversation, ConversationCreate, ConversationResponse,
    ConversationParticipant, ConversationParticipantCreate
)
from models.user import User
from services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)

conversations_router = APIRouter()

# Response models


class ConversationsListResponse(BaseModel):
    conversations: List[ConversationResponse]

# Request Models


class ConversationCreateRequest(BaseModel):
    name: Optional[str] = None
    conversation_type: str = "group"
    conversation_metadata: Optional[Dict[str, Any]] = None
    participant_ids: List[int] = []


@conversations_router.get("/", response_model=ConversationsListResponse)
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all conversations for the current user"""
    try:
        # Get conversations where user is a participant
        conversations = db.query(Conversation).join(
            ConversationParticipant,
            Conversation.id == ConversationParticipant.conversation_id
        ).filter(
            ConversationParticipant.user_id == current_user.id
        ).all()

        conversation_responses = []
        for conv in conversations:
            conversation_responses.append(ConversationResponse.from_orm(conv))

        return ConversationsListResponse(conversations=conversation_responses)
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conversations"
        )


@conversations_router.post("/")
async def create_conversation(
    conversation_data: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation"""
    try:
        # Create conversation
        conversation = Conversation(
            name=conversation_data.name,
            conversation_type=conversation_data.conversation_type,
            conversation_metadata=conversation_data.conversation_metadata,
            created_by=current_user.id,
            created_at=datetime.utcnow()
        )

        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        # Add creator as participant
        creator_participant = ConversationParticipant(
            conversation_id=conversation.id,
            user_id=current_user.id,
            joined_at=datetime.utcnow()
        )
        db.add(creator_participant)

        # Add other participants
        for participant_id in conversation_data.participant_ids:
            if participant_id != current_user.id:  # Don't add creator twice
                participant = ConversationParticipant(
                    conversation_id=conversation.id,
                    user_id=participant_id,
                    joined_at=datetime.utcnow()
                )
                db.add(participant)

        db.commit()

        # Send notifications to participants
        try:
            for participant_id in conversation_data.participant_ids:
                if participant_id != current_user.id:
                    await NotificationService.notify_conversation_created(
                        db=db,
                        user_id=participant_id,
                        conversation_id=conversation.id,
                        creator_name=current_user.username
                    )
        except Exception as e:
            logger.error(f"Error sending conversation notifications: {e}")

        return {
            "id": conversation.id,
            "name": conversation.name,
            "conversation_type": conversation.conversation_type,
            "created_by": conversation.created_by,
            "created_at": conversation.created_at.isoformat()
        }

    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating conversation"
        )


@conversations_router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific conversation"""
    try:
        # Check if user is participant
        participant = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == current_user.id
        ).first()

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this conversation"
            )

        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        return ConversationResponse.from_orm(conversation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conversation"
        )


@conversations_router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    conversation_data: ConversationCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a conversation (creator only)"""
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        if conversation.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only conversation creator can update"
            )

        # Update fields
        if conversation_data.name is not None:
            conversation.name = conversation_data.name
        if conversation_data.conversation_metadata is not None:
            conversation.conversation_metadata = conversation_data.conversation_metadata

        conversation.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(conversation)

        return ConversationResponse.from_orm(conversation)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating conversation: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating conversation"
        )


@conversations_router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation (creator only)"""
    try:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        if conversation.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only conversation creator can delete"
            )

        # Delete conversation (cascades to participants and messages)
        db.delete(conversation)
        db.commit()

        return {"message": "Conversation deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting conversation"
        )



