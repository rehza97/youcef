#!/usr/bin/env python3
"""
Script to check and fix test users in the database
"""

import asyncio
from sqlalchemy.orm import Session
from database.connection import get_db, init_db
from models.user import User
from core.security import get_password_hash
from datetime import datetime


def check_and_fix_users():
    """Check if test users exist and create them if needed"""

    # Initialize database
    try:
        asyncio.run(init_db())
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")

    # Get database session
    db = next(get_db())

    try:
        print("🔍 Checking for test users...")

        # Check if admin user exists
        admin_user = db.query(User).filter(User.username == "admin").first()

        if not admin_user:
            print("❌ Admin user not found. Creating test users...")

            # Create admin user
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

            print("✅ Admin user created successfully!")
            print(f"   Username: admin")
            print(f"   Email: admin@a.com")
            print(f"   Password: admin")
        else:
            print("✅ Admin user already exists!")
            print(f"   Username: {admin_user.username}")
            print(f"   Email: {admin_user.email}")
            print(f"   Is active: {admin_user.is_active}")

        # Check total users
        total_users = db.query(User).count()
        print(f"\n📊 Total users in database: {total_users}")

        # List all users
        print("\n👥 All users in database:")
        users = db.query(User).all()
        for user in users:
            print(
                f"   - {user.username} ({user.email}) - Active: {user.is_active}")

        return True

    except Exception as e:
        print(f"❌ Error checking users: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    print("🔧 Checking and fixing test users...")
    print("=" * 50)

    success = check_and_fix_users()

    if success:
        print("\n🎉 User check complete!")
        print("\n📝 You can now test login with:")
        print("   Username: admin")
        print("   Password: admin")
        print("   Email: admin@a.com")
    else:
        print("\n❌ User check failed!")
