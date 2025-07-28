import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from .models import Conversation, Message
from .serializers import MessageSerializer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        if self.user.is_anonymous:
            await self.close()
        else:
            self.group_name = f"chat_{self.conversation_id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        content = data.get("content", "")
        # Optionally: handle file uploads via REST, not WebSocket
        message = await self.create_message(self.user, self.conversation_id, content)
        serialized = MessageSerializer(message).data
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat_message",
                "message": serialized,
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))

    @database_sync_to_async
    def create_message(self, user, conversation_id, content):
        conversation = Conversation.objects.get(id=conversation_id)
        return Message.objects.create(conversation=conversation, sender=user, content=content, message_type='text')
