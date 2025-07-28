from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConversationViewSet, MessageViewSet, MessageReactionViewSet,
    UserBlockViewSet, ConversationParticipantViewSet, SendMultiMessageView
)

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'reactions', MessageReactionViewSet, basename='reaction')
router.register(r'blocks', UserBlockViewSet, basename='block')
router.register(r'participants', ConversationParticipantViewSet,
                basename='participant')

urlpatterns = [
    path('send-multi/', SendMultiMessageView.as_view(), name='send-multi'),
    path('', include(router.urls)),
]
