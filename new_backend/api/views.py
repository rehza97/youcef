from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
import logging
import re

logger = logging.getLogger(__name__)

# Custom throttle classes


class LoginRateThrottle(UserRateThrottle):
    scope = 'login'


class RegisterRateThrottle(AnonRateThrottle):
    scope = 'register'


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username):
    """Validate username format"""
    if not username or len(username) < 3 or len(username) > 30:
        return False
    pattern = r'^[a-zA-Z0-9_]+$'
    return re.match(pattern, username) is not None


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Simple health check endpoint
    """
    return Response({
        'status': 'healthy',
        'message': 'Django backend is running successfully!',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0'
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_info(request):
    """
    API information endpoint
    """
    return Response({
        'name': 'Youcef Backend API',
        'version': '1.0.0',
        'framework': 'Django REST Framework',
        'endpoints': [
            '/api/health/',
            '/api/info/',
            '/api/register/',
            '/api/login/',
            '/api/logout/',
            '/api/refresh-token/',
            '/api/protected/',
            '/api/profile/',
            '/api/change-password/',
        ]
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([RegisterRateThrottle])
def register(request):
    """
    User registration with comprehensive validation
    """
    try:
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        email = request.data.get('email', '').strip()

        # Input validation
        if not username or not password:
            return Response({
                'error': 'Username and password are required.',
                'code': 'MISSING_FIELDS'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not validate_username(username):
            return Response({
                'error': 'Username must be 3-30 characters long and contain only letters, numbers, and underscores.',
                'code': 'INVALID_USERNAME'
            }, status=status.HTTP_400_BAD_REQUEST)

        if email and not validate_email(email):
            return Response({
                'error': 'Invalid email format.',
                'code': 'INVALID_EMAIL'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if user exists
        if User.objects.filter(username=username).exists():
            return Response({
                'error': 'Username already exists.',
                'code': 'USERNAME_EXISTS'
            }, status=status.HTTP_400_BAD_REQUEST)

        if email and User.objects.filter(email=email).exists():
            return Response({
                'error': 'Email already registered.',
                'code': 'EMAIL_EXISTS'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate password
        try:
            validate_password(password)
        except ValidationError as e:
            return Response({
                'error': 'Password validation failed.',
                'details': list(e.messages),
                'code': 'WEAK_PASSWORD'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create user
        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email
            )
            token, created = Token.objects.get_or_create(user=user)

        logger.info(f"New user registered: {username}")

        return Response({
            'message': 'User registered successfully.',
            'token': token.key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'date_joined': user.date_joined.isoformat()
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return Response({
            'error': 'Internal server error during registration.',
            'code': 'INTERNAL_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_view(request):
    """
    User login with enhanced security
    """
    try:
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')

        if not username or not password:
            return Response({
                'error': 'Username and password are required.',
                'code': 'MISSING_CREDENTIALS'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)

        if user is not None:
            if not user.is_active:
                return Response({
                    'error': 'Account is disabled.',
                    'code': 'ACCOUNT_DISABLED'
                }, status=status.HTTP_403_FORBIDDEN)

            # Update last login
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            # Get or create token
            token, created = Token.objects.get_or_create(user=user)

            logger.info(f"User logged in: {username}")

            return Response({
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'last_login': user.last_login.isoformat() if user.last_login else None
                }
            }, status=status.HTTP_200_OK)
        else:
            logger.warning(f"Failed login attempt for username: {username}")
            return Response({
                'error': 'Invalid credentials.',
                'code': 'INVALID_CREDENTIALS'
            }, status=status.HTTP_401_UNAUTHORIZED)

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return Response({
            'error': 'Internal server error during login.',
            'code': 'INTERNAL_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    User logout - invalidate token
    """
    try:
        # Delete the user's token
        Token.objects.filter(user=request.user).delete()

        logger.info(f"User logged out: {request.user.username}")

        return Response({
            'message': 'Successfully logged out.'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return Response({
            'error': 'Error during logout.',
            'code': 'LOGOUT_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def refresh_token(request):
    """
    Refresh user token
    """
    try:
        # Delete old token and create new one
        Token.objects.filter(user=request.user).delete()
        token = Token.objects.create(user=request.user)

        return Response({
            'token': token.key,
            'message': 'Token refreshed successfully.'
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return Response({
            'error': 'Error refreshing token.',
            'code': 'TOKEN_REFRESH_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def protected_view(request):
    """
    Protected endpoint example
    """
    return Response({
        'message': f'Hello, {request.user.username}! This is a protected endpoint.',
        'user_id': request.user.id,
        'timestamp': timezone.now().isoformat()
    }, status=status.HTTP_200_OK)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """
    Get or update user profile
    """
    try:
        if request.method == 'GET':
            return Response({
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'date_joined': request.user.date_joined.isoformat(),
                'last_login': request.user.last_login.isoformat() if request.user.last_login else None,
                'is_active': request.user.is_active
            }, status=status.HTTP_200_OK)

        elif request.method == 'PUT':
            user = request.user

            # Update allowed fields
            email = request.data.get('email', '').strip()
            first_name = request.data.get('first_name', '').strip()
            last_name = request.data.get('last_name', '').strip()

            if email:
                if not validate_email(email):
                    return Response({
                        'error': 'Invalid email format.',
                        'code': 'INVALID_EMAIL'
                    }, status=status.HTTP_400_BAD_REQUEST)

                if User.objects.filter(email=email).exclude(id=user.id).exists():
                    return Response({
                        'error': 'Email already in use.',
                        'code': 'EMAIL_EXISTS'
                    }, status=status.HTTP_400_BAD_REQUEST)

                user.email = email

            user.first_name = first_name
            user.last_name = last_name
            user.save()

            logger.info(f"Profile updated for user: {user.username}")

            return Response({
                'message': 'Profile updated successfully.',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                }
            }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Profile error: {str(e)}")
        return Response({
            'error': 'Error processing profile request.',
            'code': 'PROFILE_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Change user password
    """
    try:
        current_password = request.data.get('current_password', '')
        new_password = request.data.get('new_password', '')

        if not current_password or not new_password:
            return Response({
                'error': 'Current password and new password are required.',
                'code': 'MISSING_PASSWORDS'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        # Verify current password
        if not user.check_password(current_password):
            return Response({
                'error': 'Current password is incorrect.',
                'code': 'INVALID_CURRENT_PASSWORD'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate new password
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({
                'error': 'New password validation failed.',
                'details': list(e.messages),
                'code': 'WEAK_PASSWORD'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Change password
        user.set_password(new_password)
        user.save()

        # Invalidate all tokens for this user
        Token.objects.filter(user=user).delete()

        # Create new token
        token = Token.objects.create(user=user)

        logger.info(f"Password changed for user: {user.username}")

        return Response({
            'message': 'Password changed successfully.',
            'token': token.key  # New token since old ones are invalidated
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        return Response({
            'error': 'Error changing password.',
            'code': 'PASSWORD_CHANGE_ERROR'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
