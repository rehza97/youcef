from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class NotificationType(models.Model):
    """Types of notifications (system, user, email, etc.)"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_types'

    def __str__(self):
        return self.name


class NotificationTemplate(models.Model):
    """Templates for different notification types"""
    name = models.CharField(max_length=100)
    notification_type = models.ForeignKey(
        NotificationType, on_delete=models.CASCADE)
    subject = models.CharField(max_length=200, blank=True)
    message_template = models.TextField()
    html_template = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_templates'

    def __str__(self):
        return f"{self.name} ({self.notification_type.name})"


class Notification(models.Model):
    """Main notification model"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.ForeignKey(
        NotificationType, on_delete=models.CASCADE)
    template = models.ForeignKey(
        NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True)

    # Content
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    html_message = models.TextField(blank=True)

    # Metadata
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending')

    # Related object (optional)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # Error tracking
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['scheduled_for']),
        ]

    def __str__(self):
        return f"Notification to {self.recipient.username}: {self.subject}"

    def mark_as_sent(self):
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])

    def mark_as_delivered(self):
        self.status = 'delivered'
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])

    def mark_as_read(self):
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])

    def mark_as_failed(self, error_message=""):
        self.status = 'failed'
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message'])

    def can_retry(self):
        return self.status == 'failed' and self.retry_count < self.max_retries

    def increment_retry_count(self):
        self.retry_count += 1
        self.save(update_fields=['retry_count'])


class NotificationDelivery(models.Model):
    """Track delivery attempts for notifications"""
    DELIVERY_METHOD_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Push Notification'),
        ('webhook', 'Webhook'),
        ('in_app', 'In-App'),
    ]

    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name='deliveries')
    delivery_method = models.CharField(
        max_length=20, choices=DELIVERY_METHOD_CHOICES)

    # Delivery details
    recipient_address = models.CharField(max_length=255)  # email, phone, etc.
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # Status
    status = models.CharField(
        max_length=10, choices=Notification.STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True)

    # Provider info
    # smtp, twilio, etc.
    provider = models.CharField(max_length=50, blank=True)
    provider_message_id = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_deliveries'
        verbose_name_plural = 'Notification deliveries'

    def __str__(self):
        return f"{self.delivery_method} delivery for {self.notification}"


class UserNotificationPreference(models.Model):
    """User preferences for notification delivery"""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='notification_preferences')

    # Email preferences
    email_enabled = models.BooleanField(default=True)
    email_frequency = models.CharField(max_length=20, default='immediate', choices=[
        ('immediate', 'Immediate'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ])

    # SMS preferences
    sms_enabled = models.BooleanField(default=False)
    sms_number = models.CharField(max_length=20, blank=True)

    # Push notification preferences
    push_enabled = models.BooleanField(default=True)

    # In-app notification preferences
    in_app_enabled = models.BooleanField(default=True)

    # Notification type preferences
    system_notifications = models.BooleanField(default=True)
    user_notifications = models.BooleanField(default=True)
    marketing_notifications = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_notification_preferences'

    def __str__(self):
        return f"Preferences for {self.user.username}"
