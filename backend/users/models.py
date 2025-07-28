from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.utils import timezone

# Create your models here.


class Permission(models.Model):
    """Custom permission model for RBAC"""
    codename = models.CharField(
        max_length=100,
        unique=True,
        validators=[MinLengthValidator(3), MaxLengthValidator(100)],
        help_text="Unique permission codename"
    )
    description = models.TextField(
        blank=True,
        help_text="Human-readable description of the permission"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'custom_permissions'
        ordering = ['codename']
        indexes = [
            models.Index(fields=['codename'], name='perm_codename_idx'),
        ]

    def __str__(self):
        return self.codename

    def clean(self):
        """Custom validation"""
        super().clean()
        if self.codename:
            self.codename = self.codename.lower().strip()


class Role(models.Model):
    """Role model for RBAC"""
    name = models.CharField(
        max_length=50,
        unique=True,
        validators=[MinLengthValidator(2), MaxLengthValidator(50)],
        help_text="Unique role name"
    )
    description = models.TextField(
        blank=True,
        help_text="Role description"
    )
    permissions = models.ManyToManyField(
        Permission,
        through='RolePermission',
        related_name='roles',
        blank=True,
        help_text="Permissions assigned to this role"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this role is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roles'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name'], name='role_name_idx'),
            models.Index(fields=['is_active'], name='role_active_idx'),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        """Custom validation"""
        super().clean()
        if self.name:
            self.name = self.name.lower().strip()


class RolePermission(models.Model):
    """Through model for Role-Permission relationship"""
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_permissions'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='permission_roles'
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_permissions'
    )

    class Meta:
        db_table = 'role_permissions'
        unique_together = ('role', 'permission')
        indexes = [
            models.Index(fields=['role', 'permission'], name='role_perm_idx'),
        ]

    def __str__(self):
        return f"{self.role.name} - {self.permission.codename}"


class UserRole(models.Model):
    """User role assignment"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_roles'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_users'
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_roles'
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this role assignment is active"
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration date for the role"
    )

    class Meta:
        db_table = 'user_roles'
        unique_together = ('user', 'role')
        indexes = [
            models.Index(fields=['user'], name='user_role_user_idx'),
            models.Index(fields=['role'], name='user_role_role_idx'),
            models.Index(fields=['is_active'], name='user_role_active_idx'),
            models.Index(fields=['expires_at'], name='user_role_expires_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"

    def is_expired(self):
        """Check if the role assignment has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def clean(self):
        """Custom validation"""
        super().clean()
        if self.expires_at and self.expires_at <= timezone.now():
            from django.core.exceptions import ValidationError
            raise ValidationError("Expiration date must be in the future")


class Setting(models.Model):
    """Application settings"""
    key = models.CharField(
        max_length=100,
        unique=True,
        validators=[MinLengthValidator(2), MaxLengthValidator(100)],
        help_text="Setting key"
    )
    value = models.TextField(
        help_text="Setting value (can be JSON)"
    )
    description = models.TextField(
        blank=True,
        help_text="Setting description"
    )
    is_public = models.BooleanField(
        default=False,
        help_text="Whether this setting is public (non-sensitive)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'settings'
        ordering = ['key']
        indexes = [
            models.Index(fields=['key'], name='setting_key_idx'),
            models.Index(fields=['is_public'], name='setting_public_idx'),
        ]

    def __str__(self):
        return f"{self.key}: {self.value[:50]}..."

    def clean(self):
        """Custom validation"""
        super().clean()
        if self.key:
            self.key = self.key.lower().strip()


class UserProfile(models.Model):
    """Extended user profile"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        help_text="User avatar image"
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text="User biography"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Phone number"
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text="Date of birth"
    )
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        help_text="User timezone"
    )
    language = models.CharField(
        max_length=10,
        default='en',
        help_text="Preferred language"
    )
    is_email_verified = models.BooleanField(
        default=False,
        help_text="Whether email is verified"
    )
    is_phone_verified = models.BooleanField(
        default=False,
        help_text="Whether phone is verified"
    )
    two_factor_enabled = models.BooleanField(
        default=False,
        help_text="Whether 2FA is enabled"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profiles'
        indexes = [
            models.Index(fields=['user'], name='profile_user_idx'),
            models.Index(fields=['is_email_verified'],
                         name='profile_email_verified_idx'),
            models.Index(fields=['two_factor_enabled'],
                         name='profile_2fa_idx'),
        ]

    def __str__(self):
        return f"{self.user.username}'s profile"


class UserSession(models.Model):
    """Track user sessions for security"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['user'], name='session_user_idx'),
            models.Index(fields=['session_key'], name='session_key_idx'),
            models.Index(fields=['is_active'], name='session_active_idx'),
            models.Index(fields=['last_activity'],
                         name='session_activity_idx'),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"
