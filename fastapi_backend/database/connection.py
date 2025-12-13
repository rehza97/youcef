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
    # ✅ MAIN ENGINE: API requests (priority for user navigation)
    engine = create_engine(
        settings.DATABASE_URL,
        echo=settings.DATABASE_ECHO,
        poolclass=QueuePool,
        # ✅ Reduced to prevent connection exhaustion
        pool_size=10,
        max_overflow=15,                                 # ✅ Reduced to prevent exhaustion
        pool_pre_ping=True,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        # ✅ Reduced from 30 for faster failures
        pool_timeout=10,
        connect_args={
            "connect_timeout": 10,
            "application_name": "youcef_api"             # ✅ Identify API requests
        }
    )

    # ✅ BACKGROUND ENGINE: File processing (separate pool to avoid blocking API)
    background_engine = create_engine(
        settings.DATABASE_URL,
        echo=False,                                      # Don't log background queries
        poolclass=QueuePool,
        pool_size=5,                                     # ✅ Smaller pool for background
        max_overflow=10,                                  # ✅ Limited overflow
        pool_pre_ping=True,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        pool_timeout=5,                                  # ✅ Fast timeout for background
        connect_args={
            "connect_timeout": 10,
            "application_name": "youcef_background"      # ✅ Identify background tasks
        }
    )

    # ✅ WEBSOCKET ENGINE: Real-time connections (separate pool)
    websocket_engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        poolclass=QueuePool,
        pool_size=3,                                     # ✅ Small pool for WebSocket
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=settings.DATABASE_POOL_RECYCLE,
        pool_timeout=5,
        connect_args={
            "connect_timeout": 10,
            "application_name": "youcef_websocket"       # ✅ Identify WebSocket connections
        }
    )

    logger.info(f"✅ Connection pools initialized:")
    logger.info(f"   API Pool: {10} base + {15} overflow = 25 connections")
    logger.info(
        f"   Background Pool: {5} base + {10} overflow = 15 connections")
    logger.info(
        f"   WebSocket Pool: {3} base + {5} overflow = 8 connections")
    logger.info(f"   TOTAL: 48 connections (PostgreSQL max: 100)")

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
        # Import all models to ensure they are registered with SQLAlchemy
        # Core RBAC models
        from models.user import User
        from models.role import Role, UserRole, RolePermission
        from models.permission import Permission
        from models.user_block import UserBlock
        
        # Messaging models
        from models.notification import Notification, NotificationPreference
        from models.conversation import Conversation, ConversationParticipant
        from models.message import Message, MessageReaction, MessageReadReceipt
        
        # File management
        from models.file_upload import FileUpload, FilePreview
        
        # Business/ETL models
        from models.dot import DOT
        from models.park import Park, ParkAnomaly
        from models.park_2b import Park2B
        from models.revenue import RevenueJournal, AccountDescription, RevenueObjective, RevenueAnomaly
        from models.revenue_pivot import RevenuePivotCache, RevenuePivotMetadata
        from models.encaissement import EncaissementARDot, EncaissementAnomaly, EncaissementAggregateView
        from models.creance import CreancePeriodiqueDot, CreanceAggregateView
        from models.user_module_dot import UserModuleDOT
        from models.module_dot_config import ModuleDOTConfig

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
