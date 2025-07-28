import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Handle WebSocket connection with proper authentication
        """
        try:
            self.user = self.scope["user"]
            self.user_id = self.scope["url_route"]["kwargs"]["user_id"]

            # Check authentication
            if self.user.is_anonymous:
                logger.warning(
                    f"Anonymous user attempted to connect to notifications")
                await self.close(code=4001)
                return

            # Validate user ID and permissions
            if not self.user_id or not self.user_id.isdigit():
                logger.warning(f"Invalid user ID: {self.user_id}")
                await self.close(code=4002)
                return

            # Check if user can access these notifications
            if int(self.user_id) != self.user.id and not self.user.is_staff:
                logger.warning(
                    f"User {self.user.id} denied access to notifications for user {self.user_id}")
                await self.close(code=4003)
                return

            self.group_name = f"notifications_{self.user_id}"

            # Join notification group
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

            logger.info(
                f"User {self.user.username} connected to notifications channel")

            # Send initial unread count
            await self.send_unread_count()

        except Exception as e:
            logger.error(f"Error in NotificationConsumer connect: {str(e)}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection
        """
        try:
            if hasattr(self, 'group_name'):
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
                logger.info(
                    f"User {self.user.username} disconnected from notifications")
        except Exception as e:
            logger.error(f"Error in NotificationConsumer disconnect: {str(e)}")

    async def receive(self, text_data):
        """
        Handle incoming WebSocket messages
        """
        try:
            # Parse JSON data
            try:
                data = json.loads(text_data)
            except json.JSONDecodeError:
                await self.send_error("Invalid JSON format")
                return

            # Validate message type
            message_type = data.get("type")
            if message_type not in ["mark_read", "get_unread_count", "ping"]:
                await self.send_error("Invalid message type")
                return

            # Handle different message types
            if message_type == "mark_read":
                await self.handle_mark_read(data)
            elif message_type == "get_unread_count":
                await self.send_unread_count()
            elif message_type == "ping":
                await self.send_ping_response()

        except Exception as e:
            logger.error(f"Error in NotificationConsumer receive: {str(e)}")
            await self.send_error("Internal server error")

    async def handle_mark_read(self, data):
        """
        Handle marking notifications as read
        """
        try:
            notification_id = data.get("notification_id")

            if notification_id:
                # Mark single notification as read
                success = await self.mark_notification_read(notification_id)
                if success:
                    await self.send_notification_marked_read(notification_id)
                    await self.send_unread_count()
                else:
                    await self.send_error("Failed to mark notification as read")
            else:
                # Mark all notifications as read
                count = await self.mark_all_notifications_read()
                await self.send_all_notifications_marked_read(count)
                await self.send_unread_count()

        except Exception as e:
            logger.error(f"Error handling mark read: {str(e)}")
            await self.send_error("Error processing mark read request")

    async def send_unread_count(self):
        """
        Send current unread notification count
        """
        try:
            count = await self.get_unread_count()
            await self.send(text_data=json.dumps({
                "type": "unread_count",
                "count": count
            }))
        except Exception as e:
            logger.error(f"Error sending unread count: {str(e)}")

    async def send_ping_response(self):
        """
        Send ping response
        """
        try:
            await self.send(text_data=json.dumps({
                "type": "pong"
            }))
        except Exception as e:
            logger.error(f"Error sending ping response: {str(e)}")

    async def send_notification_marked_read(self, notification_id):
        """
        Send confirmation that notification was marked as read
        """
        try:
            await self.send(text_data=json.dumps({
                "type": "notification_marked_read",
                "notification_id": notification_id
            }))
        except Exception as e:
            logger.error(f"Error sending marked read confirmation: {str(e)}")

    async def send_all_notifications_marked_read(self, count):
        """
        Send confirmation that all notifications were marked as read
        """
        try:
            await self.send(text_data=json.dumps({
                "type": "all_notifications_marked_read",
                "count": count
            }))
        except Exception as e:
            logger.error(
                f"Error sending all marked read confirmation: {str(e)}")

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

    # Channel layer event handlers
    async def notification_created(self, event):
        """
        Send new notification to client
        """
        try:
            await self.send(text_data=json.dumps({
                "type": "new_notification",
                "notification": event["notification"]
            }))
            await self.send_unread_count()
        except Exception as e:
            logger.error(f"Error sending new notification: {str(e)}")

    async def notifications_marked_read(self, event):
        """
        Handle notifications marked as read event
        """
        try:
            await self.send_unread_count()
        except Exception as e:
            logger.error(f"Error handling marked read event: {str(e)}")

    # Database operations
    @database_sync_to_async
    def get_unread_count(self):
        """
        Get unread notification count for user
        """
        try:
            return Notification.objects.filter(
                recipient_id=self.user_id,
                read_at__isnull=True
            ).count()
        except Exception as e:
            logger.error(f"Error getting unread count: {str(e)}")
            return 0

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """
        Mark a single notification as read
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient_id=self.user_id
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            logger.warning(
                f"Notification {notification_id} not found for user {self.user_id}")
            return False
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return False

    @database_sync_to_async
    def mark_all_notifications_read(self):
        """
        Mark all notifications as read for user
        """
        try:
            from django.utils import timezone
            count = Notification.objects.filter(
                recipient_id=self.user_id,
                read_at__isnull=True
            ).update(read_at=timezone.now())
            return count
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {str(e)}")
            return 0
