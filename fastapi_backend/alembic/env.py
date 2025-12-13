# Import all models to ensure they're registered with SQLAlchemy for migrations
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

from database.connection import Base
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import all models to ensure they're registered with SQLAlchemy

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
