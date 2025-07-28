#!/usr/bin/env python3
"""
Script to check database for users
"""

import asyncio
from sqlalchemy.orm import Session
from database.connection import get_db, init_db
from models.user import User
from core.security import get_password_hash, verify_password
from datetime import datetime


def check_database_users():
    """Check what users exist in the database"""

    # Initialize database
    try:
        asyncio.run(init_db())
    except Exception as e:
        print(f"⚠️  Database initialization warning: {e}")

    # Get database session
    db = next(get_db())

    try:
        print("🔍 Checking database for users...")

        # Count total users
        total_users = db.query(User).count()
        print(f"📊 Total users in database: {total_users}")

        if total_users == 0:
            print("❌ No users found in database!")
            print("💡 Creating admin user...")

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

            print("✅ Admin user created!")
            print(f"   Username: {admin_user.username}")
            print(f"   Email: {admin_user.email}")
            print(f"   Password: admin")
            print(f"   Is active: {admin_user.is_active}")

        else:
            print("\n👥 Users in database:")
            users = db.query(User).all()
            for user in users:
                print(
                    f"   - {user.username} ({user.email}) - Active: {user.is_active}")

                # Test password verification
                if user.username == "admin":
                    is_valid = verify_password("admin", user.hashed_password)
                    print(
                        f"     Password verification: {'✅ Valid' if is_valid else '❌ Invalid'}")

        # Test specific user lookup
        print("\n🔍 Testing user lookup...")
        admin_user = db.query(User).filter(User.username == "admin").first()

        if admin_user:
            print(f"✅ Found admin user: {admin_user.username}")
            print(f"   Email: {admin_user.email}")
            print(f"   Is active: {admin_user.is_active}")
            print(
                f"   Hashed password length: {len(admin_user.hashed_password)}")

            # Test password verification
            is_valid = verify_password("admin", admin_user.hashed_password)
            print(
                f"   Password verification: {'✅ Valid' if is_valid else '❌ Invalid'}")

        else:
            print("❌ Admin user not found!")

        return True

    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    print("🔧 Database User Check")
    print("=" * 50)

    success = check_database_users()

    if success:
        print("\n🎉 Database check complete!")
        print("\n📝 You can now test login with:")
        print("   Username: admin")
        print("   Password: admin")
        print("   Email: admin@a.com")
    else:
        print("\n❌ Database check failed!")
