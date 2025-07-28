from django.dispatch import Signal
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import (
    Notification, NotificationType, NotificationTemplate,
    UserNotificationPreference, NotificationDelivery
)
from .services import NotificationService
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


@receiver(post_save, sender=User)
def create_user_notification_preferences(sender, instance, created, **kwargs):
    """Create notification preferences when a new user is created"""
    if created:
        UserNotificationPreference.objects.get_or_create(user=instance)


@receiver(post_save, sender=Notification)
def handle_notification_created(sender, instance, created, **kwargs):
    """Handle notification creation and trigger delivery"""
    if created:
        # Queue notification for delivery
        NotificationService.queue_notification(instance)
        # Send real-time notification
        channel_layer = get_channel_layer()
        group_name = f"notifications_{instance.recipient.id}"
        notification_data = {
            "id": instance.id,
            "subject": instance.subject,
            "message": instance.message,
            "created_at": str(instance.created_at),
            "is_read": instance.is_read,
            "conversation_id": getattr(instance.content_object, 'id', None),
        }
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "send_notification",
                "notification": notification_data,
            }
        )


@receiver(post_save, sender=Notification)
def handle_notification_status_change(sender, instance, **kwargs):
    """Handle notification status changes"""
    if instance.status == 'sent':
        # Create delivery records for each enabled method
        NotificationService.create_delivery_records(instance)
    elif instance.status == 'delivered':
        # Update delivery records
        NotificationService.update_delivery_status(instance)


# Custom signals for different notification types

# Signal for user-related notifications
user_notification_signal = Signal()

# Signal for system notifications
system_notification_signal = Signal()

# Signal for marketing notifications
marketing_notification_signal = Signal()


@receiver(user_notification_signal)
def handle_user_notification(sender, recipient, notification_type, subject, message, **kwargs):
    """Handle user-to-user notifications"""
    notification_service = NotificationService()
    # Only pass valid Notification fields
    valid_fields = {'priority', 'template',
                    'html_message', 'content_object', 'scheduled_for'}
    filtered_kwargs = {k: v for k, v in kwargs.items() if k in valid_fields}
    notification_service.create_user_notification(
        recipient=recipient,
        notification_type=notification_type,
        subject=subject,
        message=message,
        **filtered_kwargs
    )


@receiver(system_notification_signal)
def handle_system_notification(sender, recipients, notification_type, subject, message, **kwargs):
    """Handle system-wide notifications"""
    notification_service = NotificationService()
    notification_service.create_system_notification(
        recipients=recipients,
        notification_type=notification_type,
        subject=subject,
        message=message,
        **kwargs
    )


@receiver(marketing_notification_signal)
def handle_marketing_notification(sender, recipients, subject, message, **kwargs):
    """Handle marketing notifications"""
    notification_service = NotificationService()
    notification_service.create_marketing_notification(
        recipients=recipients,
        subject=subject,
        message=message,
        **kwargs
    )
