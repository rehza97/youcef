from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ModelSerializer
from .models import Notification, NotificationPreference
import logging

logger = logging.getLogger(__name__)

# Serializers


class NotificationSerializer(ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class NotificationPreferenceSerializer(ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = '__all__'


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    """Get user's notifications"""
    try:
        notifications = Notification.objects.filter(recipient=request.user)
        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}")
        return Response({'error': 'Error fetching notifications'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_detail(request, pk):
    """Get specific notification"""
    try:
        notification = Notification.objects.get(pk=pk, recipient=request.user)
        serializer = NotificationSerializer(notification)
        return Response(serializer.data)
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching notification {pk}: {str(e)}")
        return Response({'error': 'Error fetching notification'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_as_read(request, pk):
    """Mark notification as read"""
    try:
        notification = Notification.objects.get(pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save()

        return Response({'message': 'Notification marked as read'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return Response({'error': 'Error marking notification as read'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_as_read(request):
    """Mark all notifications as read"""
    try:
        Notification.objects.filter(
            recipient=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read'})
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {str(e)}")
        return Response({'error': 'Error marking notifications as read'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def preferences(request):
    """Get user's notification preferences"""
    try:
        preferences, created = NotificationPreference.objects.get_or_create(
            user=request.user)
        serializer = NotificationPreferenceSerializer(preferences)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching notification preferences: {str(e)}")
        return Response({'error': 'Error fetching preferences'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_preferences(request):
    """Update user's notification preferences"""
    try:
        preferences, created = NotificationPreference.objects.get_or_create(
            user=request.user)

        # Update preferences
        preferences.email_notifications = request.data.get(
            'email_notifications', preferences.email_notifications)
        preferences.push_notifications = request.data.get(
            'push_notifications', preferences.push_notifications)
        preferences.in_app_notifications = request.data.get(
            'in_app_notifications', preferences.in_app_notifications)
        preferences.save()

        serializer = NotificationPreferenceSerializer(preferences)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error updating notification preferences: {str(e)}")
        return Response({'error': 'Error updating preferences'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_stats(request):
    """Get notification statistics for user"""
    try:
        total_notifications = Notification.objects.filter(
            recipient=request.user).count()
        unread_notifications = Notification.objects.filter(
            recipient=request.user, is_read=False).count()
        read_notifications = total_notifications - unread_notifications

        # Count by type
        type_counts = {}
        for notification_type, _ in Notification.NOTIFICATION_TYPES:
            count = Notification.objects.filter(
                recipient=request.user,
                notification_type=notification_type
            ).count()
            type_counts[notification_type] = count

        return Response({
            'total_notifications': total_notifications,
            'unread_notifications': unread_notifications,
            'read_notifications': read_notifications,
            'type_counts': type_counts
        })
    except Exception as e:
        logger.error(f"Error fetching notification stats: {str(e)}")
        return Response({'error': 'Error fetching notification stats'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
