# Generated manually for notifications app

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationType',
            fields=[
                ('id', models.BigAutoField(auto_created=True,
                 primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'notification_types',
            },
        ),
        migrations.CreateModel(
            name='NotificationTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True,
                 primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('subject', models.CharField(blank=True, max_length=200)),
                ('message_template', models.TextField()),
                ('html_template', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('notification_type', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, to='notifications.notificationtype')),
            ],
            options={
                'db_table': 'notification_templates',
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True,
                 primary_key=True, serialize=False, verbose_name='ID')),
                ('subject', models.CharField(blank=True, max_length=200)),
                ('message', models.TextField()),
                ('html_message', models.TextField(blank=True)),
                ('priority', models.CharField(choices=[('low', 'Low'), ('normal', 'Normal'), (
                    'high', 'High'), ('urgent', 'Urgent')], default='normal', max_length=10)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('delivered', 'Delivered'), (
                    'failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending', max_length=10)),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('delivered_at', models.DateTimeField(blank=True, null=True)),
                ('read_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('retry_count', models.PositiveIntegerField(default=0)),
                ('max_retries', models.PositiveIntegerField(default=3)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('scheduled_for', models.DateTimeField(blank=True, null=True)),
                ('content_type', models.ForeignKey(blank=True, null=True,
                 on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('notification_type', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, to='notifications.notificationtype')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                 related_name='notifications', to='auth.user')),
                ('template', models.ForeignKey(blank=True, null=True,
                 on_delete=django.db.models.deletion.SET_NULL, to='notifications.notificationtemplate')),
            ],
            options={
                'db_table': 'notifications',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='NotificationDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True,
                 primary_key=True, serialize=False, verbose_name='ID')),
                ('delivery_method', models.CharField(choices=[('email', 'Email'), ('sms', 'SMS'), (
                    'push', 'Push Notification'), ('webhook', 'Webhook'), ('in_app', 'In-App')], max_length=20)),
                ('recipient_address', models.CharField(max_length=255)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('delivered_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('sent', 'Sent'), ('delivered', 'Delivered'), (
                    'failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending', max_length=10)),
                ('error_message', models.TextField(blank=True)),
                ('provider', models.CharField(blank=True, max_length=50)),
                ('provider_message_id', models.CharField(
                    blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('notification', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                 related_name='deliveries', to='notifications.notification')),
            ],
            options={
                'db_table': 'notification_deliveries',
                'verbose_name_plural': 'Notification deliveries',
            },
        ),
        migrations.CreateModel(
            name='UserNotificationPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True,
                 primary_key=True, serialize=False, verbose_name='ID')),
                ('email_enabled', models.BooleanField(default=True)),
                ('email_frequency', models.CharField(choices=[('immediate', 'Immediate'), ('hourly', 'Hourly'), (
                    'daily', 'Daily'), ('weekly', 'Weekly')], default='immediate', max_length=20)),
                ('sms_enabled', models.BooleanField(default=False)),
                ('sms_number', models.CharField(blank=True, max_length=20)),
                ('push_enabled', models.BooleanField(default=True)),
                ('in_app_enabled', models.BooleanField(default=True)),
                ('system_notifications', models.BooleanField(default=True)),
                ('user_notifications', models.BooleanField(default=True)),
                ('marketing_notifications', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,
                 related_name='notification_preferences', to='auth.user')),
            ],
            options={
                'db_table': 'user_notification_preferences',
            },
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(
                fields=['recipient', 'status'], name='notifications_recipie_8b8c8c_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(fields=['created_at'],
                               name='notifications_created_8b8c8c_idx'),
        ),
        migrations.AddIndex(
            model_name='notification',
            index=models.Index(
                fields=['scheduled_for'], name='notifications_schedul_8b8c8c_idx'),
        ),
        migrations.AddIndex(
            model_name='notificationdelivery',
            index=models.Index(fields=[
                               'notification', 'delivery_method'], name='notification__notific_8b8c8c_idx'),
        ),
        migrations.AddIndex(
            model_name='usernotificationpreference',
            index=models.Index(
                fields=['user'], name='user_notific_user_id_8b8c8c_idx'),
        ),
    ]
