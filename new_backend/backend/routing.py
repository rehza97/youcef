"""
WebSocket routing configuration
"""
from django.urls import re_path
from notifications.consumers import NotificationConsumer
from messaging.consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<conversation_id>\w+)/$', ChatConsumer.as_asgi()),
]
