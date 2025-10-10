"""
RBAC Auto-initialization on startup.
Checks if RBAC system is initialized and runs migrations if needed.
Also creates default admin account if none exists.
"""

from sqlalchemy.orm import Session
from database.connection import SessionLocal
from models.permission import Permission
from models.role import Role, UserRole
from models.user import User
from core.security import get_password_hash
import logging
import os

logger = logging.getLogger(__name__)


def create_default_admin(db: Session):
    """
    Create default admin account if no admin exists.
    Credentials can be overridden via environment variables.
    """
    # Check if any admin user exists (is_superuser=True or has admin role)
    admin_exists = db.query(User).filter(User.is_superuser == True).first()

    if admin_exists:
        logger.info(f"✓ Admin account already exists: {admin_exists.username}")
        return

    logger.info("👤 No admin account found. Creating default admin...")

    # Get credentials from environment or use defaults
    admin_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")

    # Ensure password is not longer than 72 bytes (bcrypt limit)
    password_bytes = len(admin_password.encode('utf-8'))
    logger.info(
        f"Admin password length: {len(admin_password)} characters, {password_bytes} bytes")

    if password_bytes > 72:
        admin_password = admin_password[:72]
        logger.warning(f"Admin password truncated to 72 bytes")

    logger.info(
        f"Final password: '{admin_password}' ({len(admin_password)} chars, {len(admin_password.encode('utf-8'))} bytes)")
    logger.info(
        f"Creating admin user: {admin_username} with email: {admin_email}")

    # Create admin user
    admin_user = User(
        username=admin_username,
        email=admin_email,
        hashed_password=get_password_hash(admin_password),
        first_name="System",
        last_name="Administrator",
        is_active=True,
        is_staff=True,
        is_superuser=True
    )

    db.add(admin_user)
    db.flush()  # Get the ID

    # Assign admin role
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if admin_role:
        user_role = UserRole(user_id=admin_user.id, role_id=admin_role.id)
        db.add(user_role)

    db.commit()

    logger.info("=" * 70)
    logger.info("✅ Default admin account created!")
    logger.info("=" * 70)
    logger.info(f"   Username: {admin_username}")
    logger.info(f"   Email:    {admin_email}")
    logger.info(f"   Password: {admin_password}")
    logger.info("=" * 70)
    logger.warning(
        "⚠️  IMPORTANT: Change the admin password immediately after first login!")
    logger.info("=" * 70)


def check_and_init_rbac():
    """
    Check if RBAC system is initialized. If not, run initialization.
    Also creates default admin account if none exists.
    This is called on application startup.
    """
    db = SessionLocal()
    try:
        # Check if we have permissions and roles
        perm_count = db.query(Permission).count()
        role_count = db.query(Role).count()

        if perm_count == 0 or role_count == 0:
            logger.info("=" * 70)
            logger.info(
                "🔧 RBAC system not initialized. Running auto-initialization...")
            logger.info("=" * 70)

            # Import and run the init function
            from migrations.seed_permissions import seed_permissions
            from migrations.seed_default_roles import seed_default_roles

            # Seed permissions first
            if perm_count == 0:
                logger.info("📝 Seeding permissions...")
                seed_permissions(db)

            # Then seed roles
            if role_count == 0:
                logger.info("👥 Creating default roles...")
                seed_default_roles(db)

            logger.info("=" * 70)
            logger.info("✅ RBAC system initialized successfully!")
            logger.info("=" * 70)
        else:
            logger.info(
                f"✓ RBAC system already initialized ({perm_count} permissions, {role_count} roles)")

        # Check and create admin account if needed
        create_default_admin(db)

    except Exception as e:
        logger.error(f"❌ Failed to initialize RBAC system: {e}")
        db.rollback()
        raise
    finally:
        db.close()
