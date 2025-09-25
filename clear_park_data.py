#!/usr/bin/env python3
"""
Script to clear all park data from the database
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


def login():
    """Login and get authentication token"""
    login_data = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login", json=login_data, headers=headers)
        response.raise_for_status()

        token_data = response.json()
        return token_data.get("access_token")

    except requests.exceptions.RequestException as e:
        print(f"❌ Login failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None


def clear_park_data(token):
    """Clear all park data"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        print("🗑️  Clearing all park data...")
        response = requests.delete(
            f"{BASE_URL}/api/parks/data/clear-all", headers=headers)
        response.raise_for_status()

        result = response.json()
        print(f"✅ {result['message']}")
        print(
            f"📊 Deleted {result['deleted_count']} records out of {result['total_count']} total")

        return True

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to clear park data: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return False


def main():
    """Main function"""
    print("🚀 Park Data Clearer")
    print("=" * 50)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Login
    print("🔐 Logging in...")
    token = login()
    if not token:
        print("❌ Failed to login. Exiting.")
        sys.exit(1)

    print("✅ Login successful")
    print()

    # Confirm action
    print("⚠️  WARNING: This will delete ALL park data from the database!")
    confirm = input(
        "Are you sure you want to continue? (yes/no): ").lower().strip()

    if confirm not in ['yes', 'y']:
        print("❌ Operation cancelled by user.")
        sys.exit(0)

    # Clear data
    success = clear_park_data(token)

    if success:
        print()
        print("🎉 Park data cleared successfully!")
        print(
            f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print()
        print("❌ Failed to clear park data.")
        sys.exit(1)


if __name__ == "__main__":
    main()
