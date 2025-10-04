"""
Seed script to populate all required permissions in the database.
Run this after creating the permissions table.

Usage:
    python -m fastapi_backend.migrations.seed_permissions
"""

from sqlalchemy.orm import Session
from database.connection import SessionLocal
from models.permission import Permission
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


PERMISSIONS = [
    # User Management
    {
        "codename": "can_manage_users",
        "name": "Manage Users",
        "description": "Create, read, update, and delete users"
    },
    {
        "codename": "can_view_users",
        "name": "View Users",
        "description": "View user lists and profiles (read-only)"
    },

    # Role & Permission Management
    {
        "codename": "can_manage_rbac",
        "name": "Manage RBAC",
        "description": "Create, assign, and manage roles and permissions"
    },
    {
        "codename": "can_view_rbac",
        "name": "View RBAC",
        "description": "View roles and permissions (read-only)"
    },

    # Dashboard & Analytics
    {
        "codename": "can_view_dashboard",
        "name": "View Dashboard",
        "description": "Access the main dashboard page"
    },
    {
        "codename": "can_view_analytics",
        "name": "View Analytics",
        "description": "Access analytics and reporting features"
    },
    {
        "codename": "can_export_analytics",
        "name": "Export Analytics",
        "description": "Export analytics reports in various formats"
    },

    # File Management
    {
        "codename": "can_upload_files",
        "name": "Upload Files",
        "description": "Upload files to the system"
    },
    {
        "codename": "can_manage_files",
        "name": "Manage All Files",
        "description": "View, download, and delete all files (admin-level file management)"
    },
    {
        "codename": "can_manage_own_files",
        "name": "Manage Own Files",
        "description": "Manage files uploaded by the user"
    },

    # ETL & Data Processing
    {
        "codename": "can_run_etl",
        "name": "Run ETL Processes",
        "description": "Execute ETL data processing tasks"
    },
    {
        "codename": "can_view_etl_results",
        "name": "View ETL Results",
        "description": "View and download ETL processing results"
    },

    # Messaging & Notifications
    {
        "codename": "can_send_messages",
        "name": "Send Messages",
        "description": "Send messages to other users"
    },
    {
        "codename": "can_manage_messages",
        "name": "Manage Messages",
        "description": "Manage and moderate all messages (admin)"
    },
    {
        "codename": "can_manage_notifications",
        "name": "Manage Notifications",
        "description": "Configure and send system notifications"
    },
    {
        "codename": "can_broadcast",
        "name": "Broadcast Messages",
        "description": "Send broadcast messages to multiple users"
    },

    # Settings & Configuration
    {
        "codename": "can_manage_settings",
        "name": "Manage Settings",
        "description": "Configure system settings and preferences"
    },
    {
        "codename": "can_view_settings",
        "name": "View Settings",
        "description": "View system settings (read-only)"
    },

    # DOT & Data Access
    {
        "codename": "can_view_dot_data",
        "name": "View DOT Data",
        "description": "View data scoped to assigned DOT region (used alongside role-based DOT filtering)"
    },
    {
        "codename": "can_view_all_dots",
        "name": "View All DOT Data",
        "description": "View data across all DOT regions (admin/super_user)"
    },
    {
        "codename": "can_manage_dots",
        "name": "Manage DOTs",
        "description": "Create, update, and delete DOT regions"
    },

    # Park/Encaissement Data
    {
        "codename": "can_view_park_data",
        "name": "View Park Data",
        "description": "View park subscriber data (DOT-scoped)"
    },
    {
        "codename": "can_manage_park_data",
        "name": "Manage Park Data",
        "description": "Import, process, and manage park data"
    },
    {
        "codename": "can_view_encaissement_data",
        "name": "View Encaissement Data",
        "description": "View encaissement analytics (DOT-scoped)"
    },

    # Audit & Logs
    {
        "codename": "can_view_audit_logs",
        "name": "View Audit Logs",
        "description": "View system audit logs and user activity"
    },
]


def seed_permissions(db: Session):
    """Seed all permissions into the database"""
    created_count = 0
    updated_count = 0
    skipped_count = 0

    for perm_data in PERMISSIONS:
        existing = db.query(Permission).filter(
            Permission.codename == perm_data["codename"]
        ).first()

        if existing:
            # Update description if changed
            if existing.description != perm_data["description"] or existing.name != perm_data["name"]:
                existing.name = perm_data["name"]
                existing.description = perm_data["description"]
                updated_count += 1
                logger.info(f"Updated permission: {perm_data['codename']}")
            else:
                skipped_count += 1
        else:
            # Create new permission
            new_perm = Permission(**perm_data)
            db.add(new_perm)
            created_count += 1
            logger.info(f"Created permission: {perm_data['codename']}")

    db.commit()

    logger.info(f"Permission seeding complete:")
    logger.info(f"  - Created: {created_count}")
    logger.info(f"  - Updated: {updated_count}")
    logger.info(f"  - Skipped: {skipped_count}")
    logger.info(f"  - Total: {len(PERMISSIONS)}")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        logger.info("Starting permission seeding...")
        seed_permissions(db)
        logger.info("Permission seeding completed successfully!")
    except Exception as e:
        logger.error(f"Error seeding permissions: {e}")
        db.rollback()
        raise
    finally:
        db.close()
