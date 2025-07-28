from django.dispatch import Signal
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from .models import (
    Conversation, Message, MessageReaction, ConversationParticipant,
    UserBlock, MessageAttachment
)
from notifications.signals import user_notification_signal


@receiver(post_save, sender=Conversation)
def handle_conversation_created(sender, instance, created, **kwargs):
    """Handle conversation creation"""
    if created:
        # Create participant status for all participants
        for participant in instance.participants.all():
            ConversationParticipant.objects.get_or_create(
                conversation=instance,
                user=participant
            )


@receiver(post_save, sender=Message)
def handle_message_created(sender, instance, created, **kwargs):
    """Handle new message creation"""
    if created and not instance.is_deleted:
        # Update conversation timestamp
        instance.conversation.updated_at = timezone.now()
        instance.conversation.save(update_fields=['updated_at'])

        # Increment unread count for other participants
        for participant in instance.conversation.participants.exclude(id=instance.sender.id):
            try:
                participant_status = ConversationParticipant.objects.get(
                    conversation=instance.conversation,
                    user=participant
                )
                participant_status.increment_unread_count()
            except ConversationParticipant.DoesNotExist:
                # Create participant status if it doesn't exist
                ConversationParticipant.objects.create(
                    conversation=instance.conversation,
                    user=participant,
                    unread_count=1
                )

        # Send notification to other participants
        for participant in instance.conversation.participants.exclude(id=instance.sender.id):
            # Check if user is blocked
            if not UserBlock.objects.filter(
                blocker=participant,
                blocked_user=instance.sender
            ).exists():
                # Send notification
                user_notification_signal.send(
                    sender=Message,
                    recipient=participant,
                    notification_type='new_message',
                    subject=f'Nouveau message de {instance.sender.username}',
                    message=f'{instance.sender.username} vous a envoyé un message dans {instance.conversation}',
                    conversation_id=instance.conversation.id,
                    message_id=instance.id
                )


@receiver(post_save, sender=Message)
def handle_message_updated(sender, instance, **kwargs):
    """Handle message updates (edits)"""
    if instance.is_edited:
        # Could send notification about message edit
        pass


@receiver(post_save, sender=MessageReaction)
def handle_reaction_created(sender, instance, created, **kwargs):
    """Handle new message reactions"""
    if created:
        # Send notification to message sender about reaction
        if instance.user != instance.message.sender:
            user_notification_signal.send(
                sender=MessageReaction,
                recipient=instance.message.sender,
                notification_type='message_reaction',
                subject=f'{instance.user.username} a réagi à votre message',
                message=f'{instance.user.username} a réagi avec {instance.get_reaction_type_display()} à votre message',
                conversation_id=instance.message.conversation.id,
                message_id=instance.message.id
            )


@receiver(post_save, sender=ConversationParticipant)
def handle_participant_status_change(sender, instance, **kwargs):
    """Handle participant status changes"""
    if instance.status == 'left':
        # Send notification to other participants
        for participant in instance.conversation.participants.exclude(id=instance.user.id):
            user_notification_signal.send(
                sender=ConversationParticipant,
                recipient=participant,
                notification_type='participant_left',
                subject=f'{instance.user.username} a quitté la conversation',
                message=f'{instance.user.username} a quitté la conversation {instance.conversation}',
                conversation_id=instance.conversation.id
            )


@receiver(post_save, sender=UserBlock)
def handle_user_blocked(sender, instance, created, **kwargs):
    """Handle user blocking"""
    if created:
        # Send notification to blocked user
        user_notification_signal.send(
            sender=UserBlock,
            recipient=instance.blocked_user,
            notification_type='user_blocked',
            subject=f'{instance.blocker.username} vous a bloqué',
            message=f'{instance.blocker.username} vous a bloqué',
            blocker_id=instance.blocker.id
        )


@receiver(post_delete, sender=Message)
def handle_message_deleted(sender, instance, **kwargs):
    """Handle message deletion"""
    # Update conversation timestamp
    instance.conversation.updated_at = timezone.now()
    instance.conversation.save(update_fields=['updated_at'])


# Custom signals for messaging events

# Signal for when a user joins a conversation
user_joined_conversation_signal = Signal()

# Signal for when a user leaves a conversation
user_left_conversation_signal = Signal()

# Signal for when a conversation is created
conversation_created_signal = Signal()

# Signal for when a message is sent
message_sent_signal = Signal()

# Signal for when a message is edited
message_edited_signal = Signal()

# Signal for when a message is deleted
message_deleted_signal = Signal()


@receiver(user_joined_conversation_signal)
def handle_user_joined_conversation(sender, user, conversation, **kwargs):
    """Handle user joining a conversation"""
    # Send notification to other participants
    for participant in conversation.participants.exclude(id=user.id):
        user_notification_signal.send(
            sender=Conversation,
            recipient=participant,
            notification_type='user_joined',
            subject=f'{user.username} a rejoint la conversation',
            message=f'{user.username} a rejoint la conversation {conversation}',
            conversation_id=conversation.id,
            user_id=user.id
        )


@receiver(user_left_conversation_signal)
def handle_user_left_conversation(sender, user, conversation, **kwargs):
    """Handle user leaving a conversation"""
    # Send notification to other participants
    for participant in conversation.participants.exclude(id=user.id):
        user_notification_signal.send(
            sender=Conversation,
            recipient=participant,
            notification_type='user_left',
            subject=f'{user.username} a quitté la conversation',
            message=f'{user.username} a quitté la conversation {conversation}',
            conversation_id=conversation.id,
            user_id=user.id
        )


@receiver(conversation_created_signal)
def handle_conversation_created(sender, conversation, created_by, participants, **kwargs):
    """Handle conversation creation"""
    # Send notification to participants
    for participant in participants:
        if participant != created_by:
            user_notification_signal.send(
                sender=Conversation,
                recipient=participant,
                notification_type='conversation_invite',
                subject=f'{created_by.username} vous a invité à une conversation',
                message=f'{created_by.username} vous a invité à rejoindre la conversation {conversation}',
                conversation_id=conversation.id,
                created_by_id=created_by.id
            )


@receiver(message_sent_signal)
def handle_message_sent(sender, message, **kwargs):
    """Handle message sent event"""
    # This is already handled by the post_save signal above
    pass


@receiver(message_edited_signal)
def handle_message_edited(sender, message, old_content, **kwargs):
    """Handle message edited event"""
    # Send notification to other participants about message edit
    for participant in message.conversation.participants.exclude(id=message.sender.id):
        user_notification_signal.send(
            sender=Message,
            recipient=participant,
            notification_type='message_edited',
            subject=f'{message.sender.username} a modifié un message',
            message=f'{message.sender.username} a modifié un message dans {message.conversation}',
            conversation_id=message.conversation.id,
            message_id=message.id
        )


@receiver(message_deleted_signal)
def handle_message_deleted(sender, message, **kwargs):
    """Handle message deleted event"""
    # Send notification to other participants about message deletion
    for participant in message.conversation.participants.exclude(id=message.sender.id):
        user_notification_signal.send(
            sender=Message,
            recipient=participant,
            notification_type='message_deleted',
            subject=f'{message.sender.username} a supprimé un message',
            message=f'{message.sender.username} a supprimé un message dans {message.conversation}',
            conversation_id=message.conversation.id,
            message_id=message.id
        )
