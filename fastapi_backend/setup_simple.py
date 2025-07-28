#!/usr/bin/env python3
"""
Simplified setup script for FastAPI Backend
"""

import sys


def setup_database():
    """Set up the database schema"""
    try:
        print("🗄️  Setting up database schema...")

        # Import all models first to ensure relationships are configured
        from database.connection import Base, engine
        from models.user import User
        from models.role import Role, UserRole, RolePermission
        from models.permission import Permission
        from models.notification import Notification, NotificationPreference
        from models.conversation import Conversation, ConversationParticipant
        from models.message import Message, MessageReaction
        from models.user_block import UserBlock

        # Configure mappers
        from sqlalchemy.orm import configure_mappers
        configure_mappers()

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
    """Create just the admin user"""
    try:
        print("\n👤 Creating admin user...")

        from database.connection import get_db
        from models.user import User
        from models.role import Role, UserRole
        from core.security import get_password_hash
        from datetime import datetime

        db = next(get_db())

        # Create admin role
        admin_role = Role(
            name="admin", description="Administrator with full access")
        existing_role = db.query(Role).filter(Role.name == "admin").first()
        if not existing_role:
            db.add(admin_role)
            db.commit()
            db.refresh(admin_role)
        else:
            admin_role = existing_role

        print("✅ Admin role created/verified")

        # Create admin user
        existing_user = db.query(User).filter(User.username == "admin").first()
        if existing_user:
            print("⚠️  Admin user already exists")
            return True

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

        # Assign admin role
        user_role = UserRole(user_id=admin_user.id, role_id=admin_role.id)
        db.add(user_role)
        db.commit()

        print("✅ Admin user created successfully")
        print("\n🔑 Admin Account:")
        print("   Username: admin")
        print("   Email: admin@a.com")
        print("   Password: admin")

        db.close()
        return True

    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main setup function"""
    print("🚀 Setting up FastAPI Backend - Simple Setup")
    print("=" * 50)

    # Step 1: Setup database
    if not setup_database():
        print("❌ Database setup failed!")
        sys.exit(1)

    # Step 2: Create admin user
    if not create_admin_user():
        print("❌ Admin user creation failed!")
        sys.exit(1)

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
