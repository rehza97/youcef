from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
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
from models.message import (
    Message, MessageCreate, MessageResponse, MessageReaction,
    MessageReactionCreate, MessageWithReactions
)
from models.user_block import UserBlock, UserBlockCreate
from models.user import User
from models.file_upload import FileUpload
from services.notification_service import NotificationService
import os
import uuid
import json
import logging

logger = logging.getLogger(__name__)

messaging_router = APIRouter()

# Response models for the wrapped responses


class ConversationsListResponse(BaseModel):
    conversations: List[ConversationResponse]


class MessagesListResponse(BaseModel):
    messages: List[MessageResponse]


# Request Models
class ConversationCreate(BaseModel):
    name: Optional[str] = None
    conversation_type: str = "group"
    conversation_metadata: Optional[Dict[str, Any]] = None
    participant_ids: List[int] = []


class MessageCreate(BaseModel):
    content: str
    message_type: str = "text"
    message_metadata: Optional[Dict[str, Any]] = None


class BlockUserRequest(BaseModel):
    blocked_id: int
    reason: Optional[str] = ""


class UnblockUserRequest(BaseModel):
    blocked_id: int


@messaging_router.get("/conversations", response_model=ConversationsListResponse)
async def get_conversations(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user conversations"""
    conversations = db.query(Conversation).join(ConversationParticipant).filter(
        ConversationParticipant.user_id == current_user.id,
        ConversationParticipant.left_at.is_(None)
    ).all()

    # Add participant count to each conversation
    for conv in conversations:
        conv.participant_count = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conv.id,
            ConversationParticipant.left_at.is_(None)
        ).count()

    return {"conversations": conversations}


@messaging_router.post("/conversations")
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation"""
    try:
        logger.info(f"Creating conversation for user {current_user.id}")
        logger.debug(f"Conversation data: {conversation_data}")

        # Validate participant IDs exist
        if conversation_data.participant_ids:
            existing_users = db.query(User).filter(
                User.id.in_(conversation_data.participant_ids)
            ).all()
            existing_user_ids = [user.id for user in existing_users]
            invalid_ids = [
                uid for uid in conversation_data.participant_ids if uid not in existing_user_ids]

            if invalid_ids:
                logger.error(f"Invalid participant IDs: {invalid_ids}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid participant IDs: {invalid_ids}"
                )

        # Create conversation
        conversation = Conversation(
            name=conversation_data.name,
            conversation_type=conversation_data.conversation_type,
            conversation_metadata=conversation_data.conversation_metadata
        )

        logger.debug(f"Created conversation object: {conversation}")
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        logger.info(f"Conversation saved with ID: {conversation.id}")

        # Add current user as participant
        current_user_participant = ConversationParticipant(
            conversation_id=conversation.id,
            user_id=current_user.id,
            is_admin=True
        )
        db.add(current_user_participant)

        # Add other participants
        # Include current user for notifications
        participant_ids = [current_user.id]
        for user_id in conversation_data.participant_ids:
            if user_id != current_user.id:  # Don't add current user twice
                participant = ConversationParticipant(
                    conversation_id=conversation.id,
                    user_id=user_id,
                    is_admin=False
                )
                db.add(participant)
                participant_ids.append(user_id)

        db.commit()

        # Send real-time notification to participants
        await NotificationService.notify_conversation_created(
            db=db,
            creator_id=current_user.id,
            participant_ids=participant_ids,
            conversation_name=conversation.name or f"Conversation {conversation.id}"
        )

        # Prepare response
        response_data = {
            "id": conversation.id,
            "name": conversation.name,
            "conversation_type": conversation.conversation_type,
            "is_active": conversation.is_active,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
            "participant_count": len(participant_ids)
        }

        return {"message": "Conversation created successfully", "data": response_data}

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating conversation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating conversation"
        )


@messaging_router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific conversation"""
    # Check if user is participant
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == current_user.id,
        ConversationParticipant.left_at.is_(None)
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this conversation"
        )

    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    return conversation


@messaging_router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    conversation_update: ConversationCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a conversation"""
    # Check if user is admin of the conversation
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == current_user.id,
        ConversationParticipant.is_admin == True,
        ConversationParticipant.left_at.is_(None)
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not an admin of this conversation"
        )

    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # Update conversation fields
    for field, value in conversation_update.dict(exclude_unset=True).items():
        if field != "participant_ids":  # Don't update participant_ids here
            setattr(conversation, field, value)

    try:
        db.commit()
        db.refresh(conversation)
        return conversation
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating conversation"
        )


