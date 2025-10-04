"""
Seed script to create default roles with their default permissions.
Run this after seeding permissions to set up the base RBAC structure.

Usage:
    python -m fastapi_backend.migrations.seed_default_roles
"""

from sqlalchemy.orm import Session
from database.connection import SessionLocal
from models.role import Role, RolePermission
from models.permission import Permission
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Define default roles with their permissions
DEFAULT_ROLES = {
    "admin": {
        "description": "System administrator with full access to all features and data",
        "permissions": "ALL"  # Special flag - admin gets all permissions
    },
    "SUPER_USER": {
        "description": "Super user with access to all DOT regions and most management features",
        "permissions": [
            "can_view_dashboard",
            "can_view_analytics",
            "can_export_analytics",
            "can_view_encaissement_data",
            "can_view_all_dots",
            "can_view_park_data",
            "can_manage_park_data",
            "can_run_etl",
            "can_view_etl_results",
            "can_upload_files",
            "can_manage_own_files",
            "can_send_messages",
            "can_view_settings",
            "can_view_audit_logs",
        ]
    },
    "DOT_USER": {
        "description": "Regional user with access restricted to their assigned DOT region",
        "permissions": [
            "can_view_dashboard",
            "can_view_analytics",
            "can_view_encaissement_data",
            "can_view_dot_data",
            "can_view_park_data",
            "can_manage_own_files",
            "can_send_messages",
        ]
    },
    "Data Analyst": {
        "description": "Analyst with read access to analytics and reporting features",
        "permissions": [
            "can_view_dashboard",
            "can_view_analytics",
            "can_export_analytics",
            "can_view_encaissement_data",
            "can_view_park_data",
            "can_view_etl_results",
            "can_view_settings",
        ]
    },
    "File Manager": {
        "description": "User who can upload and manage files",
        "permissions": [
            "can_view_dashboard",
            "can_upload_files",
            "can_manage_files",
            "can_manage_own_files",
        ]
    },
    "ETL Operator": {
        "description": "User who can run ETL processes and view results",
        "permissions": [
            "can_view_dashboard",
            "can_run_etl",
            "can_view_etl_results",
            "can_upload_files",
            "can_manage_own_files",
            "can_view_park_data",
            "can_manage_park_data",
        ]
    },
    "Moderator": {
        "description": "User who can manage messages and notifications",
        "permissions": [
            "can_view_dashboard",
            "can_send_messages",
            "can_manage_messages",
            "can_manage_notifications",
            "can_broadcast",
            "can_view_users",
        ]
    },
    "User": {
        "description": "Basic user with minimal permissions",
        "permissions": [
            "can_view_dashboard",
            "can_send_messages",
            "can_manage_own_files",
        ]
    },
}


def seed_default_roles(db: Session):
    """Seed default roles and assign their permissions"""

    # First, get all permissions for "ALL" assignment
    all_permissions = db.query(Permission).all()
    permission_map = {perm.codename: perm for perm in all_permissions}

    created_count = 0
    updated_count = 0
    skipped_count = 0

    for role_name, role_config in DEFAULT_ROLES.items():
        # Check if role exists
        existing_role = db.query(Role).filter(Role.name == role_name).first()

        if existing_role:
            # Update description if changed
            if existing_role.description != role_config["description"]:
                existing_role.description = role_config["description"]
                updated_count += 1
                logger.info(f"Updated role: {role_name}")
            else:
                skipped_count += 1

            role = existing_role
        else:
            # Create new role
            role = Role(
                name=role_name,
                description=role_config["description"]
            )
            db.add(role)
            db.flush()  # Get the ID
            created_count += 1
            logger.info(f"Created role: {role_name}")

        # Assign permissions
        permission_codenames = role_config["permissions"]

        # Clear existing permissions for this role to avoid duplicates
        db.query(RolePermission).filter(RolePermission.role_id == role.id).delete()

        if permission_codenames == "ALL":
            # Admin gets all permissions
            for perm in all_permissions:
                role_perm = RolePermission(role_id=role.id, permission_id=perm.id)
                db.add(role_perm)
            logger.info(f"  → Assigned ALL permissions ({len(all_permissions)}) to {role_name}")
        else:
            # Assign specific permissions
            assigned_count = 0
            missing_perms = []

            for perm_codename in permission_codenames:
                if perm_codename in permission_map:
                    role_perm = RolePermission(
                        role_id=role.id,
                        permission_id=permission_map[perm_codename].id
                    )
                    db.add(role_perm)
                    assigned_count += 1
                else:
                    missing_perms.append(perm_codename)

            logger.info(f"  → Assigned {assigned_count} permissions to {role_name}")
            if missing_perms:
                logger.warning(f"  → Missing permissions for {role_name}: {', '.join(missing_perms)}")

    db.commit()

    logger.info(f"\nDefault roles seeding complete:")
    logger.info(f"  - Created: {created_count}")
    logger.info(f"  - Updated: {updated_count}")
    logger.info(f"  - Skipped: {skipped_count}")
    logger.info(f"  - Total roles: {len(DEFAULT_ROLES)}")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        logger.info("Starting default roles seeding...")
        logger.info("=" * 60)

        # Check if permissions exist
        perm_count = db.query(Permission).count()
        if perm_count == 0:
            logger.error("No permissions found! Please run seed_permissions.py first.")
            exit(1)

        logger.info(f"Found {perm_count} permissions in database")
        logger.info("=" * 60)

        seed_default_roles(db)

        logger.info("=" * 60)
        logger.info("Default roles seeding completed successfully!")
        logger.info("\nCreated roles:")
        for role_name, config in DEFAULT_ROLES.items():
            logger.info(f"  • {role_name}: {config['description']}")

    except Exception as e:
        logger.error(f"Error seeding default roles: {e}")
        db.rollback()
        raise
    finally:
        db.close()
