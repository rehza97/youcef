import logging
from typing import List, Optional, Dict, Any
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from .models import (
    Notification, NotificationType, NotificationTemplate,
    UserNotificationPreference, NotificationDelivery
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service class for handling notification operations"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def create_notification(
        self,
        recipient: User,
        notification_type: str,
        subject: str,
        message: str,
        html_message: str = "",
        priority: str = "normal",
        template: Optional[NotificationTemplate] = None,
        content_object=None,
        scheduled_for: Optional[timezone.datetime] = None,
        **kwargs
    ) -> Notification:
        """Create a new notification"""
        try:
            # Get or create notification type
            notification_type_obj, created = NotificationType.objects.get_or_create(
                name=notification_type,
                defaults={
                    'description': f'Notifications of type {notification_type}'}
            )

            # Create notification
            notification = Notification.objects.create(
                recipient=recipient,
                notification_type=notification_type_obj,
                template=template,
                subject=subject,
                message=message,
                html_message=html_message,
                priority=priority,
                content_object=content_object,
                scheduled_for=scheduled_for,
                **kwargs
            )

            self.logger.info(
                f"Created notification {notification.id} for user {recipient.username}")
            return notification

        except Exception as e:
            self.logger.error(f"Error creating notification: {e}")
            raise

    def create_user_notification(
        self,
        recipient: User,
        notification_type: str,
        subject: str,
        message: str,
        **kwargs
    ) -> Notification:
        """Create a user-to-user notification"""
        return self.create_notification(
            recipient=recipient,
            notification_type=notification_type,
            subject=subject,
            message=message,
            priority="normal",
            **kwargs
        )

    def create_system_notification(
        self,
        recipients: List[User],
        notification_type: str,
        subject: str,
        message: str,
        **kwargs
    ) -> List[Notification]:
        """Create system notifications for multiple users"""
        notifications = []
        for recipient in recipients:
            notification = self.create_notification(
                recipient=recipient,
                notification_type=notification_type,
                subject=subject,
                message=message,
                priority="normal",
                **kwargs
            )
            notifications.append(notification)
        return notifications

    def create_marketing_notification(
        self,
        recipients: List[User],
        subject: str,
        message: str,
        **kwargs
    ) -> List[Notification]:
        """Create marketing notifications for multiple users"""
        notifications = []
        for recipient in recipients:
            # Check user preferences for marketing notifications
            try:
                preferences = recipient.notification_preferences
                if not preferences.marketing_notifications:
                    continue
            except UserNotificationPreference.DoesNotExist:
                # Create preferences if they don't exist
                preferences = UserNotificationPreference.objects.create(
                    user=recipient)
                if not preferences.marketing_notifications:
                    continue

            notification = self.create_notification(
                recipient=recipient,
                notification_type="marketing",
                subject=subject,
                message=message,
                priority="low",
                **kwargs
            )
            notifications.append(notification)
        return notifications

    @staticmethod
    def queue_notification(notification: Notification):
        """Queue a notification for delivery"""
        try:
            # For now, we'll use a simple approach
            # In production, you'd use Celery or similar
            if notification.scheduled_for and notification.scheduled_for > timezone.now():
                # Schedule for later
                NotificationService.schedule_notification(notification)
            else:
                # Send immediately
                NotificationService.send_notification(notification)
        except Exception as e:
            logger.error(f"Error queuing notification {notification.id}: {e}")
            notification.mark_as_failed(str(e))

    @staticmethod
    def send_notification(notification: Notification):
        """Send a notification through all enabled delivery methods"""
        try:
            # Get user preferences
            try:
                preferences = notification.recipient.notification_preferences
            except UserNotificationPreference.DoesNotExist:
                preferences = UserNotificationPreference.objects.create(
                    user=notification.recipient)

            # Send via email if enabled
            if preferences.email_enabled and notification.recipient.email:
                NotificationService.send_email_notification(notification)

            # Send in-app notification
            if preferences.in_app_enabled:
                NotificationService.send_in_app_notification(notification)

            # Mark as sent
            notification.mark_as_sent()

        except Exception as e:
            logger.error(f"Error sending notification {notification.id}: {e}")
            notification.mark_as_failed(str(e))

    @staticmethod
    def send_email_notification(notification: Notification):
        """Send notification via email"""
        try:
            # Create delivery record
            delivery = NotificationDelivery.objects.create(
                notification=notification,
                delivery_method='email',
                recipient_address=notification.recipient.email,
                provider='smtp'
            )

            # Send email
            send_mail(
                subject=notification.subject,
                message=notification.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[notification.recipient.email],
                html_message=notification.html_message,
                fail_silently=False,
            )

            # Update delivery status
            delivery.status = 'delivered'
            delivery.delivered_at = timezone.now()
            delivery.save()

            logger.info(
                f"Email notification {notification.id} sent to {notification.recipient.email}")

        except Exception as e:
            logger.error(
                f"Error sending email notification {notification.id}: {e}")
            delivery.status = 'failed'
            delivery.error_message = str(e)
            delivery.save()

    @staticmethod
    def send_in_app_notification(notification: Notification):
        """Send in-app notification"""
        try:
            # Create delivery record
            delivery = NotificationDelivery.objects.create(
                notification=notification,
                delivery_method='in_app',
                recipient_address=notification.recipient.username,
                provider='internal'
            )

            # For in-app notifications, we just mark as delivered
            # The frontend will fetch these via API
            delivery.status = 'delivered'
            delivery.delivered_at = timezone.now()
            delivery.save()

            logger.info(
                f"In-app notification {notification.id} created for {notification.recipient.username}")

        except Exception as e:
            logger.error(
                f"Error creating in-app notification {notification.id}: {e}")
            delivery.status = 'failed'
            delivery.error_message = str(e)
            delivery.save()

    @staticmethod
    def schedule_notification(notification: Notification):
        """Schedule a notification for later delivery"""
        # In production, you'd use Celery or similar for scheduling
        logger.info(
            f"Notification {notification.id} scheduled for {notification.scheduled_for}")

    @staticmethod
    def create_delivery_records(notification: Notification):
        """Create delivery records for a notification"""
        try:
            preferences = notification.recipient.notification_preferences

            # Create delivery records for enabled methods
            if preferences.email_enabled and notification.recipient.email:
                NotificationDelivery.objects.get_or_create(
                    notification=notification,
                    delivery_method='email',
                    defaults={
                        'recipient_address': notification.recipient.email,
                        'provider': 'smtp'
                    }
                )

            if preferences.in_app_enabled:
                NotificationDelivery.objects.get_or_create(
                    notification=notification,
                    delivery_method='in_app',
                    defaults={
                        'recipient_address': notification.recipient.username,
                        'provider': 'internal'
                    }
                )

        except Exception as e:
            logger.error(
                f"Error creating delivery records for notification {notification.id}: {e}")

    @staticmethod
    def update_delivery_status(notification: Notification):
        """Update delivery status for a notification"""
        try:
            for delivery in notification.deliveries.all():
                if delivery.status == 'pending':
                    delivery.status = 'delivered'
                    delivery.delivered_at = timezone.now()
                    delivery.save()

        except Exception as e:
            logger.error(
                f"Error updating delivery status for notification {notification.id}: {e}")

    def get_user_notifications(
        self,
        user: User,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[Notification]:
        """Get notifications for a user"""
        queryset = Notification.objects.filter(recipient=user)

        if unread_only:
            queryset = queryset.filter(read_at__isnull=True)

        return queryset[:limit]

    def mark_notification_as_read(self, notification: Notification):
        """Mark a notification as read"""
        notification.mark_as_read()

    def mark_all_notifications_as_read(self, user: User):
        """Mark all notifications as read for a user"""
        Notification.objects.filter(
            recipient=user,
            read_at__isnull=True
        ).update(read_at=timezone.now())

    def get_notification_count(self, user: User, unread_only: bool = True) -> int:
        """Get notification count for a user"""
        queryset = Notification.objects.filter(recipient=user)

        if unread_only:
            queryset = queryset.filter(read_at__isnull=True)

        return queryset.count()

    def delete_old_notifications(self, days: int = 30):
        """Delete notifications older than specified days"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        deleted_count = Notification.objects.filter(
            created_at__lt=cutoff_date,
            read_at__isnull=False
        ).delete()[0]

        logger.info(f"Deleted {deleted_count} old notifications")
        return deleted_count
