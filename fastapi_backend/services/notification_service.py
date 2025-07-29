"""
Global Notification Service for Real-time Notifications
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from models.notification import Notification, NotificationPreference
from models.user import User
from websocket_manager import manager

logger = logging.getLogger(__name__)


class NotificationService:
    """Global notification service for real-time notifications"""

    @staticmethod
    async def send_notification(
        db: Session,
        user_id: int,
        title: str,
        message: str,
        notification_type: str = "info",
        data: Optional[Dict[str, Any]] = None,
        send_websocket: bool = True
    ) -> Notification:
        """Send notification to a specific user"""
        try:
            # Check user notification preferences
            preference = db.query(NotificationPreference).filter(
                NotificationPreference.user_id == user_id
            ).first()

            if not preference or not preference.in_app_notifications:
                logger.info(
                    f"User {user_id} has disabled in-app notifications")
                return None

            # Create notification record
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
                data=data or {},
                is_read=False
            )

            db.add(notification)
            db.commit()
            db.refresh(notification)

            # Send real-time notification via WebSocket
            if send_websocket:
                await NotificationService.send_websocket_notification(user_id, notification)

            logger.info(f"Notification sent to user {user_id}: {title}")
            return notification

        except Exception as e:
            logger.error(f"Error sending notification to user {user_id}: {e}")
            return None

    @staticmethod
    async def send_websocket_notification(user_id: int, notification: Notification):
        """Send notification via WebSocket"""
        try:
            notification_data = {
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "notification_type": notification.notification_type,
                "data": notification.data,
                "created_at": notification.created_at.isoformat(),
                "is_read": notification.is_read
            }

            await manager.send_personal_message(
                json.dumps({
                    "type": "notification",
                    "data": notification_data
                }),
                user_id,
                "notifications"
            )

        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {e}")

    @staticmethod
    async def send_bulk_notifications(
        db: Session,
        user_ids: List[int],
        title: str,
        message: str,
        notification_type: str = "info",
        data: Optional[Dict[str, Any]] = None
    ):
        """Send notifications to multiple users"""
        notifications = []
        for user_id in user_ids:
            notification = await NotificationService.send_notification(
                db, user_id, title, message, notification_type, data
            )
            if notification:
                notifications.append(notification)

        return notifications

    @staticmethod
    async def notify_message_sent(
        db: Session,
        sender_id: int,
        conversation_id: int,
        message_content: str,
        participants: List[int]
    ):
        """Notify participants about new message"""
        sender = db.query(User).filter(User.id == sender_id).first()
        if not sender:
            return

        # Don't notify the sender
        recipient_ids = [p for p in participants if p != sender_id]

        title = f"Nouveau message de {sender.username}"
        message = f"{sender.username}: {message_content[:50]}{'...' if len(message_content) > 50 else ''}"

        await NotificationService.send_bulk_notifications(
            db,
            recipient_ids,
            title,
            message,
            "message",
            {
                "sender_id": sender_id,
                "sender_username": sender.username,
                "conversation_id": conversation_id,
                "message_preview": message_content[:100]
            }
        )

    @staticmethod
    async def notify_file_uploaded(
        db: Session,
        user_id: int,
        filename: str,
        file_size: int,
        file_type: str
    ):
        """Notify user about file upload"""
        title = "Fichier téléchargé"
        message = f"Le fichier '{filename}' a été téléchargé avec succès"

        await NotificationService.send_notification(
            db,
            user_id,
            title,
            message,
            "success",
            {
                "filename": filename,
                "file_size": file_size,
                "file_type": file_type,
                "action": "upload"
            }
        )

    @staticmethod
    async def notify_file_processing_started(
        db: Session,
        user_id: int,
        filename: str,
        file_type: str
    ):
        """Notify user about file processing start"""
        title = "Traitement en cours"
        message = f"Le traitement du fichier '{filename}' a commencé"

        await NotificationService.send_notification(
            db,
            user_id,
            title,
            message,
            "info",
            {
                "filename": filename,
                "file_type": file_type,
                "action": "processing_started",
                "progress": 0
            }
        )

    @staticmethod
    async def notify_file_processing_progress(
        db: Session,
        user_id: int,
        filename: str,
        progress: int
    ):
        """Notify user about file processing progress"""
        title = "Progression du traitement"
        message = f"Traitement de '{filename}': {progress}% terminé"

        await NotificationService.send_notification(
            db,
            user_id,
            title,
            message,
            "info",
            {
                "filename": filename,
                "action": "processing_progress",
                "progress": progress
            }
        )

    @staticmethod
    async def notify_file_processing_completed(
        db: Session,
        user_id: int,
        filename: str,
        results: Dict[str, Any]
    ):
        """Notify user about file processing completion"""
        title = "Traitement terminé"
        message = f"Le traitement du fichier '{filename}' est terminé"

        await NotificationService.send_notification(
            db,
            user_id,
            title,
            message,
            "success",
            {
                "filename": filename,
                "action": "processing_completed",
                "results": results,
                "progress": 100
            }
        )

    @staticmethod
    async def notify_file_processing_failed(
        db: Session,
        user_id: int,
        filename: str,
        error_message: str
    ):
        """Notify user about file processing failure"""
        title = "Erreur de traitement"
        message = f"Le traitement du fichier '{filename}' a échoué: {error_message}"

        await NotificationService.send_notification(
            db,
            user_id,
            title,
            message,
            "error",
            {
                "filename": filename,
                "action": "processing_failed",
                "error": error_message
            }
        )

    @staticmethod
    async def notify_file_shared(
        db: Session,
        sender_id: int,
        recipient_ids: List[int],
        filename: str
    ):
        """Notify users about file sharing"""
        sender = db.query(User).filter(User.id == sender_id).first()
        if not sender:
            return

        title = f"Fichier partagé par {sender.username}"
        message = f"{sender.username} a partagé le fichier '{filename}' avec vous"

        await NotificationService.send_bulk_notifications(
            db,
            recipient_ids,
            title,
            message,
            "file_share",
            {
                "sender_id": sender_id,
                "sender_username": sender.username,
                "filename": filename,
                "action": "file_shared"
            }
        )

    @staticmethod
    async def notify_user_blocked(
        db: Session,
        blocker_id: int,
        blocked_id: int,
        reason: str
    ):
        """Notify users about blocking"""
        blocker = db.query(User).filter(User.id == blocker_id).first()
        blocked = db.query(User).filter(User.id == blocked_id).first()

        if not blocker or not blocked:
            return

        # Notify blocked user
        title = "Compte bloqué"
        message = f"Votre compte a été bloqué par {blocker.username}"

        await NotificationService.send_notification(
            db,
            blocked_id,
            title,
            message,
            "warning",
            {
                "blocker_id": blocker_id,
                "blocker_username": blocker.username,
                "reason": reason,
                "action": "user_blocked"
            }
        )

    @staticmethod
    async def notify_user_unblocked(
        db: Session,
        unblocker_id: int,
        unblocked_id: int
    ):
        """Notify users about unblocking"""
        unblocker = db.query(User).filter(User.id == unblocker_id).first()
        unblocked = db.query(User).filter(User.id == unblocked_id).first()

        if not unblocker or not unblocked:
            return

        # Notify unblocked user
        title = "Compte débloqué"
        message = f"Votre compte a été débloqué par {unblocker.username}"

        await NotificationService.send_notification(
            db,
            unblocked_id,
            title,
            message,
            "success",
            {
                "unblocker_id": unblocker_id,
                "unblocker_username": unblocker.username,
                "action": "user_unblocked"
            }
        )

    @staticmethod
    async def notify_system_event(
        db: Session,
        user_ids: List[int],
        title: str,
        message: str,
        event_type: str = "system",
        data: Optional[Dict[str, Any]] = None
    ):
        """Notify users about system events"""
        await NotificationService.send_bulk_notifications(
            db,
            user_ids,
            title,
            message,
            event_type,
            data or {}
        )

    @staticmethod
    async def notify_conversation_created(
        db: Session,
        creator_id: int,
        participant_ids: List[int],
        conversation_name: str
    ):
        """Notify participants about new conversation"""
        creator = db.query(User).filter(User.id == creator_id).first()
        if not creator:
            return

        # Don't notify the creator
        recipient_ids = [p for p in participant_ids if p != creator_id]

        title = "Nouvelle conversation"
        message = f"{creator.username} vous a ajouté à une nouvelle conversation: {conversation_name}"

        await NotificationService.send_bulk_notifications(
            db,
            recipient_ids,
            title,
            message,
            "conversation",
            {
                "creator_id": creator_id,
                "creator_username": creator.username,
                "conversation_name": conversation_name,
                "action": "conversation_created"
            }
        )
