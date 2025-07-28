#!/usr/bin/env python3
"""
Initialize all models to ensure SQLAlchemy relationships are properly configured
"""


def init_all_models():
    """Import all models to ensure SQLAlchemy relationships are configured"""
    try:
        print("🔧 Initializing all models...")

        # Import database connection first
        from database.connection import Base, engine

        # Import all models to register them with SQLAlchemy
        from models.user import User
        from models.role import Role, UserRole, RolePermission
        from models.permission import Permission
        from models.notification import Notification, NotificationPreference
        from models.conversation import Conversation, ConversationParticipant
        from models.message import Message, MessageReaction
        from models.user_block import UserBlock

        # Configure all mappers to ensure relationships are properly set up
        from sqlalchemy.orm import configure_mappers
        configure_mappers()

        print("✅ All models initialized successfully")
        return True

    except Exception as e:
        print(f"❌ Error initializing models: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    init_all_models()
