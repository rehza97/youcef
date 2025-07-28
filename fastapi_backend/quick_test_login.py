#!/usr/bin/env python3
"""
Quick test for login functionality
"""

import requests
import json
import asyncio
from database.connection import init_db
from models.user import User
from core.security import get_password_hash
from datetime import datetime


def setup_test_user():
    """Ensure test user exists"""
    try:
        asyncio.run(init_db())
        from sqlalchemy.orm import Session
        from database.connection import get_db

        db = next(get_db())

        # Check if admin user exists
        admin_user = db.query(User).filter(User.username == "admin").first()

        if not admin_user:
            print("Creating admin user...")
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
            print("✅ Admin user created")
        else:
            print("✅ Admin user already exists")

        db.close()
        return True
    except Exception as e:
        print(f"❌ Error setting up test user: {e}")
        return False


def test_login():
    """Test login endpoint"""
    login_data = {
        "username": "admin",
        "password": "admin"
    }

    try:
        print("🔐 Testing login...")
        response = requests.post(
            "http://127.0.0.1:8000/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Login successful!")
            print(f"Access token: {result.get('access_token', 'N/A')[:20]}...")
            print(f"User: {result.get('user', {}).get('username', 'N/A')}")
            return True
        else:
            print("❌ Login failed!")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Quick Login Test")
    print("=" * 30)

    # Setup test user
    if setup_test_user():
        # Test login
        test_login()
    else:
        print("❌ Failed to setup test user")
