from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationViewSet, NotificationTypeViewSet, NotificationTemplateViewSet,
    UserNotificationPreferenceViewSet, AdminNotificationViewSet
)

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'types', NotificationTypeViewSet,
                basename='notification-type')
router.register(r'templates', NotificationTemplateViewSet,
                basename='notification-template')
router.register(r'preferences', UserNotificationPreferenceViewSet,
                basename='notification-preference')

# Admin router for managing all notifications
admin_router = DefaultRouter()
admin_router.register(r'admin/notifications',
                      AdminNotificationViewSet, basename='admin-notification')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(admin_router.urls)),
]
