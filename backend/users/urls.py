from django.urls import path
from .views import (
    UserListView, RoleListView, AssignRoleView, check_user_role,
    PermissionListCreateView, update_role_permissions, check_user_permission,
    SettingListView, SettingDetailView
)

urlpatterns = [
    path('users/', UserListView.as_view(), name='user-list'),
    path('roles/', RoleListView.as_view(), name='role-list'),
    path('permissions/', PermissionListCreateView.as_view(),
         name='permission-list-create'),
    path('assign-role/', AssignRoleView.as_view(), name='assign-role'),
    path('check-role/<str:role_name>/', check_user_role, name='check-user-role'),
    path('check-permission/<str:codename>/',
         check_user_permission, name='check-user-permission'),
    path('roles/<int:role_id>/update-permissions/',
         update_role_permissions, name='update-role-permissions'),
    path('settings/', SettingListView.as_view(), name='setting-list'),
    path('settings/<str:key>/', SettingDetailView.as_view(), name='setting-detail'),
]
