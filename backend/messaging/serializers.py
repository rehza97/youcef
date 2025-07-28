from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Conversation, Message, MessageReaction, ConversationParticipant,
    UserBlock, MessageAttachment
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class MessageReactionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    reaction_display = serializers.CharField(
        source='get_reaction_type_display', read_only=True)

    class Meta:
        model = MessageReaction
        fields = ['id', 'user', 'reaction_type',
                  'reaction_display', 'created_at']


class MessageAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttachment
        fields = ['id', 'file', 'file_name', 'file_size',
                  'file_type', 'mime_type', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    reactions = MessageReactionSerializer(many=True, read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    sender_username = serializers.CharField(
        source='sender.username', read_only=True)
    message_type_display = serializers.CharField(
        source='get_message_type_display', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_username', 'message_type',
            'message_type_display', 'content', 'file', 'file_name', 'file_size',
            'is_edited', 'edited_at', 'is_deleted', 'deleted_at', 'created_at',
            'updated_at', 'reactions', 'attachments'
        ]
        read_only_fields = ['id', 'sender', 'is_edited', 'edited_at',
                            'is_deleted', 'deleted_at', 'created_at', 'updated_at']


class ConversationParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    status_display = serializers.CharField(
        source='get_status_display', read_only=True)

    class Meta:
        model = ConversationParticipant
        fields = [
            'id', 'user', 'status', 'status_display', 'joined_at', 'left_at',
            'last_read_at', 'unread_count'
        ]


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = MessageSerializer(read_only=True)
    conversation_type_display = serializers.CharField(
        source='get_conversation_type_display', read_only=True)
    participant_count = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'name', 'conversation_type', 'conversation_type_display',
            'created_by', 'participants', 'is_active', 'created_at', 'updated_at',
            'last_message', 'participant_count', 'unread_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_participant_count(self, obj):
        return obj.participants.count()

    def get_unread_count(self, obj):
        user = self.context['request'].user
        try:
            participant = ConversationParticipant.objects.get(
                conversation=obj,
                user=user
            )
            return participant.unread_count
        except ConversationParticipant.DoesNotExist:
            return 0


class ConversationListSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = MessageSerializer(read_only=True)
    conversation_type_display = serializers.CharField(
        source='get_conversation_type_display', read_only=True)
    other_participant = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'name', 'conversation_type', 'conversation_type_display',
            'participants', 'last_message', 'other_participant', 'unread_count',
            'created_at', 'updated_at'
        ]

    def get_other_participant(self, obj):
        user = self.context['request'].user
        if obj.conversation_type == 'direct':
            other_participant = obj.get_other_participant(user)
            if other_participant:
                return UserSerializer(other_participant).data
        return None

    def get_unread_count(self, obj):
        user = self.context['request'].user
        try:
            participant = ConversationParticipant.objects.get(
                conversation=obj,
                user=user
            )
            return participant.unread_count
        except ConversationParticipant.DoesNotExist:
            return 0


class CreateConversationSerializer(serializers.ModelSerializer):
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        help_text="List of user IDs to add to the conversation"
    )

    class Meta:
        model = Conversation
        fields = ['name', 'conversation_type', 'participant_ids']

    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids')
        conversation = Conversation.objects.create(**validated_data)

        # Add participants
        for user_id in participant_ids:
            try:
                user = User.objects.get(id=user_id)
                conversation.participants.add(user)
            except User.DoesNotExist:
                continue

        return conversation


class CreateMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['conversation', 'message_type', 'content', 'file']

    def create(self, validated_data):
        # Set the sender to the current user
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)


class EditMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['content']

    def update(self, instance, validated_data):
        old_content = instance.content
        instance.edit_message(validated_data['content'])
        return instance


class MessageReactionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageReaction
        fields = ['message', 'reaction_type']

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class UserBlockSerializer(serializers.ModelSerializer):
    blocked_user = UserSerializer(read_only=True)
    blocker = UserSerializer(read_only=True)

    class Meta:
        model = UserBlock
        fields = ['id', 'blocker', 'blocked_user', 'reason', 'created_at']
        read_only_fields = ['id', 'blocker', 'created_at']


class CreateUserBlockSerializer(serializers.ModelSerializer):
    blocked_user_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = UserBlock
        fields = ['blocked_user_id', 'reason']

    def create(self, validated_data):
        blocked_user_id = validated_data.pop('blocked_user_id')
        validated_data['blocker'] = self.context['request'].user
        validated_data['blocked_user_id'] = blocked_user_id
        return super().create(validated_data)


class ConversationStatsSerializer(serializers.Serializer):
    total_conversations = serializers.IntegerField()
    active_conversations = serializers.IntegerField()
    total_messages = serializers.IntegerField()
    unread_messages = serializers.IntegerField()
    conversations_by_type = serializers.DictField()


class MessageSearchSerializer(serializers.Serializer):
    query = serializers.CharField(help_text="Search query")
    conversation_id = serializers.IntegerField(
        required=False, help_text="Limit search to specific conversation")
    date_from = serializers.DateTimeField(
        required=False, help_text="Search from date")
    date_to = serializers.DateTimeField(
        required=False, help_text="Search to date")
