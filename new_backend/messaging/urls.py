from django.urls import path
from . import views

urlpatterns = [
    path('conversations/', views.conversation_list, name='conversation-list'),
    path('conversations/<int:pk>/', views.conversation_detail,
         name='conversation-detail'),
    path('conversations/<int:pk>/messages/',
         views.message_list, name='message-list'),
    path('conversations/<int:pk>/messages/<int:message_id>/',
         views.message_detail, name='message-detail'),
    path('messages/<int:message_id>/react/',
         views.add_reaction, name='add-reaction'),
    path('blocks/', views.block_user, name='block-user'),
    path('blocks/unblock/', views.unblock_user, name='unblock-user'),
    path('blocks/blocked_users/', views.blocked_users_list,
         name='blocked-users-list'),
    path('send-multi/', views.send_multi_message, name='send-multi-message'),
]
