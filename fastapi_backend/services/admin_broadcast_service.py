import json
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models.user import User
from models.file_upload import FileUpload
from services.secure_file_service import secure_file_service
from services.dot_service import DOTService
from services.audit_service import audit_service
from services.websocket_messaging_service import websocket_messaging_manager
from services.notification_service import NotificationService

logger = logging.getLogger(__name__)

class AdminBroadcastService:
    """Service for admin file broadcasting and messaging"""

    def __init__(self):
        self.secure_file_service = secure_file_service
        self.audit_service = audit_service
        self.websocket_manager = websocket_messaging_manager

    def validate_admin_permissions(self, user: User, required_action: str = "broadcast") -> bool:
        """Validate admin permissions for broadcasting"""
        try:
            # Check if user is admin or has specific broadcast permissions
            if user.is_superuser or user.is_staff:
                return True

            # TODO: Check specific broadcast permissions if implemented
            # For now, only allow superusers and staff
            return False

        except Exception as e:
            logger.error(f"Error validating admin permissions: {e}")
            return False

    async def broadcast_file_to_all_users(
        self,
        db: Session,
        admin_user: User,
        file_upload: FileUpload,
        message: Optional[str] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Broadcast file to all active users"""
        try:
            # Validate admin permissions
            if not self.validate_admin_permissions(admin_user, "broadcast_all"):
                raise HTTPException(status_code=403, detail="Insufficient permissions for broadcasting")

            # Get all active users
            active_users = db.query(User).filter(User.is_active == True).all()

            # Update file metadata to mark as broadcast
            file_metadata = json.loads(file_upload.file_metadata or '{}')
            file_metadata.update({
                "broadcast_type": "all_users",
                "broadcast_by": admin_user.id,
                "broadcast_at": datetime.utcnow().isoformat(),
                "broadcast_message": message,
                "priority": priority
            })
            file_upload.file_metadata = json.dumps(file_metadata)
            db.commit()

            # Send notifications to all users
            notification_count = 0
            websocket_count = 0

            for user in active_users:
                if user.id == admin_user.id:
                    continue  # Skip admin user

                try:
                    # Send database notification
                    await NotificationService.send_notification(
                        db=db,
                        user_id=user.id,
                        title="📁 New File Broadcast",
                        message=message or f"New file available: {file_upload.original_filename}",
                        notification_type="file_broadcast",
                        data={
                            "file_id": file_upload.id,
                            "filename": file_upload.original_filename,
                            "file_size": file_upload.file_size,
                            "broadcast_by": admin_user.username,
                            "priority": priority
                        }
                    )
                    notification_count += 1

                    # Send real-time WebSocket notification if user is connected
                    if user.id in self.websocket_manager.active_connections:
                        await self.websocket_manager._send_to_user(user.id, {
                            "type": "file_broadcast",
                            "data": {
                                "file_id": file_upload.id,
                                "filename": file_upload.original_filename,
                                "file_size": file_upload.file_size,
                                "mime_type": file_upload.mime_type,
                                "broadcast_by": admin_user.username,
                                "message": message,
                                "priority": priority,
                                "broadcast_at": datetime.utcnow().isoformat()
                            }
                        })
                        websocket_count += 1

                except Exception as e:
                    logger.error(f"Error notifying user {user.id} about broadcast: {e}")

            # Log the broadcast activity
            self.audit_service.log_activity(
                db=db,
                user_id=admin_user.id,
                action="file_broadcast_all",
                resource_type="file",
                resource_id=file_upload.id,
                details=f"Broadcast file to all users: {file_upload.original_filename}",
                additional_data={
                    "recipient_count": notification_count,
                    "websocket_notifications": websocket_count,
                    "priority": priority
                },
                severity="info"
            )

            return {
                "success": True,
                "broadcast_type": "all_users",
                "file_id": file_upload.id,
                "recipients_notified": notification_count,
                "realtime_notifications": websocket_count,
                "total_recipients": len(active_users) - 1  # Exclude admin
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error broadcasting file to all users: {e}")
            raise HTTPException(status_code=500, detail="Failed to broadcast file")

    async def broadcast_file_to_dot_users(
        self,
        db: Session,
        admin_user: User,
        file_upload: FileUpload,
        dot_id: int,
        message: Optional[str] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Broadcast file to users in specific DOT"""
        try:
            # Validate admin permissions
            if not self.validate_admin_permissions(admin_user, "broadcast_dot"):
                raise HTTPException(status_code=403, detail="Insufficient permissions for DOT broadcasting")

            # Validate DOT exists
            dot = DOTService.get_dot_by_id(db, dot_id)
            if not dot:
                raise HTTPException(status_code=404, detail="DOT not found")

            # Get users in the DOT
            dot_users = DOTService.get_users_in_dot(db, dot_id, skip=0, limit=1000)

            if not dot_users:
                return {
                    "success": True,
                    "broadcast_type": "dot_users",
                    "file_id": file_upload.id,
                    "recipients_notified": 0,
                    "realtime_notifications": 0,
                    "total_recipients": 0,
                    "dot_name": dot.name
                }

            # Update file metadata
            file_metadata = json.loads(file_upload.file_metadata or '{}')
            file_metadata.update({
                "broadcast_type": "dot_users",
                "target_dot_id": dot_id,
                "target_dot_name": dot.name,
                "broadcast_by": admin_user.id,
                "broadcast_at": datetime.utcnow().isoformat(),
                "broadcast_message": message,
                "priority": priority
            })
            file_upload.file_metadata = json.dumps(file_metadata)
            db.commit()

            # Send notifications to DOT users
            notification_count = 0
            websocket_count = 0

            for user in dot_users:
                if user.id == admin_user.id:
                    continue  # Skip admin user

                try:
                    # Send database notification
                    await NotificationService.send_notification(
                        db=db,
                        user_id=user.id,
                        title=f"📁 New File for {dot.name}",
                        message=message or f"New file available for {dot.name}: {file_upload.original_filename}",
                        notification_type="file_broadcast_dot",
                        data={
                            "file_id": file_upload.id,
                            "filename": file_upload.original_filename,
                            "file_size": file_upload.file_size,
                            "broadcast_by": admin_user.username,
                            "dot_name": dot.name,
                            "priority": priority
                        }
                    )
                    notification_count += 1

                    # Send real-time WebSocket notification
                    if user.id in self.websocket_manager.active_connections:
                        await self.websocket_manager._send_to_user(user.id, {
                            "type": "file_broadcast",
                            "data": {
                                "file_id": file_upload.id,
                                "filename": file_upload.original_filename,
                                "file_size": file_upload.file_size,
                                "mime_type": file_upload.mime_type,
                                "broadcast_by": admin_user.username,
                                "message": message,
                                "priority": priority,
                                "dot_name": dot.name,
                                "broadcast_at": datetime.utcnow().isoformat()
                            }
                        })
                        websocket_count += 1

                except Exception as e:
                    logger.error(f"Error notifying DOT user {user.id} about broadcast: {e}")

            # Log the broadcast activity
            self.audit_service.log_activity(
                db=db,
                user_id=admin_user.id,
                action="file_broadcast_dot",
                resource_type="file",
                resource_id=file_upload.id,
                details=f"Broadcast file to DOT {dot.name}: {file_upload.original_filename}",
                additional_data={
                    "dot_id": dot_id,
                    "dot_name": dot.name,
                    "recipient_count": notification_count,
                    "websocket_notifications": websocket_count,
                    "priority": priority
                },
                severity="info"
            )

            return {
                "success": True,
                "broadcast_type": "dot_users",
                "file_id": file_upload.id,
                "recipients_notified": notification_count,
                "realtime_notifications": websocket_count,
                "total_recipients": len(dot_users) - (1 if admin_user in dot_users else 0),
                "dot_name": dot.name
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error broadcasting file to DOT users: {e}")
            raise HTTPException(status_code=500, detail="Failed to broadcast file to DOT")

    async def broadcast_file_to_selected_users(
        self,
        db: Session,
        admin_user: User,
        file_upload: FileUpload,
        user_ids: List[int],
        message: Optional[str] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Broadcast file to selected users"""
        try:
            # Validate admin permissions
            if not self.validate_admin_permissions(admin_user, "broadcast_selected"):
                raise HTTPException(status_code=403, detail="Insufficient permissions for selective broadcasting")

            # Validate user IDs
            valid_users = db.query(User).filter(
                User.id.in_(user_ids),
                User.is_active == True
            ).all()

            if not valid_users:
                raise HTTPException(status_code=400, detail="No valid users found")

            # Update file metadata
            file_metadata = json.loads(file_upload.file_metadata or '{}')
            file_metadata.update({
                "broadcast_type": "selected_users",
                "target_user_ids": user_ids,
                "broadcast_by": admin_user.id,
                "broadcast_at": datetime.utcnow().isoformat(),
                "broadcast_message": message,
                "priority": priority
            })
            file_upload.file_metadata = json.dumps(file_metadata)
            db.commit()

            # Send notifications to selected users
            notification_count = 0
            websocket_count = 0

            for user in valid_users:
                if user.id == admin_user.id:
                    continue  # Skip admin user

                try:
                    # Send database notification
                    await NotificationService.send_notification(
                        db=db,
                        user_id=user.id,
                        title="📁 File Shared With You",
                        message=message or f"File shared with you: {file_upload.original_filename}",
                        notification_type="file_broadcast_personal",
                        data={
                            "file_id": file_upload.id,
                            "filename": file_upload.original_filename,
                            "file_size": file_upload.file_size,
                            "broadcast_by": admin_user.username,
                            "priority": priority
                        }
                    )
                    notification_count += 1

                    # Send real-time WebSocket notification
                    if user.id in self.websocket_manager.active_connections:
                        await self.websocket_manager._send_to_user(user.id, {
                            "type": "file_broadcast",
                            "data": {
                                "file_id": file_upload.id,
                                "filename": file_upload.original_filename,
                                "file_size": file_upload.file_size,
                                "mime_type": file_upload.mime_type,
                                "broadcast_by": admin_user.username,
                                "message": message,
                                "priority": priority,
                                "broadcast_at": datetime.utcnow().isoformat()
                            }
                        })
                        websocket_count += 1

                except Exception as e:
                    logger.error(f"Error notifying selected user {user.id} about broadcast: {e}")

            # Log the broadcast activity
            self.audit_service.log_activity(
                db=db,
                user_id=admin_user.id,
                action="file_broadcast_selected",
                resource_type="file",
                resource_id=file_upload.id,
                details=f"Broadcast file to selected users: {file_upload.original_filename}",
                additional_data={
                    "target_user_ids": user_ids,
                    "recipient_count": notification_count,
                    "websocket_notifications": websocket_count,
                    "priority": priority
                },
                severity="info"
            )

            return {
                "success": True,
                "broadcast_type": "selected_users",
                "file_id": file_upload.id,
                "recipients_notified": notification_count,
                "realtime_notifications": websocket_count,
                "total_recipients": len(valid_users) - (1 if admin_user in valid_users else 0),
                "requested_recipients": len(user_ids),
                "valid_recipients": len(valid_users)
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error broadcasting file to selected users: {e}")
            raise HTTPException(status_code=500, detail="Failed to broadcast file to selected users")

    async def broadcast_message_to_all_users(
        self,
        db: Session,
        admin_user: User,
        message: str,
        title: Optional[str] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """Broadcast text message to all users"""
        try:
            # Validate admin permissions
            if not self.validate_admin_permissions(admin_user, "message_broadcast_all"):
                raise HTTPException(status_code=403, detail="Insufficient permissions for message broadcasting")

            # Get all active users
            active_users = db.query(User).filter(User.is_active == True).all()

            notification_count = 0
            websocket_count = 0

            for user in active_users:
                if user.id == admin_user.id:
                    continue  # Skip admin user

                try:
                    # Send database notification
                    await NotificationService.send_notification(
                        db=db,
                        user_id=user.id,
                        title=title or "📢 System Announcement",
                        message=message,
                        notification_type="admin_broadcast",
                        data={
                            "broadcast_by": admin_user.username,
                            "priority": priority,
                            "broadcast_type": "message_all"
                        }
                    )
                    notification_count += 1

                    # Send real-time WebSocket notification
                    if user.id in self.websocket_manager.active_connections:
                        await self.websocket_manager._send_to_user(user.id, {
                            "type": "admin_broadcast",
                            "data": {
                                "title": title or "System Announcement",
                                "message": message,
                                "broadcast_by": admin_user.username,
                                "priority": priority,
                                "broadcast_at": datetime.utcnow().isoformat()
                            }
                        })
                        websocket_count += 1

                except Exception as e:
                    logger.error(f"Error sending broadcast message to user {user.id}: {e}")

            # Log the broadcast activity
            self.audit_service.log_activity(
                db=db,
                user_id=admin_user.id,
                action="message_broadcast_all",
                resource_type="broadcast",
                details=f"Broadcast message to all users: {title or 'System Announcement'}",
                additional_data={
                    "recipient_count": notification_count,
                    "websocket_notifications": websocket_count,
                    "priority": priority,
                    "message_length": len(message)
                },
                severity="info"
            )

            return {
                "success": True,
                "broadcast_type": "message_all",
                "recipients_notified": notification_count,
                "realtime_notifications": websocket_count,
                "total_recipients": len(active_users) - 1
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error broadcasting message to all users: {e}")
            raise HTTPException(status_code=500, detail="Failed to broadcast message")

    def get_broadcast_files(
        self,
        db: Session,
        user: User,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get broadcast files accessible to user"""
        try:
            # Get files that were broadcast to this user
            user_accessible_dots = DOTService.get_user_accessible_dots(db, user.id)

            # Query broadcast files
            broadcast_files = db.query(FileUpload).filter(
                FileUpload.file_metadata.contains('"broadcast_type"')
            ).offset(offset).limit(limit).all()

            accessible_files = []

            for file_upload in broadcast_files:
                try:
                    metadata = json.loads(file_upload.file_metadata or '{}')
                    broadcast_type = metadata.get('broadcast_type')

                    # Check if user can access this broadcast file
                    can_access = False

                    if broadcast_type == "all_users":
                        can_access = True
                    elif broadcast_type == "dot_users":
                        target_dot_id = metadata.get('target_dot_id')
                        if target_dot_id in user_accessible_dots:
                            can_access = True
                    elif broadcast_type == "selected_users":
                        target_user_ids = metadata.get('target_user_ids', [])
                        if user.id in target_user_ids:
                            can_access = True

                    # Admin users can access all broadcasts
                    if user.is_superuser or user.is_staff:
                        can_access = True

                    if can_access:
                        # Get broadcaster info
                        broadcaster = db.query(User).filter(
                            User.id == metadata.get('broadcast_by')
                        ).first()

                        accessible_files.append({
                            "file_id": file_upload.id,
                            "filename": file_upload.original_filename,
                            "file_size": file_upload.file_size,
                            "mime_type": file_upload.mime_type,
                            "broadcast_type": broadcast_type,
                            "broadcast_by": broadcaster.username if broadcaster else "Unknown",
                            "broadcast_at": metadata.get('broadcast_at'),
                            "broadcast_message": metadata.get('broadcast_message'),
                            "priority": metadata.get('priority', 'normal'),
                            "created_at": file_upload.created_at.isoformat()
                        })

                except Exception as e:
                    logger.error(f"Error processing broadcast file {file_upload.id}: {e}")

            return accessible_files

        except Exception as e:
            logger.error(f"Error getting broadcast files: {e}")
            return []

# Global admin broadcast service instance
admin_broadcast_service = AdminBroadcastService()