#!/usr/bin/env python3
"""
Comprehensive script to fix sequences and create additional test users
"""

import psycopg2
import logging
from sqlalchemy.orm import Session
from database.connection import get_db
from models.user import User
from models.role import Role, UserRole
from core.security import get_password_hash
from datetime import datetime, timezone

# Import all models to ensure they are registered
from models.notification import Notification
from models.user_block import UserBlock
from models.file_upload import FileUpload, FilePreview

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_sequences():
    """Fix PostgreSQL sequences to match existing data"""

    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='youcef_db',
            user='postgres',
            password='123456789'
        )

        cursor = conn.cursor()

        # Get all tables with sequences
        cursor.execute("""
            SELECT table_name, column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND column_default LIKE 'nextval%'
            ORDER BY table_name, ordinal_position
        """)

        sequences = cursor.fetchall()
        logger.info(f"Found {len(sequences)} sequences to fix")

        for table_name, column_name in sequences:
            try:
                # Get the maximum ID for this table
                cursor.execute(f"SELECT MAX({column_name}) FROM {table_name}")
                max_id = cursor.fetchone()[0]

                if max_id is not None:
                    # Reset the sequence to the maximum ID + 1
                    sequence_name = f"{table_name}_{column_name}_seq"
                    cursor.execute(
                        f"SELECT setval('{sequence_name}', {max_id + 1}, false)")
                    logger.info(
                        f"Fixed sequence for {table_name}.{column_name} to {max_id + 1}")
                else:
                    logger.info(
                        f"Table {table_name} is empty, setting sequence to 1")
                    sequence_name = f"{table_name}_{column_name}_seq"
                    cursor.execute(
                        f"SELECT setval('{sequence_name}', 1, false)")

            except Exception as e:
                logger.warning(
                    f"Could not fix sequence for {table_name}.{column_name}: {e}")

        conn.commit()
        cursor.close()
        conn.close()

        logger.info("✅ All sequences fixed successfully!")
        return True

    except Exception as e:
        logger.error(f"Error fixing sequences: {e}")
        import traceback
        traceback.print_exc()
        return False


def create_additional_users():
    """Create additional test users that don't exist yet"""

    db = next(get_db())

    try:
        logger.info("🔧 Creating additional test users...")

        # Get existing users to avoid duplicates
        existing_users = db.query(User).all()
        existing_usernames = {user.username for user in existing_users}
        existing_emails = {user.email for user in existing_users}

        # Additional users to create
        additional_users = [
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
            },
            {
                "username": "support",
                "email": "support@example.com",
                "password": "support123",
                "first_name": "Support",
                "last_name": "Agent",
                "is_staff": True,
                "roles": ["moderator"]
            }
        ]

        created_users = []

        for user_data in additional_users:
            # Skip if user already exists
            if user_data["username"] in existing_usernames or user_data["email"] in existing_emails:
                logger.info(
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
                    user_role = UserRole(
                        user_id=user.id,
                        role_id=role.id
                    )
                    db.add(user_role)

            db.commit()
            created_users.append(user)
            logger.info(f"✅ Created user: {user.username} ({user.email})")

        logger.info(
            f"\n🎉 Successfully created {len(created_users)} additional users!")

        # Print credentials for new users
        if created_users:
            print("\n📋 New User Credentials:")
            print("=" * 50)
            for user in created_users:
                user_data = next(
                    u for u in additional_users if u["username"] == user.username)
                print(f"Username: {user.username}")
                print(f"Email: {user.email}")
                print(f"Password: {user_data['password']}")
                print(f"Roles: {', '.join(user_data['roles'])}")
                print("-" * 30)

        return True

    except Exception as e:
        logger.error(f"❌ Error creating additional users: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False

    finally:
        db.close()


def main():
    """Main function to fix sequences and create users"""

    print("🚀 Fixing sequences and creating additional test users")
    print("=" * 60)

    # Step 1: Fix sequences
    print("\n🔧 Step 1: Fixing PostgreSQL sequences...")
    if fix_sequences():
        print("✅ Sequences fixed successfully!")
    else:
        print("❌ Failed to fix sequences")
        return

    # Step 2: Create additional users
    print("\n👥 Step 2: Creating additional test users...")
    if create_additional_users():
        print("✅ Additional users created successfully!")
    else:
        print("❌ Failed to create additional users")
        return

    print("\n🎉 All operations completed successfully!")
    print("\n📝 Next steps:")
    print("1. Start the FastAPI server: python main.py")
    print("2. Visit: http://127.0.0.1:8000/docs")
    print("3. Test login with any of the created accounts")
    print("4. Explore the API endpoints")


if __name__ == "__main__":
    main()
