from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.utils import timezone
from .models import (
    Conversation, Message, MessageReaction, ConversationParticipant,
    UserBlock, MessageAttachment
)
from .serializers import (
    ConversationSerializer, ConversationListSerializer, CreateConversationSerializer,
    MessageSerializer, CreateMessageSerializer, EditMessageSerializer,
    MessageReactionSerializer, MessageReactionCreateSerializer,
    UserBlockSerializer, CreateUserBlockSerializer,
    ConversationStatsSerializer, MessageSearchSerializer,
    ConversationParticipantSerializer
)
from .signals import (
    user_joined_conversation_signal, user_left_conversation_signal,
    conversation_created_signal, message_sent_signal, message_edited_signal,
    message_deleted_signal
)


class ConversationViewSet(viewsets.ModelViewSet):
    """API endpoint for conversations"""
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return conversations for the current user"""
        return Conversation.objects.filter(
            participants=self.request.user,
            is_active=True
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return ConversationListSerializer
        elif self.action == 'create':
            return CreateConversationSerializer
        return ConversationSerializer

    def perform_create(self, serializer):
        """Create conversation and add current user as participant"""
        conversation = serializer.save(created_by=self.request.user)
        conversation.participants.add(self.request.user)

        # Send signal
        conversation_created_signal.send(
            sender=Conversation,
            conversation=conversation,
            created_by=self.request.user,
            participants=conversation.participants.all()
        )

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Join a conversation"""
        conversation = self.get_object()
        user = request.user

        if user not in conversation.participants.all():
            conversation.add_participant(user)

            # Send signal
            user_joined_conversation_signal.send(
                sender=Conversation,
                user=user,
                conversation=conversation
            )

            return Response({'status': 'joined conversation'})
        return Response({'status': 'already a participant'})

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Leave a conversation"""
        conversation = self.get_object()
        user = request.user

        if user in conversation.participants.all():
            # Update participant status
            try:
                participant = ConversationParticipant.objects.get(
                    conversation=conversation,
                    user=user
                )
                participant.leave_conversation()
            except ConversationParticipant.DoesNotExist:
                pass

            # Send signal
            user_left_conversation_signal.send(
                sender=Conversation,
                user=user,
                conversation=conversation
            )

            return Response({'status': 'left conversation'})
        return Response({'status': 'not a participant'})

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark conversation as read"""
        conversation = self.get_object()
        user = request.user

        try:
            participant = ConversationParticipant.objects.get(
                conversation=conversation,
                user=user
            )
            participant.mark_as_read()
            return Response({'status': 'marked as read'})
        except ConversationParticipant.DoesNotExist:
            return Response({'status': 'participant not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get conversation statistics for the current user"""
        user = request.user
        conversations = self.get_queryset()

        stats = {
            'total_conversations': conversations.count(),
            'active_conversations': conversations.filter(is_active=True).count(),
            'total_messages': Message.objects.filter(conversation__participants=user).count(),
            'unread_messages': ConversationParticipant.objects.filter(
                user=user,
                unread_count__gt=0
            ).aggregate(total=Count('unread_count'))['total'] or 0,
            'conversations_by_type': conversations.values('conversation_type').annotate(
                count=Count('id')
            )
        }

        serializer = ConversationStatsSerializer(stats)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """API endpoint for messages"""
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return messages for conversations the user is part of"""
        return Message.objects.filter(
            conversation__participants=self.request.user
        ).exclude(is_deleted=True)

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateMessageSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return EditMessageSerializer
        return MessageSerializer

    def perform_create(self, serializer):
        """Create message and send signal"""
        message = serializer.save()

        # Send signal
        message_sent_signal.send(
            sender=Message,
            message=message
        )

    def perform_update(self, serializer):
        """Update message and send signal"""
        old_content = self.get_object().content
        message = serializer.save()

        # Send signal
        message_edited_signal.send(
            sender=Message,
            message=message,
            old_content=old_content
        )

    @action(detail=True, methods=['post'])
    def delete_message(self, request, pk=None):
        """Soft delete a message"""
        message = self.get_object()

        # Only allow sender to delete
        if message.sender != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        message.delete_message()

        # Send signal
        message_deleted_signal.send(
            sender=Message,
            message=message
        )

        return Response({'status': 'message deleted'})

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """Add reaction to message"""
        message = self.get_object()
        reaction_type = request.data.get('reaction_type')

        if not reaction_type:
            return Response({'error': 'reaction_type required'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if reaction already exists
        reaction, created = MessageReaction.objects.get_or_create(
            message=message,
            user=request.user,
            reaction_type=reaction_type
        )

        if not created:
            # Remove existing reaction
            reaction.delete()
            return Response({'status': 'reaction removed'})

        return Response({'status': 'reaction added'})

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search messages"""
        serializer = MessageSearchSerializer(data=request.query_params)
        if serializer.is_valid():
            data = serializer.validated_data
            queryset = self.get_queryset()

            # Search in content
            if data.get('query'):
                queryset = queryset.filter(content__icontains=data['query'])

            # Filter by conversation
            if data.get('conversation_id'):
                queryset = queryset.filter(
                    conversation_id=data['conversation_id'])

            # Filter by date range
            if data.get('date_from'):
                queryset = queryset.filter(created_at__gte=data['date_from'])

            if data.get('date_to'):
                queryset = queryset.filter(created_at__lte=data['date_to'])

            # Limit results
            queryset = queryset[:50]

            message_serializer = MessageSerializer(queryset, many=True)
            return Response(message_serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='conversations/(?P<conversation_id>[^/.]+)/messages')
    def conversation_messages(self, request, conversation_id=None):
        """Return all messages for a given conversation"""
        conversation = Conversation.objects.filter(
            id=conversation_id, participants=request.user).first()
        if not conversation:
            return Response({'detail': 'Conversation not found.'}, status=404)
        messages = Message.objects.filter(
            conversation=conversation).order_by('created_at')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)


class MessageReactionViewSet(viewsets.ModelViewSet):
    """API endpoint for message reactions"""
    queryset = MessageReaction.objects.all()
    serializer_class = MessageReactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return MessageReactionCreateSerializer
        return MessageReactionSerializer


class UserBlockViewSet(viewsets.ModelViewSet):
    """API endpoint for user blocks"""
    serializer_class = UserBlockSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return blocks created by the current user"""
        return UserBlock.objects.filter(blocker=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateUserBlockSerializer
        return UserBlockSerializer

    @action(detail=False, methods=['get'])
    def blocked_users(self, request):
        """Get list of users blocked by current user"""
        blocked_users = User.objects.filter(blocked_by__blocker=request.user)
        serializer = UserSerializer(blocked_users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def blocked_by(self, request):
        """Get list of users who blocked current user"""
        blocked_by_users = User.objects.filter(
            blocked_users__blocked_user=request.user)
        serializer = UserSerializer(blocked_by_users, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def unblock(self, request):
        """Unblock a user"""
        blocked_user_id = request.data.get('blocked_user_id')

        if not blocked_user_id:
            return Response({'error': 'blocked_user_id required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            block = UserBlock.objects.get(
                blocker=request.user,
                blocked_user_id=blocked_user_id
            )
            block.delete()
            return Response({'status': 'user unblocked'})
        except UserBlock.DoesNotExist:
            return Response({'error': 'block not found'}, status=status.HTTP_404_NOT_FOUND)


class ConversationParticipantViewSet(viewsets.ModelViewSet):
    """API endpoint for conversation participants"""
    queryset = ConversationParticipant.objects.all()
    serializer_class = ConversationParticipantSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return participants for conversations the user is part of"""
        return ConversationParticipant.objects.filter(
            conversation__participants=self.request.user
        )

    @action(detail=True, methods=['post'])
    def mute(self, request, pk=None):
        """Mute a conversation"""
        participant = self.get_object()
        participant.status = 'muted'
        participant.save()
        return Response({'status': 'conversation muted'})

    @action(detail=True, methods=['post'])
    def unmute(self, request, pk=None):
        """Unmute a conversation"""
        participant = self.get_object()
        participant.status = 'active'
        participant.save()
        return Response({'status': 'conversation unmuted'})


class SendMultiMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        sender = request.user
        recipient_ids = request.data.getlist('recipient_ids')
        content = request.data.get('content', '')
        file = request.FILES.get('file')
        results = []
        for rid in recipient_ids:
            try:
                recipient = User.objects.get(id=rid)
            except User.DoesNotExist:
                results.append(
                    {'recipient_id': rid, 'status': 'user_not_found'})
                continue
            # Find or create direct conversation
            conversation = Conversation.objects.filter(
                conversation_type='direct',
                participants=sender
            ).filter(participants=recipient).first()
            if not conversation:
                conversation = Conversation.objects.create(
                    conversation_type='direct',
                    name='',
                    created_by=sender
                )
                conversation.participants.add(sender, recipient)
            # Create message
            msg_data = {'conversation': conversation.id,
                        'message_type': 'text', 'content': content}
            if file:
                msg_data['message_type'] = 'file'
            message = Message.objects.create(
                conversation=conversation,
                sender=sender,
                message_type=msg_data['message_type'],
                content=content
            )
            if file:
                MessageAttachment.objects.create(
                    message=message,
                    file=file,
                    file_name=file.name,
                    file_size=file.size,
                    file_type=file.content_type,
                    mime_type=file.content_type
                )
            results.append({'recipient_id': rid, 'status': 'sent',
                           'conversation_id': conversation.id, 'message_id': message.id})
        return Response({'results': results})
