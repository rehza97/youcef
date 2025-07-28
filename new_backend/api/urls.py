from django.urls import path
from django.views.decorators.cache import cache_page
from . import views

urlpatterns = [
    # Health and info endpoints
    path('health/', cache_page(60)(views.health_check), name='health-check'),
    path('info/', cache_page(300)(views.api_info), name='api-info'),

    # Authentication endpoints with rate limiting
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('refresh-token/', views.refresh_token, name='refresh-token'),

    # Protected endpoint
    path('protected/', views.protected_view, name='protected'),

    # User profile endpoints
    path('profile/', views.user_profile, name='user-profile'),
    path('change-password/', views.change_password, name='change-password'),
]
