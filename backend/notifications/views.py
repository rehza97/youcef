from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.utils import timezone
from .models import (
    Notification, NotificationType, NotificationTemplate,
    UserNotificationPreference, NotificationDelivery
)
from .serializers import (
    NotificationSerializer, NotificationListSerializer, NotificationTypeSerializer,
    NotificationTemplateSerializer, UserNotificationPreferenceSerializer,
    CreateNotificationSerializer, MarkNotificationReadSerializer,
    NotificationStatsSerializer, BulkNotificationSerializer
)
from .services import NotificationService


class NotificationTypeViewSet(viewsets.ModelViewSet):
    """API endpoint for notification types"""
    queryset = NotificationType.objects.all()
    serializer_class = NotificationTypeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NotificationType.objects.filter(is_active=True)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """API endpoint for notification templates"""
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NotificationTemplate.objects.filter(is_active=True)


class NotificationViewSet(viewsets.ModelViewSet):
    """API endpoint for notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return notifications for the current user"""
        return Notification.objects.filter(recipient=self.request.user)

    def get_serializer_class(self):
        if self.action == 'list':
            return NotificationListSerializer
        elif self.action == 'create':
            return CreateNotificationSerializer
        return NotificationSerializer

    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications for the current user"""
        notifications = self.get_queryset().filter(read_at__isnull=True)
        serializer = NotificationListSerializer(notifications, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics for the current user"""
        user = request.user
        queryset = self.get_queryset()

        stats = {
            'total_notifications': queryset.count(),
            'unread_notifications': queryset.filter(read_at__isnull=True).count(),
            'read_notifications': queryset.filter(read_at__isnull=False).count(),
            'pending_notifications': queryset.filter(status='pending').count(),
            'failed_notifications': queryset.filter(status='failed').count(),
        }

        serializer = NotificationStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read for the current user"""
        serializer = MarkNotificationReadSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user

            if serializer.validated_data.get('mark_all'):
                # Mark all notifications as read
                Notification.objects.filter(
                    recipient=user,
                    read_at__isnull=True
                ).update(read_at=timezone.now())
                return Response({'status': 'all notifications marked as read'})
            else:
                # Mark specific notifications as read
                notification_ids = serializer.validated_data.get(
                    'notification_ids', [])
                Notification.objects.filter(
                    recipient=user,
                    id__in=notification_ids
                ).update(read_at=timezone.now())
                return Response({'status': 'selected notifications marked as read'})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Create multiple notifications"""
        serializer = BulkNotificationSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            notification_service = NotificationService()

            notifications = []
            for recipient_id in data['recipients']:
                try:
                    recipient = User.objects.get(id=recipient_id)
                    notification = notification_service.create_notification(
                        recipient=recipient,
                        notification_type=data['notification_type'],
                        subject=data['subject'],
                        message=data['message'],
                        html_message=data.get('html_message', ''),
                        priority=data.get('priority', 'normal'),
                        scheduled_for=data.get('scheduled_for')
                    )
                    notifications.append(notification)
                except User.DoesNotExist:
                    continue

            return Response({
                'status': 'notifications created',
                'count': len(notifications)
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserNotificationPreferenceViewSet(viewsets.ModelViewSet):
    """API endpoint for user notification preferences"""
    serializer_class = UserNotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return preferences for the current user"""
        return UserNotificationPreference.objects.filter(user=self.request.user)

    def get_object(self):
        """Get or create preferences for the current user"""
        obj, created = UserNotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj

    @action(detail=False, methods=['post'])
    def update_preferences(self, request):
        """Update notification preferences"""
        try:
            preferences = self.get_object()
        except UserNotificationPreference.DoesNotExist:
            preferences = UserNotificationPreference.objects.create(
                user=request.user)

        serializer = self.get_serializer(
            preferences, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminNotificationViewSet(viewsets.ModelViewSet):
    """Admin API endpoint for managing all notifications"""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        queryset = Notification.objects.all()

        # Filter by recipient
        recipient = self.request.query_params.get('recipient', None)
        if recipient:
            queryset = queryset.filter(
                recipient__username__icontains=recipient)

        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by notification type
        notification_type = self.request.query_params.get(
            'notification_type', None)
        if notification_type:
            queryset = queryset.filter(
                notification_type__name=notification_type)

        # Filter by date range
        date_from = self.request.query_params.get('date_from', None)
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)

        date_to = self.request.query_params.get('date_to', None)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        return queryset

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get global notification statistics"""
        queryset = self.get_queryset()

        stats = {
            'total_notifications': queryset.count(),
            'unread_notifications': queryset.filter(read_at__isnull=True).count(),
            'read_notifications': queryset.filter(read_at__isnull=False).count(),
            'pending_notifications': queryset.filter(status='pending').count(),
            'sent_notifications': queryset.filter(status='sent').count(),
            'delivered_notifications': queryset.filter(status='delivered').count(),
            'failed_notifications': queryset.filter(status='failed').count(),
            'cancelled_notifications': queryset.filter(status='cancelled').count(),
        }

        # Add notification type breakdown
        type_stats = queryset.values('notification_type__name').annotate(
            count=Count('id')
        ).order_by('-count')
        stats['notification_types'] = list(type_stats)

        serializer = NotificationStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def retry_failed(self, request):
        """Retry failed notifications"""
        failed_notifications = Notification.objects.filter(
            status='failed'
        ).filter(
            retry_count__lt=models.F('max_retries')
        )

        retry_count = 0
        for notification in failed_notifications:
            if notification.can_retry():
                notification.increment_retry_count()
                notification.status = 'pending'
                notification.save()
                retry_count += 1

        return Response({
            'status': 'retry initiated',
            'retry_count': retry_count
        })

    @action(detail=False, methods=['post'])
    def cleanup_old(self, request):
        """Clean up old notifications"""
        days = request.data.get('days', 30)
        notification_service = NotificationService()
        deleted_count = notification_service.delete_old_notifications(days)

        return Response({
            'status': 'cleanup completed',
            'deleted_count': deleted_count
        })
