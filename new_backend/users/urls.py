from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.user_list, name='user-list'),
    path('users/<int:pk>/', views.user_detail, name='user-detail'),
    path('roles/', views.role_list, name='role-list'),
    path('roles/<int:pk>/', views.role_detail, name='role-detail'),
    path('permissions/', views.permission_list, name='permission-list'),
    path('assign-role/', views.assign_role, name='assign-role'),
    path('check-role/<str:role_name>/', views.check_role, name='check-role'),
    path('check-permission/<str:codename>/',
         views.check_permission, name='check-permission'),
    path('roles/<int:role_id>/update-permissions/',
         views.update_role_permissions, name='update-role-permissions'),
]
