from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Notification, NotificationType, NotificationTemplate,
    UserNotificationPreference, NotificationDelivery
)


class NotificationTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationType
        fields = ['id', 'name', 'description',
                  'is_active', 'created_at', 'updated_at']


class NotificationTemplateSerializer(serializers.ModelSerializer):
    notification_type = NotificationTypeSerializer(read_only=True)
    notification_type_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'notification_type', 'notification_type_id',
            'subject', 'message_template', 'html_template', 'is_active',
            'created_at', 'updated_at'
        ]


class NotificationDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationDelivery
        fields = [
            'id', 'delivery_method', 'recipient_address', 'sent_at',
            'delivered_at', 'status', 'error_message', 'provider',
            'provider_message_id', 'created_at', 'updated_at'
        ]


class NotificationSerializer(serializers.ModelSerializer):
    notification_type = NotificationTypeSerializer(read_only=True)
    deliveries = NotificationDeliverySerializer(many=True, read_only=True)
    recipient_username = serializers.CharField(
        source='recipient.username', read_only=True)
    content_type_name = serializers.CharField(
        source='content_type.model', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_username', 'notification_type',
            'subject', 'message', 'html_message', 'priority', 'status',
            'sent_at', 'delivered_at', 'read_at', 'error_message',
            'retry_count', 'max_retries', 'created_at', 'updated_at',
            'scheduled_for', 'deliveries', 'content_type_name', 'object_id'
        ]
        read_only_fields = [
            'id', 'sent_at', 'delivered_at', 'read_at', 'error_message',
            'retry_count', 'created_at', 'updated_at', 'deliveries'
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    notification_type = NotificationTypeSerializer(read_only=True)
    recipient_username = serializers.CharField(
        source='recipient.username', read_only=True)
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient_username', 'notification_type', 'subject',
            'message', 'priority', 'status', 'created_at', 'is_read'
        ]

    def get_is_read(self, obj):
        return obj.read_at is not None


class UserNotificationPreferenceSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(
        source='user.username', read_only=True)

    class Meta:
        model = UserNotificationPreference
        fields = [
            'id', 'user', 'user_username', 'email_enabled', 'email_frequency',
            'sms_enabled', 'sms_number', 'push_enabled', 'in_app_enabled',
            'system_notifications', 'user_notifications', 'marketing_notifications',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CreateNotificationSerializer(serializers.ModelSerializer):
    recipient_id = serializers.IntegerField(write_only=True)
    notification_type_name = serializers.CharField(write_only=True)

    class Meta:
        model = Notification
        fields = [
            'recipient_id', 'notification_type_name', 'subject', 'message',
            'html_message', 'priority', 'scheduled_for'
        ]

    def create(self, validated_data):
        recipient_id = validated_data.pop('recipient_id')
        notification_type_name = validated_data.pop('notification_type_name')

        try:
            recipient = User.objects.get(id=recipient_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("Recipient not found")

        # Get or create notification type
        notification_type, created = NotificationType.objects.get_or_create(
            name=notification_type_name,
            defaults={
                'description': f'Notifications of type {notification_type_name}'}
        )

        return Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            **validated_data
        )


class MarkNotificationReadSerializer(serializers.Serializer):
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )
    mark_all = serializers.BooleanField(default=False)


class NotificationStatsSerializer(serializers.Serializer):
    total_notifications = serializers.IntegerField()
    unread_notifications = serializers.IntegerField()
    read_notifications = serializers.IntegerField()
    pending_notifications = serializers.IntegerField()
    failed_notifications = serializers.IntegerField()


class BulkNotificationSerializer(serializers.Serializer):
    recipients = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of user IDs to send notifications to"
    )
    notification_type = serializers.CharField()
    subject = serializers.CharField()
    message = serializers.CharField()
    html_message = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(
        choices=Notification.PRIORITY_CHOICES,
        default='normal'
    )
    scheduled_for = serializers.DateTimeField(required=False, allow_null=True)
