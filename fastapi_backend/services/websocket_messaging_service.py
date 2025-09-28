import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any, List
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from services.secure_messaging_service import secure_messaging_service
from services.dot_service import DOTService
from services.audit_service import audit_service
from models.user import User
from models.conversation import ConversationParticipant
from core.security import verify_token

logger = logging.getLogger(__name__)

class WebSocketMessagingManager:
    """WebSocket manager for real-time messaging with security"""

    def __init__(self):
        # Active WebSocket connections by user ID
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Conversation subscriptions: conversation_id -> set of user_ids
        self.conversation_subscriptions: Dict[int, Set[int]] = {}
        # WebSocket to user mapping for cleanup
        self.websocket_to_user: Dict[WebSocket, int] = {}
        # Rate limiting: user_id -> {last_message_time, message_count}
        self.rate_limits: Dict[int, Dict[str, Any]] = {}

    async def authenticate_websocket(self, websocket: WebSocket, token: str, db: Session) -> Optional[User]:
        """Authenticate WebSocket connection using JWT token"""
        try:
            # Verify JWT token
            payload = verify_token(token)
            if not payload:
                await websocket.close(code=4001, reason="Invalid token")
                return None

            user_id = payload.get("user_id")
            if not user_id:
                await websocket.close(code=4001, reason="Invalid user")
                return None

            # Get user from database
            user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
            if not user:
                await websocket.close(code=4001, reason="User not found or inactive")
                return None

            return user

        except Exception as e:
            logger.error(f"WebSocket authentication error: {e}")
            await websocket.close(code=4001, reason="Authentication failed")
            return None

    async def connect_user(self, websocket: WebSocket, user: User, db: Session):
        """Connect a user's WebSocket with security validation"""
        try:
            await websocket.accept()

            user_id = user.id

            # Initialize user connections if not exists
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()

            # Add WebSocket to user's connections
            self.active_connections[user_id].add(websocket)
            self.websocket_to_user[websocket] = user_id

            # Initialize rate limiting
            self.rate_limits[user_id] = {
                "last_message_time": datetime.utcnow(),
                "message_count": 0,
                "last_reset": datetime.utcnow()
            }

            # Log connection
            audit_service.log_activity(
                db=db,
                user_id=user_id,
                action="websocket_connected",
                resource_type="websocket",
                details=f"User connected to WebSocket messaging",
                severity="info"
            )

            logger.info(f"User {user_id} connected to WebSocket messaging")

            # Send connection confirmation
            await self._send_to_user(user_id, {
                "type": "connection_confirmed",
                "data": {
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })

        except Exception as e:
            logger.error(f"Error connecting user WebSocket: {e}")
            await websocket.close(code=4000, reason="Connection failed")

    async def disconnect_user(self, websocket: WebSocket, db: Session):
        """Disconnect user WebSocket"""
        try:
            user_id = self.websocket_to_user.get(websocket)
            if not user_id:
                return

            # Remove from active connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

            # Remove from conversation subscriptions
            for conversation_id, subscribers in list(self.conversation_subscriptions.items()):
                subscribers.discard(user_id)
                if not subscribers:
                    del self.conversation_subscriptions[conversation_id]

            # Clean up mappings
            del self.websocket_to_user[websocket]
            if user_id in self.rate_limits:
                del self.rate_limits[user_id]

            # Log disconnection
            audit_service.log_activity(
                db=db,
                user_id=user_id,
                action="websocket_disconnected",
                resource_type="websocket",
                details=f"User disconnected from WebSocket messaging",
                severity="info"
            )

            logger.info(f"User {user_id} disconnected from WebSocket messaging")

        except Exception as e:
            logger.error(f"Error disconnecting user WebSocket: {e}")

    async def subscribe_to_conversation(self, user_id: int, conversation_id: int, db: Session) -> bool:
        """Subscribe user to conversation updates"""
        try:
            # Validate user can access conversation
            if not secure_messaging_service.can_user_access_conversation(db, user_id, conversation_id):
                return False

            # Add to subscriptions
            if conversation_id not in self.conversation_subscriptions:
                self.conversation_subscriptions[conversation_id] = set()

            self.conversation_subscriptions[conversation_id].add(user_id)

            # Send confirmation
            await self._send_to_user(user_id, {
                "type": "conversation_subscribed",
                "data": {
                    "conversation_id": conversation_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })

            logger.info(f"User {user_id} subscribed to conversation {conversation_id}")
            return True

        except Exception as e:
            logger.error(f"Error subscribing to conversation: {e}")
            return False

    async def unsubscribe_from_conversation(self, user_id: int, conversation_id: int):
        """Unsubscribe user from conversation updates"""
        try:
            if conversation_id in self.conversation_subscriptions:
                self.conversation_subscriptions[conversation_id].discard(user_id)
                if not self.conversation_subscriptions[conversation_id]:
                    del self.conversation_subscriptions[conversation_id]

            await self._send_to_user(user_id, {
                "type": "conversation_unsubscribed",
                "data": {
                    "conversation_id": conversation_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            })

            logger.info(f"User {user_id} unsubscribed from conversation {conversation_id}")

        except Exception as e:
            logger.error(f"Error unsubscribing from conversation: {e}")

    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user is within rate limits"""
        try:
            current_time = datetime.utcnow()

            if user_id not in self.rate_limits:
                return True

            rate_data = self.rate_limits[user_id]

            # Reset counter every minute
            if (current_time - rate_data["last_reset"]).total_seconds() > 60:
                rate_data["message_count"] = 0
                rate_data["last_reset"] = current_time

            # Check if user exceeded rate limit (30 messages per minute)
            if rate_data["message_count"] >= 30:
                return False

            # Check if user is sending messages too quickly (max 1 per second)
            if (current_time - rate_data["last_message_time"]).total_seconds() < 1:
                return False

            return True

        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True

    async def handle_message(self, websocket: WebSocket, message_data: dict, db: Session):
        """Handle incoming WebSocket message"""
        try:
            user_id = self.websocket_to_user.get(websocket)
            if not user_id:
                await websocket.close(code=4001, reason="Unauthorized")
                return

            # Check rate limits
            if not self._check_rate_limit(user_id):
                await self._send_to_websocket(websocket, {
                    "type": "rate_limit_exceeded",
                    "error": "Too many messages. Please slow down."
                })
                return

            # Update rate limit counters
            if user_id in self.rate_limits:
                self.rate_limits[user_id]["message_count"] += 1
                self.rate_limits[user_id]["last_message_time"] = datetime.utcnow()

            message_type = message_data.get("type")
            data = message_data.get("data", {})

            if message_type == "send_message":
                await self._handle_send_message(user_id, data, db)

            elif message_type == "edit_message":
                await self._handle_edit_message(user_id, data, db)

            elif message_type == "delete_message":
                await self._handle_delete_message(user_id, data, db)

            elif message_type == "subscribe_conversation":
                conversation_id = data.get("conversation_id")
                if conversation_id:
                    await self.subscribe_to_conversation(user_id, conversation_id, db)

            elif message_type == "unsubscribe_conversation":
                conversation_id = data.get("conversation_id")
                if conversation_id:
                    await self.unsubscribe_from_conversation(user_id, conversation_id)

            elif message_type == "typing_start":
                await self._handle_typing_indicator(user_id, data, "typing_start")

            elif message_type == "typing_stop":
                await self._handle_typing_indicator(user_id, data, "typing_stop")

            elif message_type == "message_read":
                await self._handle_message_read(user_id, data, db)

            else:
                await self._send_to_websocket(websocket, {
                    "type": "error",
                    "error": f"Unknown message type: {message_type}"
                })

        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
            await self._send_to_websocket(websocket, {
                "type": "error",
                "error": "Failed to process message"
            })

    async def _handle_send_message(self, user_id: int, data: dict, db: Session):
        """Handle sending a new message"""
        try:
            conversation_id = data.get("conversation_id")
            content = data.get("content", "")
            message_type = data.get("message_type", "text")
            metadata = data.get("metadata", {})
            reply_to_id = data.get("reply_to_id")

            if not conversation_id or not content.strip():
                await self._send_to_user(user_id, {
                    "type": "error",
                    "error": "Missing required fields"
                })
                return

            # Send message using secure messaging service
            message = secure_messaging_service.send_secure_message(
                db=db,
                sender_id=user_id,
                conversation_id=conversation_id,
                content=content,
                message_type=message_type,
                metadata=metadata,
                reply_to_id=reply_to_id
            )

            if message:
                # Broadcast to conversation subscribers
                await self._broadcast_to_conversation(conversation_id, {
                    "type": "new_message",
                    "data": {
                        "message_id": message.id,
                        "conversation_id": conversation_id,
                        "sender_id": user_id,
                        "content": content,
                        "message_type": message_type,
                        "metadata": metadata,
                        "created_at": message.created_at.isoformat(),
                        "reply_to_id": reply_to_id
                    }
                }, exclude_user=user_id)

                # Send confirmation to sender
                await self._send_to_user(user_id, {
                    "type": "message_sent",
                    "data": {
                        "message_id": message.id,
                        "conversation_id": conversation_id,
                        "timestamp": message.created_at.isoformat()
                    }
                })

            else:
                await self._send_to_user(user_id, {
                    "type": "error",
                    "error": "Failed to send message"
                })

        except Exception as e:
            logger.error(f"Error handling send message: {e}")
            await self._send_to_user(user_id, {
                "type": "error",
                "error": "Failed to send message"
            })

    async def _handle_edit_message(self, user_id: int, data: dict, db: Session):
        """Handle editing a message"""
        try:
            message_id = data.get("message_id")
            new_content = data.get("content", "")

            if not message_id or not new_content.strip():
                await self._send_to_user(user_id, {
                    "type": "error",
                    "error": "Missing required fields"
                })
                return

            success = secure_messaging_service.edit_message(
                db=db,
                user_id=user_id,
                message_id=message_id,
                new_content=new_content
            )

            if success:
                # Get message to broadcast update
                from models.message import Message
                message = db.query(Message).filter(Message.id == message_id).first()

                if message:
                    # Broadcast to conversation subscribers
                    await self._broadcast_to_conversation(message.conversation_id, {
                        "type": "message_edited",
                        "data": {
                            "message_id": message_id,
                            "conversation_id": message.conversation_id,
                            "new_content": new_content,
                            "edited_at": datetime.utcnow().isoformat(),
                            "edited_by": user_id
                        }
                    })

            else:
                await self._send_to_user(user_id, {
                    "type": "error",
                    "error": "Failed to edit message"
                })

        except Exception as e:
            logger.error(f"Error handling edit message: {e}")
            await self._send_to_user(user_id, {
                "type": "error",
                "error": "Failed to edit message"
            })

    async def _handle_delete_message(self, user_id: int, data: dict, db: Session):
        """Handle deleting a message"""
        try:
            message_id = data.get("message_id")

            if not message_id:
                await self._send_to_user(user_id, {
                    "type": "error",
                    "error": "Missing message ID"
                })
                return

            # Get message first to get conversation_id
            from models.message import Message
            message = db.query(Message).filter(Message.id == message_id).first()

            if not message:
                await self._send_to_user(user_id, {
                    "type": "error",
                    "error": "Message not found"
                })
                return

            conversation_id = message.conversation_id

            success = secure_messaging_service.delete_message_securely(
                db=db,
                user_id=user_id,
                message_id=message_id
            )

            if success:
                # Broadcast to conversation subscribers
                await self._broadcast_to_conversation(conversation_id, {
                    "type": "message_deleted",
                    "data": {
                        "message_id": message_id,
                        "conversation_id": conversation_id,
                        "deleted_by": user_id,
                        "deleted_at": datetime.utcnow().isoformat()
                    }
                })

            else:
                await self._send_to_user(user_id, {
                    "type": "error",
                    "error": "Failed to delete message"
                })

        except Exception as e:
            logger.error(f"Error handling delete message: {e}")

    async def _handle_typing_indicator(self, user_id: int, data: dict, typing_status: str):
        """Handle typing indicators"""
        try:
            conversation_id = data.get("conversation_id")
            if not conversation_id:
                return

            # Broadcast typing status to conversation subscribers
            await self._broadcast_to_conversation(conversation_id, {
                "type": typing_status,
                "data": {
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }, exclude_user=user_id)

        except Exception as e:
            logger.error(f"Error handling typing indicator: {e}")

    async def _handle_message_read(self, user_id: int, data: dict, db: Session):
        """Handle message read receipts"""
        try:
            message_id = data.get("message_id")
            conversation_id = data.get("conversation_id")

            if not message_id or not conversation_id:
                return

            # TODO: Implement read receipts in database
            # For now, just broadcast the read status
            await self._broadcast_to_conversation(conversation_id, {
                "type": "message_read",
                "data": {
                    "message_id": message_id,
                    "read_by": user_id,
                    "read_at": datetime.utcnow().isoformat()
                }
            }, exclude_user=user_id)

        except Exception as e:
            logger.error(f"Error handling message read: {e}")

    async def _send_to_user(self, user_id: int, message: dict):
        """Send message to all WebSocket connections of a user"""
        if user_id in self.active_connections:
            disconnected = set()
            for websocket in self.active_connections[user_id]:
                try:
                    await self._send_to_websocket(websocket, message)
                except:
                    disconnected.add(websocket)

            # Clean up disconnected WebSockets
            for websocket in disconnected:
                self.active_connections[user_id].discard(websocket)

    async def _send_to_websocket(self, websocket: WebSocket, message: dict):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            raise

    async def _broadcast_to_conversation(self, conversation_id: int, message: dict, exclude_user: Optional[int] = None):
        """Broadcast message to all subscribers of a conversation"""
        if conversation_id in self.conversation_subscriptions:
            subscribers = self.conversation_subscriptions[conversation_id].copy()

            if exclude_user:
                subscribers.discard(exclude_user)

            for user_id in subscribers:
                await self._send_to_user(user_id, message)

    def get_active_users(self) -> List[int]:
        """Get list of currently connected user IDs"""
        return list(self.active_connections.keys())

    def get_conversation_subscribers(self, conversation_id: int) -> List[int]:
        """Get list of users subscribed to a conversation"""
        return list(self.conversation_subscriptions.get(conversation_id, set()))

# Global WebSocket manager instance
websocket_messaging_manager = WebSocketMessagingManager()