from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database.connection import get_db
from core.security import get_current_user, get_password_hash
from models.user import User, UserResponse, UserUpdate, UserProfile, UserCreate
from models.role import Role, UserRole
from core.config import settings

users_management_router = APIRouter()


@users_management_router.post("/", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user (Admin only)"""
    # Check if current user is admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role not found"
        )

    user_role = db.query(UserRole).filter(
        UserRole.user_id == current_user.id,
        UserRole.role_id == admin_role.id
    ).first()

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create users"
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
        full_name=user_data.full_name,
        is_active=user_data.is_active if user_data.is_active is not None else True,
        created_at=datetime.utcnow()
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
    # Check admin permissions
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        user_role = db.query(UserRole).filter(
            UserRole.user_id == current_user.id,
            UserRole.role_id == admin_role.id
        ).first()
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can view all users"
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

        current_user.updated_at = datetime.utcnow()
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
    is_admin = False

    if not is_own_profile:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role:
            user_role = db.query(UserRole).filter(
                UserRole.user_id == current_user.id,
                UserRole.role_id == admin_role.id
            ).first()
            is_admin = user_role is not None

    if not is_own_profile and not is_admin:
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

        user.updated_at = datetime.utcnow()
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
    # Check if current user is admin
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not admin_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role not found"
        )

    user_role = db.query(UserRole).filter(
        UserRole.user_id == current_user.id,
        UserRole.role_id == admin_role.id
    ).first()

    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete users"
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
        # Delete user (this will cascade to related records)
        db.delete(user)
        db.commit()

        return {"message": f"User {user.username} deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting user: {str(e)}"
        )


