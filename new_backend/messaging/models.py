from django.db import models
from django.contrib.auth.models import User


class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_group = models.BooleanField(default=False)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.title:
            return self.title
        participant_names = [p.username for p in self.participants.all()]
        return f"Conversation between {', '.join(participant_names)}"


class Message(models.Model):
    MESSAGE_TYPES = (
        ('text', 'Text'),
        ('image', 'Image'),
        ('file', 'File'),
        ('audio', 'Audio'),
        ('video', 'Video'),
    )

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField()
    message_type = models.CharField(
        max_length=10, choices=MESSAGE_TYPES, default='text')
    file = models.FileField(upload_to='messages/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.username}: {self.content[:50]}"


class MessageReaction(models.Model):
    REACTION_TYPES = (
        ('like', 'Like'),
        ('love', 'Love'),
        ('laugh', 'Laugh'),
        ('wow', 'Wow'),
        ('sad', 'Sad'),
        ('angry', 'Angry'),
    )

    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='message_reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['message', 'user', 'reaction_type']

    def __str__(self):
        return f"{self.user.username} {self.reaction_type} on message {self.message.id}"


class UserBlock(models.Model):
    blocker = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='blocked_users')
    blocked_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='blocked_by')
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['blocker', 'blocked_user']

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked_user.username}"
