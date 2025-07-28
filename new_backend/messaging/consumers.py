import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Conversation, Message, UserBlock


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Get user and conversation from scope
        self.user = self.scope["user"]
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']

        if not self.user.is_authenticated:
            await self.close()
            return

        # Check if user is participant in conversation
        if not await self.is_participant():
            await self.close()
            return

        # Join conversation group
        self.room_group_name = f"chat_{self.conversation_id}"
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave conversation group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'message')
        content = text_data_json.get('content', '')

        if message_type == 'message':
            # Save message to database
            message = await self.save_message(content)

            # Send message to conversation group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': message.id,
                        'sender': message.sender.username,
                        'content': message.content,
                        'message_type': message.message_type,
                        'created_at': message.created_at.isoformat()
                    }
                }
            )

    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message']
        }))

    @database_sync_to_async
    def is_participant(self):
        """Check if user is participant in conversation"""
        try:
            conversation = Conversation.objects.get(id=self.conversation_id)
            return conversation.participants.filter(id=self.user.id).exists()
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, content):
        """Save message to database"""
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message.objects.create(
            conversation=conversation,
            sender=self.user,
            content=content,
            message_type='text'
        )
        return message

    @database_sync_to_async
    def check_blocked(self, sender, recipient):
        """Check if sender is blocked by recipient"""
        return UserBlock.objects.filter(
            blocker=recipient,
            blocked_user=sender
        ).exists()