@messaging_router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation"""
    # Check if user is admin of the conversation
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == current_user.id,
        ConversationParticipant.is_admin == True,
        ConversationParticipant.left_at.is_(None)
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not an admin of this conversation"
        )

    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    try:
        # Soft delete by setting is_active to False
        conversation.is_active = False
        db.commit()
        return {"message": "Conversation deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting conversation"
        )


@messaging_router.get("/conversations/{conversation_id}/messages", response_model=MessagesListResponse)
async def get_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages from a conversation"""
    # Check if user is participant
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == current_user.id,
        ConversationParticipant.left_at.is_(None)
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this conversation"
        )

    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.is_deleted == False
    ).order_by(Message.created_at.desc()).offset(skip).limit(limit).all()

    # Add sender username to each message
    for msg in messages:
        sender = db.query(User).filter(User.id == msg.sender_id).first()
        msg.sender_username = sender.username if sender else None

        # Add reactions count
        msg.reactions_count = db.query(MessageReaction).filter(
            MessageReaction.message_id == msg.id
        ).count()

    return {"messages": messages}


@messaging_router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    message_data: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to a conversation"""
    try:
        # Verify conversation exists and user is participant
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()

        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # Check if user is participant
        participant = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == current_user.id
        ).first()

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a participant of this conversation"
            )

        # Create message
        message = Message(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            content=message_data.get("content", ""),
            message_type=message_data.get("message_type", "text"),
            message_metadata=message_data.get("message_metadata")
        )

        db.add(message)
        db.commit()
        db.refresh(message)

        # Get conversation participants for notifications
        participants = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation_id
        ).all()
        participant_ids = [p.user_id for p in participants]

        # Send real-time notification to other participants
        await NotificationService.notify_message_sent(
            db=db,
            sender_id=current_user.id,
            conversation_id=conversation_id,
            message_content=message.content,
            participants=participant_ids
        )

        # Prepare response
        response_data = {
            "id": message.id,
            "conversation_id": message.conversation_id,
            "sender_id": message.sender_id,
            "sender_username": current_user.username,
            "content": message.content,
            "message_type": message.message_type,
            "created_at": message.created_at.isoformat(),
            "updated_at": message.updated_at.isoformat() if message.updated_at else None,
            "is_edited": message.is_edited,
            "is_deleted": message.is_deleted
        }

        return {"message": "Message sent successfully", "data": response_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@messaging_router.post("/send-file", response_model=MessageResponse)
async def send_file_message(
    file: UploadFile = File(...),
    conversation_id: int = Form(...),
    message_type: str = Form("file"),
    content: str = Form(""),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a file message to a conversation"""
    if not conversation_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conversation ID is required"
        )

    # Check if user is participant
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == conversation_id,
        ConversationParticipant.user_id == current_user.id,
        ConversationParticipant.left_at.is_(None)
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this conversation"
        )

    # Create uploads directory if it doesn't exist
    upload_dir = "uploads/messages"
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(upload_dir, unique_filename)

    try:
        # Save file
        with open(file_path, "wb") as buffer:
            content_data = await file.read()
            buffer.write(content_data)

        # Create message with file metadata
        message_metadata = {
            "original_filename": file.filename,
            "file_path": file_path,
            "file_size": len(content_data),
            "file_type": file.content_type
        }

        message = Message(
            conversation_id=conversation_id,
            sender_id=current_user.id,
            content=content or f"Fichier: {file.filename}",
            message_type=message_type,
            message_metadata=message_metadata
        )

        db.add(message)
        db.commit()
        db.refresh(message)
        return message

    except Exception as e:
        # Clean up file if message creation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending file message"
        )


@messaging_router.get("/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific message"""
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.is_deleted == False
    ).first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

    # Check if user is participant in the conversation
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == message.conversation_id,
        ConversationParticipant.user_id == current_user.id,
        ConversationParticipant.left_at.is_(None)
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this conversation"
        )

    return message


@messaging_router.put("/messages/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: int,
    message_update: MessageCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a message"""
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.sender_id == current_user.id,
        Message.is_deleted == False
    ).first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or you don't have permission to edit it"
        )

    # Update message fields
    message.content = message_update.content
    message.message_type = message_update.message_type
    message.message_metadata = message_update.message_metadata
    message.updated_at = datetime.utcnow()

    try:
        db.commit()
        db.refresh(message)
        return message
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating message"
        )


@messaging_router.delete("/messages/{message_id}")
async def delete_message(
    message_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a message (soft delete)"""
    message = db.query(Message).filter(
        Message.id == message_id,
        Message.sender_id == current_user.id,
        Message.is_deleted == False
    ).first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or you don't have permission to delete it"
        )

    try:
        message.is_deleted = True
        message.deleted_at = datetime.utcnow()
        db.commit()
        return {
            "success": True,
            "message": "Message deleted successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting message"
        )


