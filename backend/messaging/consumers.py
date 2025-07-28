import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from .models import Conversation, Message
from .serializers import MessageSerializer

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Handle WebSocket connection with proper authentication
        """
        try:
            self.user = self.scope["user"]
            self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]

            # Check authentication
            if self.user.is_anonymous:
                logger.warning(
                    f"Anonymous user attempted to connect to chat {self.conversation_id}")
                await self.close(code=4001)
                return

            # Validate conversation ID
            if not self.conversation_id or not self.conversation_id.isdigit():
                logger.warning(
                    f"Invalid conversation ID: {self.conversation_id}")
                await self.close(code=4002)
                return

            # Check if user has permission to access this conversation
            has_permission = await self.check_conversation_permission(
                self.user.id, int(self.conversation_id)
            )

            if not has_permission:
                logger.warning(
                    f"User {self.user.id} denied access to conversation {self.conversation_id}")
                await self.close(code=4003)
                return

            self.group_name = f"chat_{self.conversation_id}"

            # Join conversation group
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

            logger.info(
                f"User {self.user.username} connected to conversation {self.conversation_id}")

        except Exception as e:
            logger.error(f"Error in ChatConsumer connect: {str(e)}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection
        """
        try:
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
                logger.info(
                    f"User {self.user.username} disconnected from conversation {self.conversation_id}")
        except Exception as e:
            logger.error(f"Error in ChatConsumer disconnect: {str(e)}")

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages with validation
        """
        try:
            # Parse JSON data
            try:
                data = json.loads(text_data)
            except json.JSONDecodeError:
                await self.send_error("Invalid JSON format")
                return

            # Validate message type
            message_type = data.get("type", "message")
            if message_type not in ["message", "typing", "read_receipt"]:
                await self.send_error("Invalid message type")
                return

            # Handle different message types
            if message_type == "message":
                await self.handle_message(data)
            elif message_type == "typing":
                await self.handle_typing(data)
            elif message_type == "read_receipt":
                await self.handle_read_receipt(data)

        except Exception as e:
            logger.error(f"Error in ChatConsumer receive: {str(e)}")
            await self.send_error("Internal server error")

    async def handle_message(self, data):
        """
        Handle regular chat messages
        """
        try:
            content = data.get("content", "").strip()

            # Validate content
            if not content:
                await self.send_error("Message content cannot be empty")
                return

            if len(content) > 5000:  # Limit message length
                await self.send_error("Message too long (max 5000 characters)")
                return

            # Create message in database
            message = await self.create_message(
                self.user.id,
                int(self.conversation_id),
                content
            )

            if message:
                # Serialize message
                serialized = await self.serialize_message(message)

                # Send to group
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "chat_message",
                        "message": serialized,
                    }
                )

                logger.info(
                    f"Message sent by {self.user.username} in conversation {self.conversation_id}")
            else:
                await self.send_error("Failed to create message")

        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
            await self.send_error("Error processing message")

    async def handle_typing(self, data):
        """
        Handle typing indicators
        """
        try:
            is_typing = data.get("is_typing", False)

            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "typing_indicator",
                    "user_id": self.user.id,
                    "username": self.user.username,
                    "is_typing": is_typing,
                }
            )

        except Exception as e:
            logger.error(f"Error handling typing indicator: {str(e)}")

    async def handle_read_receipt(self, data):
        """
        Handle read receipts
        """
        try:
            message_id = data.get("message_id")

            if message_id:
                # Mark message as read (implement in your models)
                await self.mark_message_as_read(self.user.id, message_id)

                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "read_receipt",
                        "message_id": message_id,
                        "user_id": self.user.id,
                        "username": self.user.username,
                    }
                )

        except Exception as e:
            logger.error(f"Error handling read receipt: {str(e)}")

    async def chat_message(self, event):
        """
        Send message to WebSocket
        """
        try:
            await self.send(text_data=json.dumps({
                "type": "message",
                "message": event["message"]
            }))
        except Exception as e:
            logger.error(f"Error sending chat message: {str(e)}")

    async def typing_indicator(self, event):
        """
        Send typing indicator to WebSocket
        """
        try:
            # Don't send typing indicator to the sender
            if event["user_id"] != self.user.id:
                await self.send(text_data=json.dumps({
                    "type": "typing",
                    "user_id": event["user_id"],
                    "username": event["username"],
                    "is_typing": event["is_typing"]
                }))
        except Exception as e:
            logger.error(f"Error sending typing indicator: {str(e)}")

    async def read_receipt(self, event):
        """
        Send read receipt to WebSocket
        """
        try:
            await self.send(text_data=json.dumps({
                "type": "read_receipt",
                "message_id": event["message_id"],
                "user_id": event["user_id"],
                "username": event["username"]
            }))
        except Exception as e:
            logger.error(f"Error sending read receipt: {str(e)}")

    async def send_error(self, error_message):
        """
        Send error message to client
        """
        try:
            await self.send(text_data=json.dumps({
                "type": "error",
                "error": error_message
            }))
        except Exception as e:
            logger.error(f"Error sending error message: {str(e)}")

    @database_sync_to_async
    def check_conversation_permission(self, user_id, conversation_id):
        """
        Check if user has permission to access conversation
        """
        try:
            conversation = Conversation.objects.filter(
                id=conversation_id,
                participants__id=user_id
            ).first()
            return conversation is not None
        except Exception as e:
            logger.error(f"Error checking conversation permission: {str(e)}")
            return False

    @database_sync_to_async
    def create_message(self, user_id, conversation_id, content):
        """
        Create message in database with validation
        """
        try:
            from django.contrib.auth.models import User

            user = User.objects.get(id=user_id)
            conversation = Conversation.objects.get(
                id=conversation_id,
                participants=user
            )

            # Additional security check
            if not conversation.participants.filter(id=user_id).exists():
                logger.warning(
                    f"User {user_id} not a participant in conversation {conversation_id}")
                return None

            message = Message.objects.create(
                conversation=conversation,
                sender=user,
                content=content,
                message_type='text'
            )

            return message

        except Exception as e:
            logger.error(f"Error creating message: {str(e)}")
            return None

    @database_sync_to_async
    def serialize_message(self, message):
        """
        Serialize message for WebSocket transmission
        """
        try:
            serializer = MessageSerializer(message)
            return serializer.data
        except Exception as e:
            logger.error(f"Error serializing message: {str(e)}")
            return None

    @database_sync_to_async
    def mark_message_as_read(self, user_id, message_id):
        """
        Mark message as read by user
        """
        try:
            # Implement read tracking logic here
            # This could involve updating a MessageRead model or similar
            pass
        except Exception as e:
            logger.error(f"Error marking message as read: {str(e)}")
