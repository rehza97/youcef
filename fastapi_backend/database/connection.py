from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool, QueuePool
from core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.DATABASE_ECHO
    )
else:
    # PostgreSQL configuration with optimized connection pool
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        poolclass=QueuePool,
        pool_size=settings.DATABASE_POOL_SIZE,           # Base connection pool size
        # Additional connections when needed
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,                              # Verify connections before use
        # Recycle connections every 5 minutes
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        # Timeout for getting connection from pool
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
        connect_args={
            "connect_timeout": 10,  # Connection timeout
            "application_name": "youcef_backend"
        }
    )

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

# Database dependency


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def init_db():
    """Initialize database"""
    try:
        # Import all models to ensure they are registered
        from models.user import User
        from models.role import Role
        from models.permission import Permission
        from models.notification import Notification
        from models.conversation import Conversation
        from models.message import Message
        from models.user_block import UserBlock
        from models.file_upload import FileUpload, FilePreview

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

        # Create default roles and permissions
        await create_default_data()

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


async def close_db():
    """Close database connections"""
    try:
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


async def create_default_data():
    """Create default roles and permissions"""
    db = SessionLocal()
    try:
        # Check if roles already exist
        from models.role import Role
        from models.permission import Permission

        existing_roles = db.query(Role).count()
        if existing_roles == 0:
            # Create default roles
            admin_role = Role(name="admin", description="Administrator")
            user_role = Role(name="user", description="Regular user")
            moderator_role = Role(name="moderator", description="Moderator")

            db.add_all([admin_role, user_role, moderator_role])

            # Create default permissions
            permissions = [
                Permission(codename="view_users", name="View Users"),
                Permission(codename="edit_users", name="Edit Users"),
                Permission(codename="delete_users", name="Delete Users"),
                Permission(codename="manage_roles", name="Manage Roles"),
                Permission(codename="send_messages", name="Send Messages"),
                Permission(codename="view_messages", name="View Messages"),
                Permission(codename="manage_notifications",
                           name="Manage Notifications"),
            ]

            db.add_all(permissions)
            db.commit()

            logger.info("Default roles and permissions created")

    except Exception as e:
        logger.error(f"Error creating default data: {e}")
        db.rollback()
    finally:
        db.close()
