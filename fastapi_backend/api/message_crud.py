from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from database.connection import get_db
from core.security import get_current_user
from models.conversation import ConversationParticipant
from models.message import Message, MessageResponse
from models.user import User
from services.notification_service import NotificationService
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

message_crud_router = APIRouter()


class MessageCreateRequest(BaseModel):
    content: str
    message_type: str = "text"
    message_metadata: dict = None


class MessagesListResponse(BaseModel):
    messages: List[MessageResponse]


@message_crud_router.get("/conversations/{conversation_id}/messages", response_model=MessagesListResponse)
async def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all messages for a conversation"""
    try:
        # Check if user is participant
        participant = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == current_user.id
        ).first()

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view messages in this conversation"
            )

        # Get messages
        messages = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.asc()).all()

        message_responses = []
        for message in messages:
            message_responses.append(MessageResponse.from_orm(message))

        return MessagesListResponse(messages=message_responses)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving messages"
        )


@message_crud_router.post("/conversations/{conversation_id}/messages", response_model=dict)
async def send_message(
    conversation_id: int,
    message_data: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to a conversation"""
    try:
        # Check if user is participant
        participant = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == current_user.id
        ).first()

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to send messages to this conversation"
            )

        # Create message
        message = Message(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            content=message_data.content,
            message_type=message_data.message_type,
            message_metadata=message_data.message_metadata,
            created_at=datetime.utcnow()
        )

        db.add(message)
        db.commit()
        db.refresh(message)

        # Send notifications to other participants
        try:
            other_participants = db.query(ConversationParticipant).filter(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id != current_user.id
            ).all()

            for participant in other_participants:
                await NotificationService.notify_new_message(
                    db=db,
                    user_id=participant.user_id,
                    message_id=message.id,
                    sender_name=current_user.username
                )
        except Exception as e:
            logger.error(f"Error sending message notifications: {e}")

        return {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "sender_id": message.sender_id,
            "content": message.content,
            "message_type": message.message_type,
            "created_at": message.created_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating message: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating message"
        )


@message_crud_router.get("/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific message by ID"""
    try:
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )

        # Check if user is participant in the conversation
        participant = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == message.conversation_id,
            ConversationParticipant.user_id == current_user.id
        ).first()

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this message"
            )

        return MessageResponse.from_orm(message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving message"
        )


@message_crud_router.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a message (only sender can delete)"""
    try:
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )

        # Only sender can delete the message
        if message.sender_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only message sender can delete this message"
            )

        db.delete(message)
        db.commit()

        return {"message": "Message deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting message"
        )