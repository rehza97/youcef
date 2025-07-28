#!/usr/bin/env python3
"""
Comprehensive setup script for FastAPI Backend
Handles database setup, migrations, and test user creation
"""

import sys
import os


def setup_database():
    """Set up the database schema"""
    try:
        print("🗄️  Setting up database schema...")

        # Initialize all models first
        from init_models import init_all_models
        if not init_all_models():
            return False

        from database.connection import Base, engine

        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database schema created successfully")
        return True

    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        return False


def create_test_users():
    """Create test users including admin account"""
    try:
        print("\n👥 Creating test users...")

        # Import all models to ensure relationships are properly configured
        from database.connection import get_db
        from models.user import User
        from models.role import Role, UserRole
        from models.permission import Permission
        from models.notification import Notification, NotificationPreference
        from models.conversation import Conversation, ConversationParticipant
        from models.message import Message, MessageReaction
        from models.user_block import UserBlock
        from core.security import get_password_hash
        from datetime import datetime

        db = next(get_db())

        # Create default roles
        roles = {
            "admin": Role(name="admin", description="Administrator with full access"),
            "user": Role(name="user", description="Regular user"),
            "moderator": Role(name="moderator", description="Moderator with limited admin access")
        }

        for role in roles.values():
            existing = db.query(Role).filter(Role.name == role.name).first()
            if not existing:
                db.add(role)

        db.commit()

        # Refresh roles to get IDs
        for name, role in roles.items():
            db.refresh(role)

        print("✅ Default roles created")

        # Create default permissions
        permissions = [
            Permission(name="user_management",
                       codename="user_management", description="Manage users"),
            Permission(name="role_management",
                       codename="role_management", description="Manage roles"),
            Permission(name="message_send", codename="message_send",
                       description="Send messages"),
            Permission(name="message_read", codename="message_read",
                       description="Read messages"),
            Permission(name="notification_manage", codename="notification_manage",
                       description="Manage notifications"),
            Permission(name="conversation_create", codename="conversation_create",
                       description="Create conversations"),
            Permission(name="conversation_join", codename="conversation_join",
                       description="Join conversations"),
            Permission(name="user_block", codename="user_block",
                       description="Block users"),
            Permission(name="system_admin", codename="system_admin",
                       description="System administration")
        ]

        for perm in permissions:
            existing = db.query(Permission).filter(
                Permission.codename == perm.codename).first()
            if not existing:
                db.add(perm)

        db.commit()
        print("✅ Default permissions created")

        # Create test users
        test_users = [
            {
                "username": "admin",
                "email": "admin@a.com",
                "password": "admin",
                "first_name": "Admin",
                "last_name": "User",
                "is_staff": True,
                "is_superuser": True,
                "roles": ["admin"]
            },
            {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "password123",
                "first_name": "John",
                "last_name": "Doe",
                "roles": ["user"]
            },
            {
                "username": "jane_smith",
                "email": "jane@example.com",
                "password": "password123",
                "first_name": "Jane",
                "last_name": "Smith",
                "roles": ["user"]
            },
            {
                "username": "moderator",
                "email": "mod@example.com",
                "password": "mod123",
                "first_name": "Moderator",
                "last_name": "User",
                "is_staff": True,
                "roles": ["moderator"]
            },
            {
                "username": "test_user1",
                "email": "test1@example.com",
                "password": "test123",
                "first_name": "Test",
                "last_name": "User1",
                "roles": ["user"]
            },
            {
                "username": "test_user2",
                "email": "test2@example.com",
                "password": "test123",
                "first_name": "Test",
                "last_name": "User2",
                "roles": ["user"]
            },
            {
                "username": "developer",
                "email": "dev@example.com",
                "password": "dev123",
                "first_name": "Developer",
                "last_name": "User",
                "is_staff": True,
                "roles": ["admin"]
            }
        ]

        created_users = []

        for user_data in test_users:
            # Check if user already exists
            existing_user = db.query(User).filter(
                User.username == user_data["username"]
            ).first()

            if existing_user:
                print(
                    f"⚠️  User {user_data['username']} already exists, skipping...")
                continue

            # Create user
            hashed_password = get_password_hash(user_data["password"])
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=hashed_password,
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                is_staff=user_data.get("is_staff", False),
                is_superuser=user_data.get("is_superuser", False),
                is_active=True,
                date_joined=datetime.utcnow()
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            # Assign roles
            for role_name in user_data["roles"]:
                role = roles.get(role_name)
                if role:
                    user_role = UserRole(
                        user_id=user.id,
                        role_id=role.id
                    )
                    db.add(user_role)

            db.commit()
            created_users.append(user)
            print(f"✅ Created user: {user.username} ({user.email})")

        print(f"\n🎉 Successfully created {len(created_users)} test users!")

        # Print user credentials
        print("\n📋 Test User Credentials:")
        print("=" * 50)
        for user in created_users:
            print(f"Username: {user.username}")
            print(f"Email: {user.email}")
            print(
                f"Password: {next(u['password'] for u in test_users if u['username'] == user.username)}")
            print(f"Roles: {', '.join([r.role.name for r in user.roles])}")
            print("-" * 30)

        print("\n🔑 Admin Account:")
        print("Username: admin")
        print("Email: admin@a.com")
        print("Password: admin")
        print("Role: admin (full access)")

        db.close()
        return True

    except Exception as e:
        print(f"❌ Error creating test users: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_sample_data():
    """Create sample conversations and messages"""
    try:
        print("\n💬 Creating sample conversations and messages...")

        # Import all models to ensure relationships are properly configured
        from database.connection import get_db
        from models.user import User
        from models.role import Role, UserRole
        from models.permission import Permission
        from models.notification import Notification, NotificationPreference
        from models.conversation import Conversation, ConversationParticipant
        from models.message import Message, MessageReaction
        from models.user_block import UserBlock

        db = next(get_db())

        # Get some users
        admin = db.query(User).filter(User.username == "admin").first()
        john = db.query(User).filter(User.username == "john_doe").first()
        jane = db.query(User).filter(User.username == "jane_smith").first()

        if not all([admin, john, jane]):
            print("⚠️  Some users not found, skipping sample data creation")
            return True

        # Create a group conversation
        group_conv = Conversation(
            name="Test Group Chat",
            conversation_type="group",
            conversation_metadata={"description": "A test group conversation"}
        )
        db.add(group_conv)
        db.commit()
        db.refresh(group_conv)

        # Add participants
        participants = [
            ConversationParticipant(
                conversation_id=group_conv.id, user_id=admin.id, is_admin=True),
            ConversationParticipant(
                conversation_id=group_conv.id, user_id=john.id),
            ConversationParticipant(
                conversation_id=group_conv.id, user_id=jane.id)
        ]
        db.add_all(participants)

        # Create some messages
        messages = [
            Message(
                conversation_id=group_conv.id,
                sender_id=admin.id,
                content="Welcome to the test group chat! 👋",
                message_type="text"
            ),
            Message(
                conversation_id=group_conv.id,
                sender_id=john.id,
                content="Hello everyone! 👋",
                message_type="text"
            ),
            Message(
                conversation_id=group_conv.id,
                sender_id=jane.id,
                content="Hi there! Nice to meet you all 😊",
                message_type="text"
            ),
            Message(
                conversation_id=group_conv.id,
                sender_id=admin.id,
                content="This is a test conversation for the FastAPI backend.",
                message_type="text"
            )
        ]
        db.add_all(messages)

        # Create a direct conversation between admin and john
        direct_conv = Conversation(
            conversation_type="direct"
        )
        db.add(direct_conv)
        db.commit()
        db.refresh(direct_conv)

        # Add participants to direct conversation
        direct_participants = [
            ConversationParticipant(
                conversation_id=direct_conv.id, user_id=admin.id),
            ConversationParticipant(
                conversation_id=direct_conv.id, user_id=john.id)
        ]
        db.add_all(direct_participants)

        # Add a message to direct conversation
        direct_message = Message(
            conversation_id=direct_conv.id,
            sender_id=admin.id,
            content="This is a private message between admin and john.",
            message_type="text"
        )
        db.add(direct_message)

        db.commit()

        print("✅ Sample conversations and messages created!")
        print(f"   - Group conversation: {group_conv.name}")
        print(f"   - Direct conversation between admin and john")
        print(f"   - Total messages: {len(messages) + 1}")

        db.close()
        return True

    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        return False


def main():
    """Main setup function"""
    print("🚀 Setting up FastAPI Backend - Complete Setup")
    print("=" * 60)

    # Step 1: Setup database
    if not setup_database():
        print("❌ Database setup failed!")
        sys.exit(1)

    # Step 2: Create test users
    if not create_test_users():
        print("❌ User creation failed!")
        sys.exit(1)

    # Step 3: Create sample data
    create_sample_data()

    print("\n🎉 Setup complete! Your FastAPI backend is ready!")
    print("\n📝 Next steps:")
    print("1. Start the server: python main.py")
    print("2. Visit: http://127.0.0.1:8000/docs")
    print("3. Test login with admin@a.com / admin")
    print("4. Explore the API endpoints")
    print("\n🔑 Quick Login:")
    print("   Email: admin@a.com")
    print("   Password: admin")


if __name__ == "__main__":
    main()
