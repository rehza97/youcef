from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

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

messaging_router = APIRouter()


@messaging_router.get("/conversations", response_model=List[ConversationResponse])
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

    return conversations


@messaging_router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific conversation"""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    return conversation


@messaging_router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
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

    return messages


@messaging_router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    message_data: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to a conversation"""
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

    # Create message
    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=message_data.get("content", ""),
        message_type=message_data.get("message_type", "text"),
        message_metadata=message_data.get("message_metadata", {})
    )

    try:
        db.add(message)
        db.commit()
        db.refresh(message)

        # Add sender username
        sender = db.query(User).filter(User.id == message.sender_id).first()
        message.sender_username = sender.username if sender else None

        return {
            "success": True,
            "message": "Message sent successfully",
            "data": message
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error sending message"
        )


@messaging_router.post("/conversations")
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation"""
    # Create conversation
    conversation = Conversation(
        name=conversation_data.name,
        conversation_type=conversation_data.conversation_type,
        conversation_metadata=conversation_data.conversation_metadata
    )

    try:
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        # Add participants
        participant_ids = conversation_data.participant_ids + \
            [current_user.id]
        for user_id in set(participant_ids):  # Remove duplicates
            participant = ConversationParticipant(
                conversation_id=conversation.id,
                user_id=user_id,
                is_admin=(user_id == current_user.id)  # Creator is admin
            )
            db.add(participant)

        db.commit()

        return {
            "success": True,
            "message": "Conversation created successfully",
            "data": {
                "id": conversation.id,
                "name": conversation.name,
                "conversation_type": conversation.conversation_type,
                "is_active": conversation.is_active,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating conversation"
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
    block_data: dict,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Block a user"""
    blocked_id = block_data.get("blocked_user_id")
    reason = block_data.get("reason", "")

    if not blocked_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="blocked_user_id is required"
        )

    # Check if user exists
    blocked_user = db.query(User).filter(User.id == blocked_id).first()
    if not blocked_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if already blocked
    existing_block = db.query(UserBlock).filter(
        UserBlock.blocker_id == current_user.id,
        UserBlock.blocked_id == blocked_id
    ).first()

    if existing_block:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already blocked"
        )

    # Create block
    user_block = UserBlock(
        blocker_id=current_user.id,
        blocked_id=blocked_id,
        reason=reason
    )

    try:
        db.add(user_block)
        db.commit()
        db.refresh(user_block)

        return {
            "success": True,
            "message": "User blocked successfully",
            "data": user_block
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error blocking user"
        )


@messaging_router.post("/blocks/unblock")
async def unblock_user(
    blocked_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unblock a user"""
    # Find and delete block
    user_block = db.query(UserBlock).filter(
        UserBlock.blocker_id == current_user.id,
        UserBlock.blocked_id == blocked_id
    ).first()

    if not user_block:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Block not found"
        )

    try:
        db.delete(user_block)
        db.commit()

        return {
            "success": True,
            "message": "User unblocked successfully"
        }
    except Exception as e:
        db.rollback()
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
