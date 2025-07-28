from django.urls import path
from . import views

urlpatterns = [
    path('notifications/', views.notification_list, name='notification-list'),
    path('notifications/<int:pk>/', views.notification_detail,
         name='notification-detail'),
    path('notifications/<int:pk>/mark_as_read/',
         views.mark_as_read, name='mark-as-read'),
    path('notifications/mark_all_as_read/',
         views.mark_all_as_read, name='mark-all-as-read'),
    path('preferences/', views.preferences, name='notification-preferences'),
    path('preferences/update_preferences/',
         views.update_preferences, name='update-preferences'),
    path('notifications/stats/', views.notification_stats,
         name='notification-stats'),
]
