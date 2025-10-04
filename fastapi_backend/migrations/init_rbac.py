"""
Master RBAC initialization script.
Runs all necessary migrations to set up the complete permission and role system.

This script:
1. Seeds all permissions
2. Creates default roles
3. Assigns permissions to roles

Usage:
    python -m fastapi_backend.migrations.init_rbac
"""

from sqlalchemy.orm import Session
from database.connection import SessionLocal
from models.permission import Permission
from models.role import Role
import logging
import sys

# Import the individual seed functions
from .seed_permissions import seed_permissions
from .seed_default_roles import seed_default_roles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_rbac_system(db: Session):
    """Initialize the complete RBAC system"""

    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║" + " RBAC SYSTEM INITIALIZATION ".center(58) + "║")
    logger.info("╚" + "═" * 58 + "╝")
    logger.info("")

    # Step 1: Check current state
    logger.info("📊 Checking current database state...")
    perm_count = db.query(Permission).count()
    role_count = db.query(Role).count()
    logger.info(f"  → Existing permissions: {perm_count}")
    logger.info(f"  → Existing roles: {role_count}")
    logger.info("")

    # Step 2: Seed permissions
    logger.info("🔑 Step 1: Seeding permissions...")
    logger.info("-" * 60)
    try:
        seed_permissions(db)
        logger.info("✓ Permissions seeded successfully")
    except Exception as e:
        logger.error(f"✗ Failed to seed permissions: {e}")
        raise
    logger.info("")

    # Step 3: Seed default roles
    logger.info("👥 Step 2: Creating default roles...")
    logger.info("-" * 60)
    try:
        seed_default_roles(db)
        logger.info("✓ Default roles created successfully")
    except Exception as e:
        logger.error(f"✗ Failed to create default roles: {e}")
        raise
    logger.info("")

    # Step 4: Summary
    logger.info("📈 Final database state:")
    final_perm_count = db.query(Permission).count()
    final_role_count = db.query(Role).count()
    logger.info(f"  → Total permissions: {final_perm_count}")
    logger.info(f"  → Total roles: {final_role_count}")
    logger.info("")

    logger.info("╔" + "═" * 58 + "╗")
    logger.info("║" + " RBAC INITIALIZATION COMPLETE! ".center(58) + "║")
    logger.info("╚" + "═" * 58 + "╝")
    logger.info("")
    logger.info("✅ Your RBAC system is now ready to use!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Restart your FastAPI backend")
    logger.info("  2. Create admin user (or assign 'admin' role to existing user)")
    logger.info("  3. Login and start managing roles/permissions via the UI")
    logger.info("")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        init_rbac_system(db)
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ RBAC initialization failed: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()
