from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import ModelSerializer
from .models import Role, UserProfile
import logging

logger = logging.getLogger(__name__)

# Serializers


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name',
                  'last_name', 'is_active', 'date_joined', 'last_login']


class RoleSerializer(ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'


class PermissionSerializer(ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']

# User management views


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def user_list(request):
    """Get list of all users"""
    try:
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        return Response({'error': 'Error fetching users'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_detail(request, pk):
    """Get specific user details"""
    try:
        user = User.objects.get(pk=pk)
        serializer = UserSerializer(user)
        return Response(serializer.data)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching user {pk}: {str(e)}")
        return Response({'error': 'Error fetching user'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Role management views


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def role_list(request):
    """Get list of all roles"""
    try:
        roles = Role.objects.all()
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching roles: {str(e)}")
        return Response({'error': 'Error fetching roles'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def role_detail(request, pk):
    """Get specific role details"""
    try:
        role = Role.objects.get(pk=pk)
        serializer = RoleSerializer(role)
        return Response(serializer.data)
    except Role.DoesNotExist:
        return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching role {pk}: {str(e)}")
        return Response({'error': 'Error fetching role'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Permission management views


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def permission_list(request):
    """Get list of all permissions"""
    try:
        permissions = Permission.objects.all()
        serializer = PermissionSerializer(permissions, many=True)
        return Response(serializer.data)
    except Exception as e:
        logger.error(f"Error fetching permissions: {str(e)}")
        return Response({'error': 'Error fetching permissions'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def assign_role(request):
    """Assign a role to a user"""
    try:
        user_id = request.data.get('user_id')
        role_id = request.data.get('role_id')

        if not user_id or not role_id:
            return Response({
                'error': 'User ID and Role ID are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(pk=user_id)
        role = Role.objects.get(pk=role_id)

        # Create or update user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.role = role
        profile.save()

        logger.info(f"Role '{role.name}' assigned to user '{user.username}'")

        return Response({
            'message': f'Role "{role.name}" assigned to user "{user.username}" successfully'
        }, status=status.HTTP_200_OK)

    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
    except Role.DoesNotExist:
        return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error assigning role: {str(e)}")
        return Response({'error': 'Error assigning role'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_role(request, role_name):
    """Check if current user has a specific role"""
    try:
        user = request.user
        has_role = False

        try:
            profile = user.profile
            if profile.role and profile.role.name == role_name:
                has_role = True
        except UserProfile.DoesNotExist:
            pass

        return Response({
            'user_id': user.id,
            'username': user.username,
            'role_name': role_name,
            'has_role': has_role
        })

    except Exception as e:
        logger.error(f"Error checking role: {str(e)}")
        return Response({'error': 'Error checking role'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_permission(request, codename):
    """Check if current user has a specific permission"""
    try:
        user = request.user
        has_permission = user.has_perm(codename)

        return Response({
            'user_id': user.id,
            'username': user.username,
            'permission_codename': codename,
            'has_permission': has_permission
        })

    except Exception as e:
        logger.error(f"Error checking permission: {str(e)}")
        return Response({'error': 'Error checking permission'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsAdminUser])
def update_role_permissions(request, role_id):
    """Update permissions for a specific role"""
    try:
        role = Role.objects.get(pk=role_id)
        permissions = request.data.get('permissions', [])

        if not isinstance(permissions, list):
            return Response({
                'error': 'Permissions must be a list'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Clear existing permissions
        role.permissions.clear()

        # Add new permissions
        for perm_id in permissions:
            try:
                permission = Permission.objects.get(pk=perm_id)
                role.permissions.add(permission)
            except Permission.DoesNotExist:
                continue

        logger.info(f"Permissions updated for role '{role.name}'")

        return Response({
            'message': f'Permissions updated for role "{role.name}" successfully'
        }, status=status.HTTP_200_OK)

    except Role.DoesNotExist:
        return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error updating role permissions: {str(e)}")
        return Response({'error': 'Error updating role permissions'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
