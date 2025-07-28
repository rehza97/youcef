#!/usr/bin/env python3
"""
Script to create test users for the FastAPI backend
"""

import asyncio
from sqlalchemy.orm import Session
from database.connection import get_db, init_db
from models.user import User
from models.role import Role, UserRole
from models.permission import Permission
from core.security import get_password_hash
from datetime import datetime, timezone

# Import all models to ensure they are registered
from models.notification import Notification
from models.user_block import UserBlock
from models.file_upload import FileUpload, FilePreview


def create_test_users():
    """Create test users with roles and permissions"""

    # Initialize database - handle async function
    import asyncio
    try:
        asyncio.run(init_db())
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")
        # Continue anyway as the database might already be initialized

    # Get database session
    db = next(get_db())

    try:
        print("🔧 Creating test users...")

        # Check for existing roles and create if they don't exist
        existing_roles = db.query(Role).all()
        role_map = {role.name: role for role in existing_roles}

        roles_to_create = []

        if "admin" not in role_map:
            admin_role = Role(
                name="admin", description="Administrator with full access")
            roles_to_create.append(admin_role)
        else:
            admin_role = role_map["admin"]

        if "user" not in role_map:
            user_role = Role(name="user", description="Regular user")
            roles_to_create.append(user_role)
        else:
            user_role = role_map["user"]

        if "moderator" not in role_map:
            moderator_role = Role(
                name="moderator", description="Moderator with limited admin access")
            roles_to_create.append(moderator_role)
        else:
            moderator_role = role_map["moderator"]

        if roles_to_create:
            db.add_all(roles_to_create)
            db.commit()
            print(f"✅ Created {len(roles_to_create)} new roles")
        else:
            print("✅ All required roles already exist")

        # Refresh roles to get their IDs
        db.refresh(admin_role)
        db.refresh(user_role)
        db.refresh(moderator_role)

        # Check for existing permissions and create if they don't exist
        existing_permissions = db.query(Permission).all()
        permission_map = {perm.codename: perm for perm in existing_permissions}

        permissions_to_create = []
        required_permissions = [
            {"name": "user_management", "codename": "user_management",
                "description": "Manage users"},
            {"name": "role_management", "codename": "role_management",
                "description": "Manage roles"},
            {"name": "message_send", "codename": "message_send",
                "description": "Send messages"},
            {"name": "message_read", "codename": "message_read",
                "description": "Read messages"},
            {"name": "notification_manage", "codename": "notification_manage",
                "description": "Manage notifications"},
            {"name": "conversation_create", "codename": "conversation_create",
                "description": "Create conversations"},
            {"name": "conversation_join", "codename": "conversation_join",
                "description": "Join conversations"},
            {"name": "user_block", "codename": "user_block",
                "description": "Block users"},
            {"name": "system_admin", "codename": "system_admin",
                "description": "System administration"}
        ]

        for perm_data in required_permissions:
            if perm_data["codename"] not in permission_map:
                permission = Permission(**perm_data)
                permissions_to_create.append(permission)

        if permissions_to_create:
            db.add_all(permissions_to_create)
            db.commit()
            print(f"✅ Created {len(permissions_to_create)} new permissions")
        else:
            print("✅ All required permissions already exist")

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
            # Check if user already exists by username or email
            existing_user = db.query(User).filter(
                (User.username == user_data["username"]) |
                (User.email == user_data["email"])
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
                date_joined=datetime.now(timezone.utc)
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            # Assign roles
            for role_name in user_data["roles"]:
                role = db.query(Role).filter(Role.name == role_name).first()
                if role:
                    # Check if user-role relationship already exists
                    existing_user_role = db.query(UserRole).filter(
                        UserRole.user_id == user.id,
                        UserRole.role_id == role.id
                    ).first()

                    if not existing_user_role:
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

        print("\n🚀 You can now test the API with these accounts!")
        print("Try logging in at: http://127.0.0.1:8000/docs")

        return True

    except Exception as e:
        print(f"❌ Error creating test users: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False

    finally:
        db.close()


def create_sample_data():
    """Create sample conversations and messages for testing"""

    db = next(get_db())

    try:
        print("\n💬 Creating sample conversations and messages...")

        # Get some users
        admin = db.query(User).filter(User.username == "admin").first()
        john = db.query(User).filter(User.username == "john_doe").first()
        jane = db.query(User).filter(User.username == "jane_smith").first()

        if not all([admin, john, jane]):
            print("⚠️  Some users not found, skipping sample data creation")
            return

        from models.conversation import Conversation, ConversationParticipant
        from models.message import Message

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

    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    print("🚀 Setting up test users for FastAPI Backend")
    print("=" * 50)

    # Create test users
    success = create_test_users()

    if success:
        # Create sample data
        create_sample_data()

        print("\n🎉 Setup complete! Your test environment is ready.")
        print("\n📝 Next steps:")
        print("1. Start the FastAPI server: python main.py")
        print("2. Visit: http://127.0.0.1:8000/docs")
        print("3. Test login with admin@a.com / admin")
        print("4. Explore the API endpoints")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        exit(1)
