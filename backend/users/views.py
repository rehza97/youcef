from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import Role, UserRole, Permission, Setting
from .serializers import UserSerializer, RoleSerializer, UserRoleSerializer, PermissionSerializer, SettingSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser

# Create your views here.


class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]


class RoleListView(generics.ListAPIView):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]


class PermissionListCreateView(generics.ListCreateAPIView):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]


class AssignRoleView(generics.CreateAPIView):
    serializer_class = UserRoleSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id')
        role_id = request.data.get('role_id')
        try:
            user = User.objects.get(id=user_id)
            role = Role.objects.get(id=role_id)
            user_role, created = UserRole.objects.get_or_create(
                user=user, role=role)
            serializer = UserRoleSerializer(user_role)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        except Role.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_role_permissions(request, role_id):
    """
    Update permissions for a role. Expects a list of permission IDs in 'permissions'.
    """
    try:
        role = Role.objects.get(id=role_id)
        perm_ids = request.data.get('permissions', [])
        perms = Permission.objects.filter(id__in=perm_ids)
        role.permissions.set(perms)
        role.save()
        return Response({'message': 'Permissions updated successfully.'})
    except Role.DoesNotExist:
        return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_user_role(request, role_name):
    has_role = request.user.user_roles.filter(role__name=role_name).exists()
    return Response({'has_role': has_role, 'role': role_name})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_user_permission(request, codename):
    # Check if user has a role with the given permission codename
    has_permission = request.user.user_roles.filter(
        role__permissions__codename=codename).exists()
    return Response({'has_permission': has_permission, 'permission': codename})


class SettingListView(generics.ListAPIView):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [IsAdminUser]


class SettingDetailView(generics.RetrieveUpdateAPIView):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [IsAdminUser]
    lookup_field = 'key'
