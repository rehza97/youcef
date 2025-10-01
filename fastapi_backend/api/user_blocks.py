from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel

from database.connection import get_db
from core.security import get_current_user
from models.user_block import UserBlock, UserBlockCreate
from models.user import User
from services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)

user_blocks_router = APIRouter()

# Request Models


class BlockUserRequest(BaseModel):
    blocked_user_id: int
    reason: str = ""


class UnblockUserRequest(BaseModel):
    blocked_user_id: int


@user_blocks_router.post("/")
async def block_user(
    block_data: BlockUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Block a user"""
    try:
        # Check if user exists
        blocked_user = db.query(User).filter(
            User.id == block_data.blocked_user_id).first()
        if not blocked_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check if user is trying to block themselves
        if block_data.blocked_user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot block yourself"
            )

        # Check if block already exists
        existing_block = db.query(UserBlock).filter(
            UserBlock.blocker_id == current_user.id,
            UserBlock.blocked_id == block_data.blocked_user_id
        ).first()

        if existing_block:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already blocked"
            )

        # Create block
        user_block = UserBlock(
            blocker_id=current_user.id,
            blocked_id=block_data.blocked_user_id,
            reason=block_data.reason,
            created_at=datetime.utcnow()
        )

        db.add(user_block)
        db.commit()
        db.refresh(user_block)

        # Send notification
        try:
            await NotificationService.notify_user_blocked(
                db=db,
                blocker_id=current_user.id,
                blocked_id=block_data.blocked_user_id
            )
        except Exception as e:
            logger.error(f"Error sending block notification: {e}")

        return {
            "message": f"User {blocked_user.username} has been blocked",
            "block_id": user_block.id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error blocking user: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error blocking user"
        )


@user_blocks_router.post("/unblock")
async def unblock_user(
    unblock_data: UnblockUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unblock a user"""
    try:
        # Find the block
        user_block = db.query(UserBlock).filter(
            UserBlock.blocker_id == current_user.id,
            UserBlock.blocked_id == unblock_data.blocked_user_id
        ).first()

        if not user_block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Block not found"
            )

        # Get blocked user for response
        blocked_user = db.query(User).filter(
            User.id == unblock_data.blocked_user_id).first()

        # Delete the block
        db.delete(user_block)
        db.commit()

        # Send notification
        try:
            await NotificationService.notify_user_unblocked(
                db=db,
                blocker_id=current_user.id,
                blocked_id=unblock_data.blocked_user_id
            )
        except Exception as e:
            logger.error(f"Error sending unblock notification: {e}")

        return {
            "message": f"User {blocked_user.username if blocked_user else 'Unknown'} has been unblocked"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unblocking user: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error unblocking user"
        )


@user_blocks_router.get("/")
async def get_blocked_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all users blocked by current user"""
    try:
        blocks = db.query(UserBlock).filter(
            UserBlock.blocker_id == current_user.id
        ).all()

        blocked_users = []
        for block in blocks:
            blocked_user = db.query(User).filter(
                User.id == block.blocked_id).first()
            if blocked_user:
                blocked_users.append({
                    "user_id": blocked_user.id,
                    "username": blocked_user.username,
                    "email": blocked_user.email,
                    "blocked_at": block.created_at.isoformat(),
                    "reason": block.reason
                })

        return {"blocked_users": blocked_users}

    except Exception as e:
        logger.error(f"Error getting blocked users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving blocked users"
        )


@user_blocks_router.get("/blocked_users")
async def get_users_who_blocked_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all users who have blocked the current user"""
    try:
        blocks = db.query(UserBlock).filter(
            UserBlock.blocked_id == current_user.id
        ).all()

        blocking_users = []
        for block in blocks:
            blocking_user = db.query(User).filter(
                User.id == block.blocker_id).first()
            if blocking_user:
                blocking_users.append({
                    "user_id": blocking_user.id,
                    "username": blocking_user.username,
                    "blocked_at": block.created_at.isoformat()
                })

        return {"blocking_users": blocking_users}

    except Exception as e:
        logger.error(f"Error getting blocking users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving blocking users"
        )





