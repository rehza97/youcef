#!/usr/bin/env python3
"""
Enable notifications for all users
"""
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from models.notification import NotificationPreference
from database.connection import engine
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def enable_notifications_for_all_users():
    """Enable notifications for all users"""
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Get all user IDs
        result = db.execute(text("SELECT id FROM users"))
        user_ids = [row[0] for row in result]

        for user_id in user_ids:
            # Check if user has notification preferences
            preference = db.query(NotificationPreference).filter(
                NotificationPreference.user_id == user_id
            ).first()

            if not preference:
                # Create notification preferences
                preference = NotificationPreference(
                    user_id=user_id,
                    in_app_notifications=True,
                    email_notifications=False,
                    push_notifications=False
                )
                db.add(preference)
                print(f"✅ Created notification preferences for user {user_id}")
            else:
                # Enable in-app notifications
                preference.in_app_notifications = True
                print(f"✅ Enabled notifications for user {user_id}")

        db.commit()
        print(f"✅ Notification preferences updated for {len(user_ids)} users")

    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🔔 Enabling notifications for all users...")
    enable_notifications_for_all_users()
    print("✅ Done!")
