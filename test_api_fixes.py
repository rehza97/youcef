#!/usr/bin/env python3
"""
Test script to verify API endpoint fixes
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"


def test_health():
    """Test health endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Health check: {response.status_code}")
        if response.status_code == 200:
            print("✓ Health endpoint working")
        else:
            print("✗ Health endpoint failed")
    except Exception as e:
        print(f"✗ Health endpoint error: {e}")


def test_notifications_endpoints():
    """Test notifications endpoints"""
    print("\n--- Testing Notifications Endpoints ---")

    # Test notifications list
    try:
        response = requests.get(f"{BASE_URL}/api/notifications/")
        print(f"Notifications list: {response.status_code}")
        if response.status_code in [200, 401]:  # 401 is expected without auth
            print("✓ Notifications endpoint accessible")
        else:
            print("✗ Notifications endpoint failed")
    except Exception as e:
        print(f"✗ Notifications endpoint error: {e}")

    # Test notifications stats
    try:
        response = requests.get(f"{BASE_URL}/api/notifications/stats")
        print(f"Notifications stats: {response.status_code}")
        if response.status_code in [200, 401]:  # 401 is expected without auth
            print("✓ Notifications stats endpoint accessible")
        else:
            print("✗ Notifications stats endpoint failed")
    except Exception as e:
        print(f"✗ Notifications stats endpoint error: {e}")

    # Test notifications preferences
    try:
        response = requests.get(f"{BASE_URL}/api/notifications/preferences")
        print(f"Notifications preferences: {response.status_code}")
        if response.status_code in [200, 401]:  # 401 is expected without auth
            print("✓ Notifications preferences endpoint accessible")
        else:
            print("✗ Notifications preferences endpoint failed")
    except Exception as e:
        print(f"✗ Notifications preferences endpoint error: {e}")


def test_messaging_endpoints():
    """Test messaging endpoints"""
    print("\n--- Testing Messaging Endpoints ---")

    # Test conversations list
    try:
        response = requests.get(f"{BASE_URL}/api/messaging/conversations")
        print(f"Conversations list: {response.status_code}")
        if response.status_code in [200, 401]:  # 401 is expected without auth
            print("✓ Conversations endpoint accessible")
        else:
            print("✗ Conversations endpoint failed")
    except Exception as e:
        print(f"✗ Conversations endpoint error: {e}")

    # Test blocked users
    try:
        response = requests.get(f"{BASE_URL}/api/messaging/blocks")
        print(f"Blocked users: {response.status_code}")
        if response.status_code in [200, 401]:  # 401 is expected without auth
            print("✓ Blocked users endpoint accessible")
        else:
            print("✗ Blocked users endpoint failed")
    except Exception as e:
        print(f"✗ Blocked users endpoint error: {e}")


if __name__ == "__main__":
    print("Testing API Endpoints...")
    test_health()
    test_notifications_endpoints()
    test_messaging_endpoints()
    print("\nTest completed!")
