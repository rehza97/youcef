from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ModelSerializer
from .models import Conversation, Message, MessageReaction, UserBlock
import logging

logger = logging.getLogger(__name__)

# Serializers


class ConversationSerializer(ModelSerializer):
    class Meta:
        model = Conversation
        fields = '__all__'


class MessageSerializer(ModelSerializer):
    class Meta:
        model = Message
        fields = '__all__'


class MessageReactionSerializer(ModelSerializer):
    class Meta:
        model = MessageReaction
        fields = '__all__'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_list(request):
    """Get user's conversations"""
    try:
        conversations = Conversation.objects.filter(participants=request.user)
        serializer = ConversationSerializer(conversations, many=True)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching conversations: {str(e)}")
        return Response({'error': 'Error fetching conversations'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_detail(request, pk):
    """Get specific conversation"""
    try:
        conversation = Conversation.objects.get(
            pk=pk, participants=request.user)
        serializer = ConversationSerializer(conversation)
        return Response(serializer.data)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching conversation {pk}: {str(e)}")
        return Response({'error': 'Error fetching conversation'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def message_list(request, pk):
    """Get messages for a conversation"""
    try:
        conversation = Conversation.objects.get(
            pk=pk, participants=request.user)
        messages = Message.objects.filter(conversation=conversation)
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching messages: {str(e)}")
        return Response({'error': 'Error fetching messages'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def message_list(request, pk):
    """Send a message to a conversation"""
    try:
        conversation = Conversation.objects.get(
            pk=pk, participants=request.user)
        content = request.data.get('content', '').strip()
        message_type = request.data.get('message_type', 'text')

        if not content:
            return Response({'error': 'Message content is required'}, status=status.HTTP_400_BAD_REQUEST)

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content,
            message_type=message_type
        )

        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return Response({'error': 'Error sending message'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def message_detail(request, pk, message_id):
    """Get, update, or delete a specific message"""
    try:
        conversation = Conversation.objects.get(
            pk=pk, participants=request.user)
        message = Message.objects.get(pk=message_id, conversation=conversation)

        if request.method == 'GET':
            serializer = MessageSerializer(message)
            return Response(serializer.data)

        elif request.method == 'PUT':
            if message.sender != request.user:
                return Response({'error': 'You can only edit your own messages'}, status=status.HTTP_403_FORBIDDEN)

            content = request.data.get('content', '').strip()
            if not content:
                return Response({'error': 'Message content is required'}, status=status.HTTP_400_BAD_REQUEST)

            message.content = content
            message.save()
            serializer = MessageSerializer(message)
            return Response(serializer.data)

        elif request.method == 'DELETE':
            if message.sender != request.user:
                return Response({'error': 'You can only delete your own messages'}, status=status.HTTP_403_FORBIDDEN)

            message.delete()
            return Response({'message': 'Message deleted successfully'})

    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
    except Message.DoesNotExist:
        return Response({'error': 'Message not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error with message {message_id}: {str(e)}")
        return Response({'error': 'Error processing message'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_reaction(request, message_id):
    """Add a reaction to a message"""
    try:
        message = Message.objects.get(pk=message_id)
        reaction_type = request.data.get('reaction_type')

        if not reaction_type:
            return Response({'error': 'Reaction type is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if user is blocked
        if UserBlock.objects.filter(blocker=message.sender, blocked_user=request.user).exists():
            return Response({'error': 'Cannot react to message from blocked user'}, status=status.HTTP_403_FORBIDDEN)

        reaction, created = MessageReaction.objects.get_or_create(
            message=message,
            user=request.user,
            reaction_type=reaction_type
        )

        serializer = MessageReactionSerializer(reaction)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    except Message.DoesNotExist:
        return Response({'error': 'Message not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error adding reaction: {str(e)}")
        return Response({'error': 'Error adding reaction'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def block_user(request):
    """Block a user"""
    try:
        blocked_user_id = request.data.get('blocked_user_id')
        reason = request.data.get('reason', '').strip()

        if not blocked_user_id:
            return Response({'error': 'Blocked user ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        blocked_user = User.objects.get(pk=blocked_user_id)

        if blocked_user == request.user:
            return Response({'error': 'Cannot block yourself'}, status=status.HTTP_400_BAD_REQUEST)

        block, created = UserBlock.objects.get_or_create(
            blocker=request.user,
            blocked_user=blocked_user,
            defaults={'reason': reason}
        )

        return Response({
            'message': f'User {blocked_user.username} blocked successfully'
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error blocking user: {str(e)}")
        return Response({'error': 'Error blocking user'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unblock_user(request):
    """Unblock a user"""
    try:
        blocked_user_id = request.data.get('blocked_user_id')

        if not blocked_user_id:
            return Response({'error': 'Blocked user ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        blocked_user = User.objects.get(pk=blocked_user_id)

        try:
            block = UserBlock.objects.get(
                blocker=request.user, blocked_user=blocked_user)
            block.delete()
            return Response({'message': f'User {blocked_user.username} unblocked successfully'})
        except UserBlock.DoesNotExist:
            return Response({'error': 'User is not blocked'}, status=status.HTTP_404_NOT_FOUND)

    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error unblocking user: {str(e)}")
        return Response({'error': 'Error unblocking user'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def blocked_users_list(request):
    """Get list of users blocked by current user"""
    try:
        blocked_users = UserBlock.objects.filter(blocker=request.user)
        data = []
        for block in blocked_users:
            data.append({
                'id': block.blocked_user.id,
                'username': block.blocked_user.username,
                'reason': block.reason,
                'blocked_at': block.created_at.isoformat()
            })
        return Response(data)
    except Exception as e:
        logger.error(f"Error fetching blocked users: {str(e)}")
        return Response({'error': 'Error fetching blocked users'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_multi_message(request):
    """Send a message to multiple conversations"""
    try:
        conversation_ids = request.data.get('conversation_ids', [])
        content = request.data.get('content', '').strip()
        message_type = request.data.get('message_type', 'text')

        if not content:
            return Response({'error': 'Message content is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not conversation_ids:
            return Response({'error': 'Conversation IDs are required'}, status=status.HTTP_400_BAD_REQUEST)

        messages = []
        for conv_id in conversation_ids:
            try:
                conversation = Conversation.objects.get(
                    pk=conv_id, participants=request.user)
                message = Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    content=content,
                    message_type=message_type
                )
                messages.append(MessageSerializer(message).data)
            except Conversation.DoesNotExist:
                continue

        return Response({
            'message': f'Message sent to {len(messages)} conversations',
            'messages': messages
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error sending multi message: {str(e)}")
        return Response({'error': 'Error sending messages'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
