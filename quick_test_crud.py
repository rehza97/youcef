#!/usr/bin/env python3
"""
Quick CRUD Test Script
Tests basic endpoint accessibility
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
            print("✅ Backend is running!")
            return True
        else:
            print("❌ Backend health check failed")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def test_endpoints():
    """Test basic endpoint accessibility"""
    endpoints = [
        "/api/users/",
        "/api/users/roles/",
        "/api/users/permissions/",
        "/api/notifications/",
        "/api/messaging/conversations",
        "/api/files/"
    ]

    print("\n🔍 Testing endpoint accessibility:")
    print("-" * 50)

    for endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            status = "✅" if response.status_code in [200, 401, 403] else "❌"
            print(f"{status} {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint}: Connection error")


def main():
    print("🚀 Quick CRUD Test")
    print("=" * 50)

    # Test health first
    if not test_health():
        print("❌ Backend is not running. Please start the server first.")
        return

    # Test endpoints
    test_endpoints()

    print("\n✅ Quick test completed!")
    print("Note: 401/403 responses are expected without authentication")


if __name__ == "__main__":
    main()
