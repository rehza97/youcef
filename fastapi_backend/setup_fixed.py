#!/usr/bin/env python3
"""
Fixed setup script for FastAPI Backend
Handles model imports and session management properly
"""

import sys


def setup_database():
    """Set up the database schema"""
    try:
        print("🗄️  Setting up database schema...")

        # Import database connection first
        from database.connection import Base, engine

        # Import all models in the correct order to avoid relationship issues
        print("📦 Importing models...")

        # Core models first
        from models.permission import Permission
        from models.role import Role, UserRole, RolePermission
        from models.user import User
        from models.user_block import UserBlock

        # Feature models
        from models.notification import Notification, NotificationPreference
        from models.conversation import Conversation, ConversationParticipant
        from models.message import Message, MessageReaction

        # Configure all mappers
        from sqlalchemy.orm import configure_mappers
        configure_mappers()

        print("✅ Models imported and configured")

        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database schema created successfully")
        return True

    except Exception as e:
        print(f"❌ Error creating schema: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_admin_user():
    """Create admin user with proper session management"""
    try:
        print("\n👤 Creating admin user...")

        from database.connection import get_db
        from models.user import User
        from models.role import Role, UserRole
        from core.security import get_password_hash
        from datetime import datetime

        db = next(get_db())

        try:
            # Create admin role (or get existing)
            print("🔧 Creating admin role...")
            admin_role = db.query(Role).filter(Role.name == "admin").first()
            if not admin_role:
                admin_role = Role(
                    name="admin", description="Administrator with full access")
                db.add(admin_role)
                db.commit()
                db.refresh(admin_role)
                print("✅ Admin role created")
            else:
                print("✅ Admin role already exists")

                # Create admin user (or get existing)
            print("🔧 Creating admin user...")
            admin_user = db.query(User).filter(
                User.username == "admin").first()
            if not admin_user:
                hashed_password = get_password_hash("admin")
                admin_user = User(
                    username="admin",
                    email="admin@a.com",
                    hashed_password=hashed_password,
                    first_name="Admin",
                    last_name="User",
                    is_staff=True,
                    is_superuser=True,
                    is_active=True,
                    date_joined=datetime.utcnow()
                )

                db.add(admin_user)
                db.commit()
                db.refresh(admin_user)
                print("✅ Admin user created")
            else:
                print("✅ Admin user already exists")

            # Assign admin role (check if already assigned)
            print("🔧 Assigning admin role...")
            existing_role = db.query(UserRole).filter(
                UserRole.user_id == admin_user.id,
                UserRole.role_id == admin_role.id
            ).first()

            if not existing_role:
                user_role = UserRole(user_id=admin_user.id,
                                     role_id=admin_role.id)
                db.add(user_role)
                db.commit()
                print("✅ Admin role assigned")
            else:
                print("✅ Admin role already assigned")

            print("\n🔑 Admin Account Created:")
            print("   Username: admin")
            print("   Email: admin@a.com")
            print("   Password: admin")
            print("   Role: admin (full access)")

            return True

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_test_users():
    """Create additional test users"""
    try:
        print("\n👥 Creating additional test users...")

        from database.connection import get_db
        from models.user import User
        from models.role import Role, UserRole
        from core.security import get_password_hash
        from datetime import datetime

        db = next(get_db())

        try:
            # Get or create roles
            roles = {}
            for role_name in ["user", "moderator"]:
                role = db.query(Role).filter(Role.name == role_name).first()
                if not role:
                    role = Role(name=role_name,
                                description=f"{role_name.title()} role")
                    db.add(role)
                    db.commit()
                    db.refresh(role)
                roles[role_name] = role

            # Create test users
            test_users = [
                {
                    "username": "john_doe",
                    "email": "john@example.com",
                    "password": "password123",
                    "first_name": "John",
                    "last_name": "Doe",
                    "role": "user"
                },
                {
                    "username": "jane_smith",
                    "email": "jane@example.com",
                    "password": "password123",
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "role": "user"
                },
                {
                    "username": "moderator",
                    "email": "mod@example.com",
                    "password": "mod123",
                    "first_name": "Moderator",
                    "last_name": "User",
                    "role": "moderator"
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
                    is_active=True,
                    date_joined=datetime.utcnow()
                )

                db.add(user)
                db.commit()
                db.refresh(user)

                # Assign role
                role = roles.get(user_data["role"])
                if role:
                    user_role = UserRole(user_id=user.id, role_id=role.id)
                    db.add(user_role)
                    db.commit()

                created_users.append(user)
                print(f"✅ Created user: {user.username} ({user.email})")

            print(
                f"\n🎉 Successfully created {len(created_users)} additional test users!")

            # Print credentials
            print("\n📋 Test User Credentials:")
            print("=" * 50)
            for user in created_users:
                password = next(u['password']
                                for u in test_users if u['username'] == user.username)
                print(f"Username: {user.username}")
                print(f"Email: {user.email}")
                print(f"Password: {password}")
                print("-" * 30)

            return True

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    except Exception as e:
        print(f"❌ Error creating test users: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main setup function"""
    print("🚀 Setting up FastAPI Backend - Fixed Setup")
    print("=" * 60)

    # Step 1: Setup database
    if not setup_database():
        print("❌ Database setup failed!")
        sys.exit(1)

    # Step 2: Create admin user
    if not create_admin_user():
        print("❌ Admin user creation failed!")
        sys.exit(1)

    # Step 3: Create additional test users
    create_test_users()

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
