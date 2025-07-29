#!/usr/bin/env python3
"""
Check admin user password
"""
import logging
from sqlalchemy import text
from core.security import get_password_hash, verify_password
from database.connection import engine
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_admin_password():
    """Check admin user password"""
    try:
        # Create connection
        with engine.connect() as conn:
            # Get admin user
            result = conn.execute(text(
                "SELECT id, username, email, hashed_password FROM users WHERE username = 'admin'"))
            admin_user = result.fetchone()

            if admin_user:
                logger.info(f"✅ Admin user found:")
                logger.info(f"- ID: {admin_user[0]}")
                logger.info(f"- Username: {admin_user[1]}")
                logger.info(f"- Email: {admin_user[2]}")
                logger.info(f"- Password hash: {admin_user[3][:20]}...")

                # Test password verification
                test_password = "admin123"
                is_valid = verify_password(test_password, admin_user[3])
                logger.info(f"- Password 'admin123' valid: {is_valid}")

                # Generate new hash
                new_hash = get_password_hash("admin123")
                logger.info(f"- New hash for 'admin123': {new_hash[:20]}...")

                # Update password if needed
                if not is_valid:
                    logger.info("Updating admin password...")
                    conn.execute(text("""
                        UPDATE users 
                        SET hashed_password = :password 
                        WHERE username = 'admin'
                    """), {"password": new_hash})
                    conn.commit()
                    logger.info("✅ Admin password updated")
                else:
                    logger.info("✅ Admin password is correct")
            else:
                logger.error("❌ Admin user not found")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    check_admin_password()
