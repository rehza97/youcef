#!/usr/bin/env python3
"""
Script to check the current state of the PostgreSQL database
"""

from sqlalchemy.orm import Session
from database.connection import get_db

# Import all models to ensure they are registered
from models.user import User
from models.role import Role, UserRole
from models.permission import Permission
from models.conversation import Conversation
from models.message import Message
from models.notification import Notification
from models.user_block import UserBlock
from models.file_upload import FileUpload, FilePreview


def check_database_state():
    """Check the current state of the database"""

    db = next(get_db())

    try:
        print("🔍 Checking PostgreSQL database state...")
        print("=" * 50)

        # Check roles
        roles = db.query(Role).all()
        print(f"📋 Roles ({len(roles)}):")
        for role in roles:
            print(f"   - {role.name}: {role.description}")

        # Check permissions
        permissions = db.query(Permission).all()
        print(f"\n🔐 Permissions ({len(permissions)}):")
        for perm in permissions:
            print(f"   - {perm.codename}: {perm.description}")

        # Check users
        users = db.query(User).all()
        print(f"\n👥 Users ({len(users)}):")
        for user in users:
            roles_str = ", ".join(
                [r.role.name for r in user.roles]) if user.roles else "No roles"
            print(f"   - {user.username} ({user.email}): {roles_str}")

        # Check conversations
        conversations = db.query(Conversation).all()
        print(f"\n💬 Conversations ({len(conversations)}):")
        for conv in conversations:
            print(f"   - {conv.conversation_type}: {conv.name or 'No name'}")

        # Check messages
        messages = db.query(Message).all()
        print(f"\n💭 Messages ({len(messages)}):")
        for msg in messages:
            sender = db.query(User).filter(User.id == msg.sender_id).first()
            sender_name = sender.username if sender else "Unknown"
            print(f"   - {sender_name}: {msg.content[:50]}...")

        print("\n✅ Database state check completed!")

    except Exception as e:
        print(f"❌ Error checking database state: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    check_database_state()
