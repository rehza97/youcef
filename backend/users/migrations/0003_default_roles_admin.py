from django.db import migrations


def create_default_roles_permissions(apps, schema_editor):
    Permission = apps.get_model('users', 'Permission')
    Role = apps.get_model('users', 'Role')
    UserRole = apps.get_model('users', 'UserRole')
    User = apps.get_model('auth', 'User')

    # Define default permissions
    default_permissions = [
        ('can_view_dashboard', 'Can view dashboard'),
        ('can_manage_users', 'Can manage users'),
        ('can_view_analytics', 'Can view analytics'),
        ('can_manage_settings', 'Can manage settings'),
        ('can_manage_rbac', 'Can manage RBAC'),
        ('can_manage_roles', 'Can manage roles'),
        ('can_manage_permissions', 'Can manage permissions'),
    ]
    perm_objs = []
    for codename, desc in default_permissions:
        perm, _ = Permission.objects.get_or_create(
            codename=codename, defaults={'description': desc})
        perm_objs.append(perm)

    # Create roles
    admin_role, _ = Role.objects.get_or_create(
        name='Admin', defaults={'description': 'Full access'})
    manager_role, _ = Role.objects.get_or_create(
        name='Manager', defaults={'description': 'Manager access'})
    user_role, _ = Role.objects.get_or_create(
        name='User', defaults={'description': 'Basic user'})

    # Assign all permissions to Admin role
    admin_role.permissions.set(perm_objs)
    admin_role.save()

    # Assign some permissions to Manager (example)
    manager_perms = [p for p in perm_objs if p.codename in [
        'can_view_dashboard', 'can_manage_users', 'can_view_analytics']]
    manager_role.permissions.set(manager_perms)
    manager_role.save()

    # Assign only dashboard view to User
    user_perms = [p for p in perm_objs if p.codename == 'can_view_dashboard']
    user_role.permissions.set(user_perms)
    user_role.save()

    # Assign Admin role to admin user
    try:
        admin_user = User.objects.get(username='admin')
        UserRole.objects.get_or_create(user=admin_user, role=admin_role)
    except User.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0002_permission_role_permissions'),
    ]

    operations = [
        migrations.RunPython(create_default_roles_permissions),
    ]
