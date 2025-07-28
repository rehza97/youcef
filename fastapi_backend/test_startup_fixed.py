#!/usr/bin/env python3
"""
Test script to verify that the FastAPI server can start without SQLAlchemy errors
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("🔍 Testing FastAPI server startup...")

    # Test importing main components
    print("📦 Importing database connection...")
    from database.connection import engine, Base

    print("📦 Importing models...")
    from models.user import User
    from models.role import Role, UserRole, RolePermission
    from models.permission import Permission
    from models.notification import Notification, NotificationPreference
    from models.conversation import Conversation, ConversationParticipant
    from models.message import Message, MessageReaction
    from models.user_block import UserBlock
    from models.file_upload import FileUpload, FilePreview

    print("📦 Importing API routers...")
    from api.auth import auth_router
    from api.users import users_router
    from api.notifications import notifications_router
    from api.messaging import messaging_router
    from api.files import files_router

    print("📦 Importing main application...")
    from main import app

    print("✅ All imports successful!")

    # Test database table creation
    print("🗄️ Testing database table creation...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")

    # Test that metadata conflicts are resolved
    print("🔧 Testing metadata conflict resolution...")

    # Check that models don't have 'metadata' attribute conflicts
    test_user = User(
        username="test",
        email="test@example.com",
        hashed_password="test"
    )

    test_conversation = Conversation(
        name="Test Conversation",
        conversation_type="group",
        conversation_metadata={"test": "data"}
    )

    test_message = Message(
        content="Test message",
        message_type="text",
        message_metadata={"test": "data"}
    )

    print("✅ Metadata conflicts resolved - models can be instantiated")

    # Check table count
    print(f"✅ Database tables defined: {len(Base.metadata.tables)} tables")
    table_names = list(Base.metadata.tables.keys())
    print(f"   Tables: {', '.join(table_names)}")

    print("\n🎉 All tests passed! FastAPI server should start without errors.")
    print("💡 You can now run: python main.py")

except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
