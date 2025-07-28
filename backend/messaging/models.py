from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator
import os


def message_file_path(instance, filename):
    """Generate file path for message attachments"""
    return f'messages/{instance.conversation.id}/{instance.id}/{filename}'


class Conversation(models.Model):
    """Conversation between users"""
    CONVERSATION_TYPES = [
        ('direct', 'Direct Message'),
        ('group', 'Group Chat'),
        ('channel', 'Channel'),
    ]

    name = models.CharField(max_length=255, blank=True)
    conversation_type = models.CharField(
        max_length=20, choices=CONVERSATION_TYPES, default='direct')
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='created_conversations')
    participants = models.ManyToManyField(User, related_name='conversations')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conversations'
        ordering = ['-updated_at']

    def __str__(self):
        if self.conversation_type == 'direct':
            participants = list(self.participants.all())
            if len(participants) == 2:
                return f"Chat between {participants[0].username} and {participants[1].username}"
        return self.name or f"Conversation {self.id}"

    def get_other_participant(self, user):
        """Get the other participant in a direct conversation"""
        if self.conversation_type == 'direct':
            other_participants = self.participants.exclude(id=user.id)
            return other_participants.first()
        return None

    def add_participant(self, user):
        """Add a participant to the conversation"""
        self.participants.add(user)

    def remove_participant(self, user):
        """Remove a participant from the conversation"""
        self.participants.remove(user)

    def get_last_message(self):
        """Get the last message in the conversation"""
        return self.messages.order_by('-created_at').first()


class Message(models.Model):
    """Individual message in a conversation"""
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('file', 'File'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('system', 'System Message'),
    ]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_messages')
    message_type = models.CharField(
        max_length=20, choices=MESSAGE_TYPES, default='text')

    # Content
    content = models.TextField(blank=True)
    file = models.FileField(
        upload_to=message_file_path,
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=[
                                           'pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'mp4', 'avi', 'mp3', 'wav'])]
    )
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveIntegerField(default=0)

    # Metadata
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'messages'
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.username} in {self.conversation}"

    def save(self, *args, **kwargs):
        # Set file name and size if file is uploaded
        if self.file and not self.file_name:
            self.file_name = os.path.basename(self.file.name)
            self.file_size = self.file.size
        super().save(*args, **kwargs)

    def edit_message(self, new_content):
        """Edit the message content"""
        self.content = new_content
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save()

    def delete_message(self):
        """Soft delete the message"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def get_file_extension(self):
        """Get the file extension"""
        if self.file:
            return os.path.splitext(self.file.name)[1].lower()
        return None


class MessageReaction(models.Model):
    """Reactions to messages"""
    REACTION_TYPES = [
        ('like', '👍'),
        ('love', '❤️'),
        ('laugh', '😂'),
        ('wow', '😮'),
        ('sad', '😢'),
        ('angry', '😠'),
    ]

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='message_reactions')
    reaction_type = models.CharField(max_length=20, choices=REACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'message_reactions'
        unique_together = ['message', 'user', 'reaction_type']

    def __str__(self):
        return f"{self.user.username} reacted with {self.reaction_type} to message {self.message.id}"


class ConversationParticipant(models.Model):
    """Track participant status in conversations"""
    PARTICIPANT_STATUS = [
        ('active', 'Active'),
        ('muted', 'Muted'),
        ('left', 'Left'),
        ('blocked', 'Blocked'),
    ]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='participant_status')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='conversation_status')
    status = models.CharField(
        max_length=20, choices=PARTICIPANT_STATUS, default='active')
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(null=True, blank=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    unread_count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'conversation_participants'
        unique_together = ['conversation', 'user']

    def __str__(self):
        return f"{self.user.username} in {self.conversation}"

    def mark_as_read(self):
        """Mark conversation as read for this participant"""
        self.last_read_at = timezone.now()
        self.unread_count = 0
        self.save()

    def increment_unread_count(self):
        """Increment unread count"""
        self.unread_count += 1
        self.save()

    def leave_conversation(self):
        """Leave the conversation"""
        self.status = 'left'
        self.left_at = timezone.now()
        self.save()


class UserBlock(models.Model):
    """Block relationships between users"""
    blocker = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='blocked_users')
    blocked_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='blocked_by')
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_blocks'
        unique_together = ['blocker', 'blocked_user']

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked_user.username}"


class MessageAttachment(models.Model):
    """Additional attachments for messages"""
    ATTACHMENT_TYPES = [
        ('image', 'Image'),
        ('document', 'Document'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('other', 'Other'),
    ]

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to=message_file_path)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    file_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPES)
    mime_type = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'message_attachments'

    def __str__(self):
        return f"Attachment {self.file_name} for message {self.message.id}"

    def save(self, *args, **kwargs):
        if not self.file_name:
            self.file_name = os.path.basename(self.file.name)
        if not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)
