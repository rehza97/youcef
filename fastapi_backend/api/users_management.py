from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database.connection import get_db
from core.security import get_current_user, get_password_hash
from models.user import User, UserResponse, UserUpdate, UserProfile, UserCreate
from models.role import Role, UserRole
from models.conversation import ConversationParticipant
from models.message import Message, MessageReaction, MessageReadReceipt
from models.notification import Notification, NotificationPreference
from models.file_upload import FileUpload
from models.user_block import UserBlock
from models.conversation import ConversationParticipant
from services.permission_service import PermissionService
from core.config import settings

users_management_router = APIRouter()


@users_management_router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user (Admin only)"""
    # Enforce admin OR can_manage_users permission
    if not (PermissionService.is_admin(current_user, db) or PermissionService.has_permission(current_user, db, "can_manage_users")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: can_manage_users"
        )

    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        first_name=getattr(user_data, "first_name", None),
        last_name=getattr(user_data, "last_name", None),
        is_active=user_data.is_active if getattr(
            user_data, "is_active", None) is not None else True,
        bio=getattr(user_data, "bio", None),
        avatar_url=getattr(user_data, "avatar_url", None),
        dot_id=getattr(user_data, "dot_id", None)
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return UserResponse.from_orm(db_user)


@users_management_router.get("/", response_model=List[UserResponse])
async def get_users(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all users (Admin only)"""
    # Enforce admin OR can_manage_users
    if not (PermissionService.is_admin(current_user, db) or PermissionService.has_permission(current_user, db, "can_manage_users")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: can_manage_users"
        )

    users = db.query(User).all()
    return [UserResponse.from_orm(user) for user in users]


@users_management_router.get("/me", response_model=UserProfile)
async def get_current_user_profile(current_user=Depends(get_current_user)):
    """Get current user profile"""
    return UserProfile.from_orm(current_user)


@users_management_router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    try:
        # Update user fields
        update_data = user_update.dict(exclude_unset=True)

        for field, value in update_data.items():
            if field == "password" and value:
                # Hash the new password
                hashed_password = get_password_hash(value)
                setattr(current_user, "hashed_password", hashed_password)
            elif hasattr(current_user, field):
                setattr(current_user, field, value)

        # Model has no updated_at column; skip timestamp update
        db.commit()
        db.refresh(current_user)

        return UserResponse.from_orm(current_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )


@users_management_router.get("/search", response_model=List[UserResponse])
async def search_users(
    q: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Search users by username or email"""
    users = db.query(User).filter(
        (User.username.ilike(f"%{q}%")) | (User.email.ilike(f"%{q}%"))
    ).limit(10).all()

    return [UserResponse.from_orm(user) for user in users]


@users_management_router.get("/{user_id}", response_model=UserProfile)
async def get_user(
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserProfile.from_orm(user)


@users_management_router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user (Admin only or own profile)"""
    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check permissions (admin or own profile)
    is_own_profile = user_id == current_user.id
    if not is_own_profile and not (
        PermissionService.is_admin(current_user, db)
        or PermissionService.has_permission(current_user, db, "can_manage_users")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user"
        )

    try:
        # Update user fields
        update_data = user_update.dict(exclude_unset=True)

        for field, value in update_data.items():
            if field == "password" and value:
                hashed_password = get_password_hash(value)
                setattr(user, "hashed_password", hashed_password)
            elif hasattr(user, field):
                setattr(user, field, value)

        # Model has no updated_at column; skip timestamp update
        db.commit()
        db.refresh(user)

        return UserResponse.from_orm(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )


@users_management_router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete user (Admin only)"""
    # Enforce admin OR can_manage_users
    if not (PermissionService.is_admin(current_user, db) or PermissionService.has_permission(current_user, db, "can_manage_users")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission required: can_manage_users"
        )

    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    try:
        # Remove role assignments first to avoid FK integrity issues
        db.query(UserRole).filter(UserRole.user_id ==
                                  user_id).delete(synchronize_session=False)

        # Remove conversation participations for this user
        db.query(ConversationParticipant).filter(
            ConversationParticipant.user_id == user_id
        ).delete(synchronize_session=False)

        # Remove messaging artifacts for this user (FKs to users)
        db.query(MessageReadReceipt).filter(
            MessageReadReceipt.user_id == user_id
        ).delete(synchronize_session=False)
        db.query(MessageReaction).filter(
            MessageReaction.user_id == user_id
        ).delete(synchronize_session=False)
        db.query(Message).filter(
            Message.sender_id == user_id
        ).delete(synchronize_session=False)

        # Remove notifications and preferences for this user
        db.query(Notification).filter(
            Notification.user_id == user_id
        ).delete(synchronize_session=False)
        db.query(NotificationPreference).filter(
            NotificationPreference.user_id == user_id
        ).delete(synchronize_session=False)

        # Remove file uploads owned by this user
        db.query(FileUpload).filter(
            FileUpload.uploaded_by == user_id
        ).delete(synchronize_session=False)

        # Remove user block relationships
        db.query(UserBlock).filter(UserBlock.blocker_id ==
                                   user_id).delete(synchronize_session=False)
        db.query(UserBlock).filter(UserBlock.blocked_id ==
                                   user_id).delete(synchronize_session=False)

        # Delete user (this will cascade to related records where configured)
        db.delete(user)
        db.commit()

        return {"message": f"User {user.username} deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )
