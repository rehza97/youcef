from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from database.connection import get_db
from core.security import get_current_user
from models.conversation import ConversationParticipant
from models.message import Message, MessageReaction, MessageWithReactions
from models.user import User
import logging

logger = logging.getLogger(__name__)

message_reactions_router = APIRouter()


class MessageReactionRequest(BaseModel):
    emoji: str


@message_reactions_router.post("/messages/{message_id}/reactions")
async def add_message_reaction(
    message_id: int,
    reaction_data: MessageReactionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a reaction to a message"""
    try:
        # Check if message exists
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
                detail="Not authorized to react to this message"
            )

        # Check if user already reacted with this emoji
        existing_reaction = db.query(MessageReaction).filter(
            MessageReaction.message_id == message_id,
            MessageReaction.user_id == current_user.id,
            MessageReaction.emoji == reaction_data.emoji
        ).first()

        if existing_reaction:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already reacted with this emoji"
            )

        # Create new reaction
        reaction = MessageReaction(
            message_id=message_id,
            user_id=current_user.id,
            emoji=reaction_data.emoji
        )

        db.add(reaction)
        db.commit()
        db.refresh(reaction)

        logger.info(f"Reaction added to message {message_id} by user {current_user.id}")
        return {"message": "Reaction added successfully", "reaction_id": reaction.id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding reaction: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error adding reaction"
        )


@message_reactions_router.delete("/messages/{message_id}/reactions/{reaction_id}")
async def remove_message_reaction(
    message_id: int,
    reaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a reaction from a message"""
    try:
        # Get the reaction
        reaction = db.query(MessageReaction).filter(
            MessageReaction.id == reaction_id,
            MessageReaction.message_id == message_id
        ).first()

        if not reaction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reaction not found"
            )

        # Only the user who added the reaction can remove it
        if reaction.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the user who added the reaction can remove it"
            )

        db.delete(reaction)
        db.commit()

        logger.info(f"Reaction {reaction_id} removed from message {message_id}")
        return {"message": "Reaction removed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing reaction: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error removing reaction"
        )


@message_reactions_router.get("/messages/{message_id}/reactions")
async def get_message_reactions(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all reactions for a message"""
    try:
        # Check if message exists
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
                detail="Not authorized to view reactions for this message"
            )

        # Get all reactions for the message
        reactions = db.query(MessageReaction).filter(
            MessageReaction.message_id == message_id
        ).all()

        # Group reactions by emoji
        reactions_grouped = {}
        for reaction in reactions:
            emoji = reaction.emoji
            if emoji not in reactions_grouped:
                reactions_grouped[emoji] = {
                    "emoji": emoji,
                    "count": 0,
                    "users": []
                }
            reactions_grouped[emoji]["count"] += 1
            reactions_grouped[emoji]["users"].append({
                "user_id": reaction.user_id,
                "username": reaction.user.username if reaction.user else "Unknown"
            })

        return {
            "message_id": message_id,
            "reactions": list(reactions_grouped.values())
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting message reactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving message reactions"
        )


@message_reactions_router.get("/messages/{message_id}/with-reactions", response_model=MessageWithReactions)
async def get_message_with_reactions(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a message with all its reactions"""
    try:
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found"
            )

        # Check if user is participant
        participant = db.query(ConversationParticipant).filter(
            ConversationParticipant.conversation_id == message.conversation_id,
            ConversationParticipant.user_id == current_user.id
        ).first()

        if not participant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this message"
            )

        return MessageWithReactions.from_orm(message)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting message with reactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving message with reactions"
        )