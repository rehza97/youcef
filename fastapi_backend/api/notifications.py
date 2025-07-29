from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from database.connection import get_db
from core.security import get_current_user
from models.notification import (
    Notification, NotificationCreate, NotificationResponse,
    NotificationPreference, NotificationPreferenceUpdate, NotificationPreferenceResponse,
    NotificationUpdate
)
from models.user import User

notifications_router = APIRouter()

# Response models for the wrapped responses


class NotificationsListResponse(BaseModel):
    notifications: List[NotificationResponse]


class NotificationStatsResponse(BaseModel):
    stats: Dict[str, Any]


class NotificationPreferencesResponse(BaseModel):
    preferences: NotificationPreferenceResponse


@notifications_router.get("/", response_model=NotificationsListResponse)
async def get_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user notifications"""
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id)

    if unread_only:
        query = query.filter(Notification.is_read == False)

    notifications = query.order_by(
        Notification.created_at.desc()).offset(skip).limit(limit).all()
    return {"notifications": notifications}


@notifications_router.put("/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    notification.is_read = True
    notification.read_at = datetime.utcnow()

    try:
        db.commit()
        return {
            "success": True,
            "message": "Notification marked as read"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating notification"
        )


@notifications_router.put("/read-all")
async def mark_all_notifications_as_read(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all user notifications as read"""
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).all()

    for notification in notifications:
        notification.is_read = True
        notification.read_at = datetime.utcnow()

    try:
        db.commit()
        return {
            "success": True,
            "message": f"Marked {len(notifications)} notifications as read"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating notifications"
        )


@notifications_router.get("/stats", response_model=NotificationStatsResponse)
async def get_notification_stats(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notification statistics"""
    total_notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).count()

    unread_notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()

    return {
        "stats": {
            "total_notifications": total_notifications,
            "unread_notifications": unread_notifications,
            "read_notifications": total_notifications - unread_notifications
        }
    }


@notifications_router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user notification preferences"""
    preferences = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()

    if not preferences:
        # Create default preferences
        preferences = NotificationPreference(user_id=current_user.id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)

    return {"preferences": preferences}


@notifications_router.put("/preferences")
async def update_notification_preferences(
    preferences_update: NotificationPreferenceUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user notification preferences"""
    preferences = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).first()

    if not preferences:
        preferences = NotificationPreference(user_id=current_user.id)
        db.add(preferences)

    # Update preferences
    update_data = preferences_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(preferences, field, value)

    try:
        db.commit()
        db.refresh(preferences)
        return {
            "success": True,
            "message": "Notification preferences updated successfully",
            "data": preferences
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating notification preferences"
        )


@notifications_router.post("/", response_model=NotificationResponse)
async def create_notification(
    notification_data: NotificationCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new notification"""
    notification = Notification(
        user_id=current_user.id,
        title=notification_data.title,
        message=notification_data.message,
        notification_type=notification_data.notification_type,
        data=notification_data.data
    )
    try:
        db.add(notification)
        db.commit()
        db.refresh(notification)
        return notification
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating notification"
        )


@notifications_router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific notification"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    return notification


@notifications_router.put("/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: int,
    notification_update: NotificationUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a notification"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    # Update notification fields
    update_data = notification_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(notification, field, value)

    try:
        db.commit()
        db.refresh(notification)
        return notification
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error updating notification"
        )


@notifications_router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a notification"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )

    try:
        db.delete(notification)
        db.commit()
        return {
            "success": True,
            "message": "Notification deleted successfully"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting notification"
        )
