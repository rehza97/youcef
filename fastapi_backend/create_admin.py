#!/usr/bin/env python3
"""
Create admin user using raw SQL
"""
import logging
from sqlalchemy import text
from core.security import get_password_hash
from database.connection import engine
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_admin_user():
    """Create admin user using raw SQL"""
    try:
        # Get password hash
        hashed_password = get_password_hash("admin123")

        # Create connection
        with engine.connect() as conn:
            # Check if admin user exists
            result = conn.execute(
                text("SELECT id, username FROM users WHERE username = 'admin'"))
            admin_user = result.fetchone()

            if admin_user:
                logger.info(
                    f"✅ Admin user already exists (ID: {admin_user[0]})")
            else:
                # Create admin user
                conn.execute(text("""
                    INSERT INTO users (username, email, hashed_password, is_active, is_superuser, date_joined)
                    VALUES ('admin', 'admin@example.com', :password, true, true, NOW())
                """), {"password": hashed_password})

                conn.commit()
                logger.info("✅ Admin user created successfully")

            # List all users
            result = conn.execute(
                text("SELECT id, username, email, is_active FROM users"))
            users = result.fetchall()

            logger.info(f"\n📋 All users in database:")
            for user in users:
                logger.info(
                    f"- ID: {user[0]}, Username: {user[1]}, Email: {user[2]}, Active: {user[3]}")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    create_admin_user()
