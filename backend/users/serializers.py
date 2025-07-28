from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import Role, UserRole, Permission, Setting, UserProfile, RolePermission
import re


class PermissionSerializer(serializers.ModelSerializer):
    """Serializer for Permission model"""

    class Meta:
        model = Permission
        fields = ['id', 'codename', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_codename(self, value):
        """Validate permission codename"""
        if not value:
            raise serializers.ValidationError("Codename is required.")

        value = value.lower().strip()

        # Check format (alphanumeric and underscores only)
        if not re.match(r'^[a-z0-9_]+$', value):
            raise serializers.ValidationError(
                "Codename can only contain lowercase letters, numbers, and underscores."
            )

        # Check length
        if len(value) < 3:
            raise serializers.ValidationError(
                "Codename must be at least 3 characters long.")

        if len(value) > 100:
            raise serializers.ValidationError(
                "Codename cannot exceed 100 characters.")

        return value


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model"""
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_count = serializers.SerializerMethodField()
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id', 'name', 'description', 'permissions', 'permission_count',
            'user_count', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_permission_count(self, obj):
        """Get number of permissions for this role"""
        return obj.permissions.count()

    def get_user_count(self, obj):
        """Get number of users with this role"""
        return obj.role_users.filter(is_active=True).count()

    def validate_name(self, value):
        """Validate role name"""
        if not value:
            raise serializers.ValidationError("Role name is required.")

        value = value.lower().strip()

        # Check format
        if not re.match(r'^[a-z0-9_\s]+$', value):
            raise serializers.ValidationError(
                "Role name can only contain lowercase letters, numbers, spaces, and underscores."
            )

        # Check length
        if len(value) < 2:
            raise serializers.ValidationError(
                "Role name must be at least 2 characters long.")

        if len(value) > 50:
            raise serializers.ValidationError(
                "Role name cannot exceed 50 characters.")

        return value


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    full_name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'is_active', 'is_staff', 'date_joined',
            'last_login', 'roles', 'profile'
        ]
        read_only_fields = ['date_joined', 'last_login']

    def get_full_name(self, obj):
        """Get user's full name"""
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_roles(self, obj):
        """Get user's active roles"""
        active_roles = obj.user_roles.filter(
            is_active=True).select_related('role')
        return [
            {
                'id': ur.role.id,
                'name': ur.role.name,
                'assigned_at': ur.assigned_at
            }
            for ur in active_roles
        ]

    def get_profile(self, obj):
        """Get user profile if exists"""
        try:
            profile = obj.profile
            return {
                'avatar': profile.avatar.url if profile.avatar else None,
                'bio': profile.bio,
                'timezone': profile.timezone,
                'language': profile.language,
                'is_email_verified': profile.is_email_verified,
                'two_factor_enabled': profile.two_factor_enabled
            }
        except UserProfile.DoesNotExist:
            return None

    def validate_email(self, value):
        """Validate email format"""
        if value:
            value = value.lower().strip()
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                raise serializers.ValidationError("Invalid email format.")
        return value

    def validate_username(self, value):
        """Validate username"""
        if not value:
            raise serializers.ValidationError("Username is required.")

        value = value.lower().strip()

        # Check format
        if not re.match(r'^[a-z0-9_]+$', value):
            raise serializers.ValidationError(
                "Username can only contain lowercase letters, numbers, and underscores."
            )

        # Check length
        if len(value) < 3:
            raise serializers.ValidationError(
                "Username must be at least 3 characters long.")

        if len(value) > 150:
            raise serializers.ValidationError(
                "Username cannot exceed 150 characters.")

        return value


class UserRoleSerializer(serializers.ModelSerializer):
    """Serializer for UserRole model"""
    user_username = serializers.CharField(
        source='user.username', read_only=True)
    role_name = serializers.CharField(source='role.name', read_only=True)
    assigned_by_username = serializers.CharField(
        source='assigned_by.username', read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = UserRole
        fields = [
            'id', 'user', 'role', 'user_username', 'role_name',
            'assigned_at', 'assigned_by', 'assigned_by_username',
            'is_active', 'expires_at', 'is_expired'
        ]
        read_only_fields = ['assigned_at']

    def get_is_expired(self, obj):
        """Check if role assignment is expired"""
        return obj.is_expired()

    def validate(self, data):
        """Cross-field validation"""
        user = data.get('user')
        role = data.get('role')

        if user and role:
            # Check if assignment already exists
            existing = UserRole.objects.filter(
                user=user,
                role=role,
                is_active=True
            ).exclude(id=self.instance.id if self.instance else None)

            if existing.exists():
                raise serializers.ValidationError(
                    "This user already has this role assigned."
                )

        return data


class SettingSerializer(serializers.ModelSerializer):
    """Serializer for Setting model"""

    class Meta:
        model = Setting
        fields = ['id', 'key', 'value', 'description',
                  'is_public', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate_key(self, value):
        """Validate setting key"""
        if not value:
            raise serializers.ValidationError("Setting key is required.")

        value = value.lower().strip()

        # Check format
        if not re.match(r'^[a-z0-9._]+$', value):
            raise serializers.ValidationError(
                "Setting key can only contain lowercase letters, numbers, dots, and underscores."
            )

        return value

    def to_representation(self, instance):
        """Custom representation - hide sensitive values"""
        data = super().to_representation(instance)

        # Hide sensitive settings for non-public settings
        request = self.context.get('request')
        if not instance.is_public and request and not request.user.is_staff:
            data['value'] = '[HIDDEN]'

        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model"""
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'username', 'avatar', 'bio', 'phone', 'date_of_birth',
            'timezone', 'language', 'is_email_verified', 'is_phone_verified',
            'two_factor_enabled', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'is_email_verified', 'is_phone_verified', 'two_factor_enabled',
            'created_at', 'updated_at'
        ]

    def validate_bio(self, value):
        """Validate bio content"""
        if value and len(value) > 500:
            raise serializers.ValidationError(
                "Bio cannot exceed 500 characters.")
        return value

    def validate_phone(self, value):
        """Validate phone number format"""
        if value:
            # Basic phone validation
            phone_pattern = r'^\+?[\d\s\-\(\)]{10,15}$'
            if not re.match(phone_pattern, value):
                raise serializers.ValidationError(
                    "Invalid phone number format.")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate_current_password(self, value):
        """Validate current password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        """Validate new password"""
        user = self.context['request'].user
        try:
            validate_password(value, user)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, data):
        """Cross-field validation"""
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords do not match.")

        if data['current_password'] == data['new_password']:
            raise serializers.ValidationError(
                "New password must be different from current password.")

        return data


class BulkUserRoleSerializer(serializers.Serializer):
    """Serializer for bulk role assignment"""
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    role_id = serializers.IntegerField()
    expires_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_user_ids(self, value):
        """Validate user IDs exist"""
        existing_users = User.objects.filter(
            id__in=value).values_list('id', flat=True)
        missing_users = set(value) - set(existing_users)

        if missing_users:
            raise serializers.ValidationError(
                f"Users with IDs {missing_users} do not exist."
            )

        return value

    def validate_role_id(self, value):
        """Validate role exists"""
        try:
            Role.objects.get(id=value, is_active=True)
        except Role.DoesNotExist:
            raise serializers.ValidationError(
                "Role does not exist or is inactive.")

        return value
