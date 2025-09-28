import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from models.conversation import Conversation, ConversationParticipant
from models.message import Message, MessageReaction
from models.user import User
from services.dot_service import DOTService
from services.encryption_service import EncryptionService
from services.audit_service import AuditService

logger = logging.getLogger(__name__)

class SecureMessagingService:
    """Secure messaging service with DOT-based access control and encryption"""

    def __init__(self):
        self.encryption_service = EncryptionService()
        self.audit_service = AuditService()

    def _sanitize_message_content(self, content: str) -> str:
        """Sanitize message content to prevent XSS and injection attacks"""
        if not content:
            return ""

        # Basic HTML/script sanitization
        dangerous_tags = ['<script', '</script>', '<iframe', '</iframe>', '<object', '</object>']
        sanitized = content

        for tag in dangerous_tags:
            sanitized = sanitized.replace(tag.lower(), f"[BLOCKED]{tag}[/BLOCKED]")
            sanitized = sanitized.replace(tag.upper(), f"[BLOCKED]{tag}[/BLOCKED]")

        # Remove potential javascript/vbscript URIs
        dangerous_protocols = ['javascript:', 'vbscript:', 'data:']
        for protocol in dangerous_protocols:
            sanitized = sanitized.replace(protocol, f"[BLOCKED]{protocol}[/BLOCKED]")

        # Limit message length
        if len(sanitized) > 4000:
            sanitized = sanitized[:3997] + "..."

        return sanitized.strip()

    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize message metadata to prevent injection"""
        if not metadata:
            return {}

        sanitized = {}
        allowed_keys = ['file_id', 'filename', 'file_size', 'mime_type', 'reply_to', 'thread_id', 'edited_at']

        for key, value in metadata.items():
            if key in allowed_keys:
                # Sanitize string values
                if isinstance(value, str):
                    sanitized[key] = self._sanitize_message_content(value)
                elif isinstance(value, (int, float, bool)):
                    sanitized[key] = value
                elif isinstance(value, dict):
                    # Recursively sanitize nested objects
                    sanitized[key] = self._sanitize_metadata(value)

        return sanitized

    def can_user_access_conversation(
        self,
        db: Session,
        user_id: int,
        conversation_id: int
    ) -> bool:
        """Check if user can access a conversation based on DOT permissions"""
        try:
            # Check if user is a participant
            participant = db.query(ConversationParticipant).filter(
                ConversationParticipant.conversation_id == conversation_id,
                ConversationParticipant.user_id == user_id
            ).first()

            if not participant:
                return False

            # Get user and conversation
            user = db.query(User).filter(User.id == user_id).first()
            conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

            if not user or not conversation:
                return False

            # Superusers and staff have access to all conversations
            if user.is_superuser or user.is_staff:
                return True

            # For regular users, check DOT-based permissions
            # Get all participants in the conversation
            participants = db.query(ConversationParticipant).filter(
                ConversationParticipant.conversation_id == conversation_id
            ).all()

            participant_users = db.query(User).filter(
                User.id.in_([p.user_id for p in participants])
            ).all()

            # Check if user can communicate with all participants based on DOT permissions
            user_accessible_dots = DOTService.get_user_accessible_dots(db, user_id)

            for participant_user in participant_users:
                if participant_user.id == user_id:
                    continue  # Skip self

                # Check if participant is in user's accessible DOTs
                if participant_user.dot_id and participant_user.dot_id not in user_accessible_dots:
                    return False

            return True

        except Exception as e:
            logger.error(f"Error checking conversation access: {e}")
            return False

    def get_user_accessible_conversations(
        self,
        db: Session,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Conversation]:
        """Get conversations accessible to user based on DOT permissions"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return []

            # Base query for user's conversations
            base_query = db.query(Conversation).join(
                ConversationParticipant,
                Conversation.id == ConversationParticipant.conversation_id
            ).filter(
                ConversationParticipant.user_id == user_id,
                Conversation.is_active == True
            )

            # For superusers and staff, return all conversations
            if user.is_superuser or user.is_staff:
                return base_query.offset(offset).limit(limit).all()

            # For regular users, filter by DOT permissions
            accessible_conversations = []
            conversations = base_query.offset(offset).limit(limit * 2).all()  # Get more to filter

            for conversation in conversations:
                if self.can_user_access_conversation(db, user_id, conversation.id):
                    accessible_conversations.append(conversation)
                    if len(accessible_conversations) >= limit:
                        break

            return accessible_conversations

        except Exception as e:
            logger.error(f"Error getting accessible conversations: {e}")
            return []

    def create_secure_conversation(
        self,
        db: Session,
        creator_id: int,
        participant_ids: List[int],
        name: Optional[str] = None,
        conversation_type: str = "group",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Conversation]:
        """Create a conversation with DOT-based validation"""
        try:
            creator = db.query(User).filter(User.id == creator_id).first()
            if not creator:
                raise ValueError("Creator not found")

            # Validate that creator can communicate with all participants
            if not creator.is_superuser and not creator.is_staff:
                creator_accessible_dots = DOTService.get_user_accessible_dots(db, creator_id)

                for participant_id in participant_ids:
                    if participant_id == creator_id:
                        continue

                    participant = db.query(User).filter(User.id == participant_id).first()
                    if not participant:
                        raise ValueError(f"Participant {participant_id} not found")

                    if participant.dot_id and participant.dot_id not in creator_accessible_dots:
                        raise ValueError(f"Cannot add participant from different DOT region")

            # Sanitize metadata
            sanitized_metadata = self._sanitize_metadata(metadata or {})

            # Create conversation
            conversation = Conversation(
                name=self._sanitize_message_content(name) if name else None,
                conversation_type=conversation_type,
                conversation_metadata=sanitized_metadata,
                created_by=creator_id,
                created_at=datetime.utcnow()
            )

            db.add(conversation)
            db.commit()
            db.refresh(conversation)

            # Add creator as admin participant
            creator_participant = ConversationParticipant(
                conversation_id=conversation.id,
                user_id=creator_id,
                is_admin=True,
                joined_at=datetime.utcnow()
            )
            db.add(creator_participant)

            # Add other participants
            for participant_id in participant_ids:
                if participant_id != creator_id:
                    participant = ConversationParticipant(
                        conversation_id=conversation.id,
                        user_id=participant_id,
                        joined_at=datetime.utcnow()
                    )
                    db.add(participant)

            db.commit()

            # Log conversation creation
            self.audit_service.log_activity(
                db=db,
                user_id=creator_id,
                action="conversation_created",
                resource_type="conversation",
                resource_id=conversation.id,
                details=f"Created conversation with {len(participant_ids)} participants"
            )

            return conversation

        except Exception as e:
            logger.error(f"Error creating secure conversation: {e}")
            db.rollback()
            return None

    def send_secure_message(
        self,
        db: Session,
        sender_id: int,
        conversation_id: int,
        content: str,
        message_type: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
        reply_to_id: Optional[int] = None
    ) -> Optional[Message]:
        """Send a message with encryption and validation"""
        try:
            # Validate conversation access
            if not self.can_user_access_conversation(db, sender_id, conversation_id):
                raise ValueError("User cannot access this conversation")

            # Sanitize content and metadata
            sanitized_content = self._sanitize_message_content(content)
            sanitized_metadata = self._sanitize_metadata(metadata or {})

            # Add reply information if applicable
            if reply_to_id:
                # Validate reply-to message exists and is in same conversation
                reply_to_message = db.query(Message).filter(
                    Message.id == reply_to_id,
                    Message.conversation_id == conversation_id
                ).first()
                if reply_to_message:
                    sanitized_metadata['reply_to'] = reply_to_id
                    sanitized_metadata['reply_to_sender'] = reply_to_message.sender_id

            # Encrypt sensitive content
            encrypted_content = self.encryption_service.encrypt_message(sanitized_content)

            # Create message
            message = Message(
                conversation_id=conversation_id,
                sender_id=sender_id,
                content=encrypted_content,
                message_type=message_type,
                message_metadata=sanitized_metadata,
                created_at=datetime.utcnow()
            )

            db.add(message)
            db.commit()
            db.refresh(message)

            # Log message sending
            self.audit_service.log_activity(
                db=db,
                user_id=sender_id,
                action="message_sent",
                resource_type="message",
                resource_id=message.id,
                details=f"Sent {message_type} message to conversation {conversation_id}"
            )

            return message

        except Exception as e:
            logger.error(f"Error sending secure message: {e}")
            db.rollback()
            return None

    def get_conversation_messages(
        self,
        db: Session,
        user_id: int,
        conversation_id: int,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """Get conversation messages with decryption and access control"""
        try:
            # Validate conversation access
            if not self.can_user_access_conversation(db, user_id, conversation_id):
                return []

            # Query messages
            query = db.query(Message).filter(
                Message.conversation_id == conversation_id
            )

            if not include_deleted:
                query = query.filter(Message.is_deleted == False)

            messages = query.order_by(Message.created_at.asc()).offset(offset).limit(limit).all()

            # Decrypt and format messages
            formatted_messages = []
            for message in messages:
                try:
                    # Decrypt content
                    decrypted_content = self.encryption_service.decrypt_message(message.content)

                    # Get sender info
                    sender = db.query(User).filter(User.id == message.sender_id).first()

                    formatted_message = {
                        "id": message.id,
                        "conversation_id": message.conversation_id,
                        "sender_id": message.sender_id,
                        "sender_username": sender.username if sender else "Unknown",
                        "content": decrypted_content,
                        "message_type": message.message_type,
                        "message_metadata": message.message_metadata or {},
                        "is_edited": message.is_edited,
                        "is_deleted": message.is_deleted,
                        "created_at": message.created_at.isoformat(),
                        "updated_at": message.updated_at.isoformat() if message.updated_at else None
                    }

                    formatted_messages.append(formatted_message)

                except Exception as decrypt_error:
                    logger.error(f"Error decrypting message {message.id}: {decrypt_error}")
                    # Add placeholder for failed decryption
                    formatted_messages.append({
                        "id": message.id,
                        "content": "[Message could not be decrypted]",
                        "message_type": "error",
                        "created_at": message.created_at.isoformat(),
                        "sender_id": message.sender_id
                    })

            # Log message access
            self.audit_service.log_activity(
                db=db,
                user_id=user_id,
                action="messages_accessed",
                resource_type="conversation",
                resource_id=conversation_id,
                details=f"Accessed {len(formatted_messages)} messages"
            )

            return formatted_messages

        except Exception as e:
            logger.error(f"Error getting conversation messages: {e}")
            return []

    def delete_message_securely(
        self,
        db: Session,
        user_id: int,
        message_id: int,
        hard_delete: bool = False
    ) -> bool:
        """Delete message with proper authorization"""
        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if not message:
                return False

            # Check if user can delete the message
            user = db.query(User).filter(User.id == user_id).first()
            can_delete = (
                message.sender_id == user_id or  # Message sender
                (user and (user.is_superuser or user.is_staff))  # Admin
            )

            if not can_delete:
                return False

            if hard_delete:
                # Permanently delete message
                db.delete(message)
            else:
                # Soft delete - mark as deleted and clear content
                message.is_deleted = True
                message.content = self.encryption_service.encrypt_message("[Message deleted]")
                message.updated_at = datetime.utcnow()

            db.commit()

            # Log message deletion
            self.audit_service.log_activity(
                db=db,
                user_id=user_id,
                action="message_deleted",
                resource_type="message",
                resource_id=message_id,
                details=f"{'Hard' if hard_delete else 'Soft'} deleted message"
            )

            return True

        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            db.rollback()
            return False

    def edit_message(
        self,
        db: Session,
        user_id: int,
        message_id: int,
        new_content: str
    ) -> bool:
        """Edit message with proper authorization"""
        try:
            message = db.query(Message).filter(Message.id == message_id).first()
            if not message or message.sender_id != user_id or message.is_deleted:
                return False

            # Sanitize new content
            sanitized_content = self._sanitize_message_content(new_content)
            encrypted_content = self.encryption_service.encrypt_message(sanitized_content)

            # Update message
            message.content = encrypted_content
            message.is_edited = True
            message.updated_at = datetime.utcnow()

            # Add edit history to metadata
            current_metadata = message.message_metadata or {}
            if 'edit_history' not in current_metadata:
                current_metadata['edit_history'] = []

            current_metadata['edit_history'].append({
                'edited_at': datetime.utcnow().isoformat(),
                'edited_by': user_id
            })
            message.message_metadata = current_metadata

            db.commit()

            # Log message edit
            self.audit_service.log_activity(
                db=db,
                user_id=user_id,
                action="message_edited",
                resource_type="message",
                resource_id=message_id,
                details="Message content updated"
            )

            return True

        except Exception as e:
            logger.error(f"Error editing message: {e}")
            db.rollback()
            return False

# Global instance
secure_messaging_service = SecureMessagingService()