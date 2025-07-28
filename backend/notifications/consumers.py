import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
        if self.user.is_anonymous or str(self.user.id) != self.user_id:
            await self.close()
        else:
            self.group_name = f"notifications_{self.user_id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # No-op: notifications are pushed from server
        pass

    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event["notification"]))
