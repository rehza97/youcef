#!/usr/bin/env python3
"""
Test script to verify all imports work correctly
"""


def test_imports():
    """Test all critical imports"""
    try:
        print("Testing imports...")

        # Test core imports
        from core.config import settings
        print("✓ Core config imported")

        from core.security import Token, verify_password, get_password_hash
        print("✓ Core security imported")

        from core.rate_limiter import RateLimiter
        print("✓ Core rate limiter imported")

        # Test database imports
        from database.connection import get_db, init_db
        print("✓ Database connection imported")

        # Test model imports
        from models.user import User, UserCreate, UserResponse
        print("✓ User models imported")

        from models.role import Role, RoleResponse
        print("✓ Role models imported")

        from models.permission import Permission, PermissionResponse
        print("✓ Permission models imported")

        from models.notification import Notification, NotificationResponse
        print("✓ Notification models imported")

        from models.conversation import Conversation, ConversationResponse
        print("✓ Conversation models imported")

        from models.message import Message, MessageResponse
        print("✓ Message models imported")

        from models.user_block import UserBlock
        print("✓ UserBlock models imported")

        # Test API imports
        from api.auth import auth_router
        print("✓ Auth router imported")

        from api.users import users_router
        print("✓ Users router imported")

        from api.notifications import notifications_router
        print("✓ Notifications router imported")

        from api.messaging import messaging_router
        print("✓ Messaging router imported")

        from api.health import health_router
        print("✓ Health router imported")

        print("\n🎉 All imports successful!")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_imports()
    exit(0 if success else 1)
