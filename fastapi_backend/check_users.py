#!/usr/bin/env python3
"""
Check and create test users
"""
import logging
from core.security import get_password_hash
from models.user import User
from sqlalchemy.orm import sessionmaker
from database.connection import engine, Base
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_and_create_users():
    """Check existing users and create test user if needed"""
    try:
        # Create tables if they don't exist
        Base.metadata.create_all(bind=engine)

        # Create session
        SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()

        # Check existing users
        users = db.query(User).all()
        logger.info(f"Found {len(users)} existing users:")

        for user in users:
            logger.info(
                f"- ID: {user.id}, Username: {user.username}, Email: {user.email}")

        # Check if admin user exists
        admin_user = db.query(User).filter(User.username == "admin").first()

        if not admin_user:
            logger.info("Creating admin user...")

            # Create admin user
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                is_superuser=True
            )

            db.add(admin_user)
            db.commit()
            logger.info("✅ Admin user created successfully")
        else:
            logger.info("✅ Admin user already exists")

        # Check if test user exists
        test_user = db.query(User).filter(User.username == "test").first()

        if not test_user:
            logger.info("Creating test user...")

            # Create test user
            test_user = User(
                username="test",
                email="test@example.com",
                hashed_password=get_password_hash("test123"),
                is_active=True,
                is_superuser=False
            )

            db.add(test_user)
            db.commit()
            logger.info("✅ Test user created successfully")
        else:
            logger.info("✅ Test user already exists")

        # List all users
        all_users = db.query(User).all()
        logger.info(f"\n📋 All users in database:")
        for user in all_users:
            logger.info(
                f"- ID: {user.id}, Username: {user.username}, Email: {user.email}, Active: {user.is_active}")

        db.close()

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    check_and_create_users()
