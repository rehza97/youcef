import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Notification


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get user from scope
        self.user = self.scope["user"]

        if not self.user.is_authenticated:
            await self.close()
            return

        # Join user's notification group
        self.room_group_name = f"notifications_{self.user.id}"
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave user's notification group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        # Handle incoming messages (if needed)
        pass

    async def notification_message(self, event):
        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))

    @database_sync_to_async
    def get_user_notifications(self):
        """Get user's unread notifications"""
        return list(Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).values('id', 'title', 'message', 'notification_type', 'created_at'))

    async def send_notification(self, notification_data):
        """Send notification to user"""
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'notification_message',
                'notification': notification_data
            }
        )