@messaging_router.post("/messages/{message_id}/react")
async def add_message_reaction(
    message_id: int,
    reaction_data: MessageReactionCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add reaction to a message"""
    # Check if message exists
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

    # Check if user is participant in conversation
    participant = db.query(ConversationParticipant).filter(
        ConversationParticipant.conversation_id == message.conversation_id,
        ConversationParticipant.user_id == current_user.id,
        ConversationParticipant.left_at.is_(None)
    ).first()

    if not participant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a participant in this conversation"
        )

    # Check if reaction already exists
    existing_reaction = db.query(MessageReaction).filter(
        MessageReaction.message_id == message_id,
        MessageReaction.user_id == current_user.id,
        MessageReaction.reaction_type == reaction_data.reaction_type
    ).first()

    if existing_reaction:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reaction already exists"
        )

    # Create reaction
    reaction = MessageReaction(
        message_id=message_id,
        user_id=current_user.id,
        reaction_type=reaction_data.reaction_type
    )

    try:
        db.add(reaction)
        db.commit()
        db.refresh(reaction)

        return {
            "success": True,
            "message": "Reaction added successfully",
            "data": reaction
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error adding reaction"
        )


@messaging_router.post("/blocks")
async def block_user(
    block_data: BlockUserRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Block a user"""
    try:
        blocked_id = block_data.blocked_id
        reason = block_data.reason

        if not blocked_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="blocked_id is required"
            )

        # Check if user is trying to block themselves
        if blocked_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot block yourself"
            )

        # Check if block already exists
        existing_block = db.query(UserBlock).filter(
            UserBlock.blocker_id == current_user.id,
            UserBlock.blocked_id == blocked_id
        ).first()

        if existing_block:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already blocked"
            )

        # Create block
        user_block = UserBlock(
            blocker_id=current_user.id,
            blocked_id=blocked_id,
            reason=reason
        )

        db.add(user_block)
        db.commit()
        db.refresh(user_block)

        # Send real-time notification to blocked user
        await NotificationService.notify_user_blocked(
            db=db,
            blocker_id=current_user.id,
            blocked_id=blocked_id,
            reason=reason
        )

        return {"message": "User blocked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error blocking user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error blocking user"
        )


@messaging_router.post("/blocks/unblock")
async def unblock_user(
    unblock_data: UnblockUserRequest,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unblock a user"""
    try:
        blocked_id = unblock_data.blocked_id

        # Validate that the blocked user exists
        blocked_user = db.query(User).filter(User.id == blocked_id).first()
        if not blocked_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Find and delete block
        user_block = db.query(UserBlock).filter(
            UserBlock.blocker_id == current_user.id,
            UserBlock.blocked_id == blocked_id
        ).first()

        if not user_block:
            # User is not blocked, but don't treat this as an error
            # Just return success message
            return {"message": "User is not blocked or already unblocked"}

        db.delete(user_block)
        db.commit()

        # Send real-time notification to unblocked user
        await NotificationService.notify_user_unblocked(
            db=db,
            unblocker_id=current_user.id,
            unblocked_id=blocked_id
        )

        return {"message": "User unblocked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error unblocking user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error unblocking user"
        )


@messaging_router.get("/blocks")
async def get_blocks(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of users blocked by current user"""
    blocked_users = db.query(UserBlock).filter(
        UserBlock.blocker_id == current_user.id
    ).all()

    return {
        "blocked_users": blocked_users,
        "count": len(blocked_users)
    }


@messaging_router.get("/blocks/blocked_users")
async def get_blocked_users(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of blocked users"""
    blocked_users = db.query(UserBlock).filter(
        UserBlock.blocker_id == current_user.id
    ).all()

    return {
        "blocked_users": blocked_users,
        "count": len(blocked_users)
    }


@messaging_router.post("/send-multi")
async def send_multi_message(
    conversation_ids: List[int],
    message_data: MessageCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send message to multiple conversations"""
    sent_messages = []

    for conversation_id in conversation_ids:
        # Check if user is participant
        participant = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == conversation_id,
            ConversationParticipant.user_id == current_user.id,
            ConversationParticipant.left_at.is_(None)
        ).first()

        if participant:
            # Create message
            message = Message(
                conversation_id=conversation_id,
                sender_id=current_user.id,
                content=message_data.content,
                message_type=message_data.message_type,
                message_metadata=message_data.message_metadata
            )
            db.add(message)
            sent_messages.append(conversation_id)

    try:
        db.commit()
        return {
            "success": True,
            "message": f"Message sent to {len(sent_messages)} conversations",
            "sent_to": sent_messages
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending messages"
        )
