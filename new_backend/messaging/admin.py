from django.contrib import admin
from .models import Conversation, Message, MessageReaction, UserBlock


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_group', 'created_at', 'updated_at')
    list_filter = ('is_group', 'created_at', 'updated_at')
    search_fields = ('title', 'participants__username')
    filter_horizontal = ('participants',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'conversation',
                    'message_type', 'is_read', 'created_at')
    list_filter = ('message_type', 'is_read', 'created_at')
    search_fields = ('sender__username', 'content', 'conversation__title')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(MessageReaction)
class MessageReactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'reaction_type', 'created_at')
    list_filter = ('reaction_type', 'created_at')
    search_fields = ('user__username', 'message__content')


@admin.register(UserBlock)
class UserBlockAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked_user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('blocker__username', 'blocked_user__username', 'reason')
