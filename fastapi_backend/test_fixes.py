#!/usr/bin/env python3
"""
Quick test to verify endpoint fixes
"""

import requests
import json


def test_fixed_endpoints():
    """Test the fixed endpoints"""
    print("🧪 Testing Fixed Endpoints")
    print("=" * 40)

    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOjEsImV4cCI6MTc1MzczMzM2NSwidHlwZSI6ImFjY2VzcyJ9.SZ7Knjzv8Pd4brd5Xg6v_HLXZupyFh1sj4bux2V2dD8"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test key endpoints
    endpoints = [
        ("GET", "/health", "Health Check"),
        ("GET", "/api/auth/protected", "Protected Endpoint"),
        ("GET", "/api/users/me", "Current User Profile"),
        ("GET", "/api/users/", "All Users"),
        ("GET", "/api/users/roles/", "All Roles"),
        ("GET", "/api/users/permissions/", "All Permissions"),
        ("GET", "/api/notifications/", "User Notifications"),
        ("GET", "/api/notifications/preferences", "Notification Preferences"),
        ("GET", "/api/messaging/conversations", "User Conversations"),
    ]

    results = {"passed": 0, "failed": 0}

    for method, endpoint, description in endpoints:
        try:
            url = f"http://127.0.0.1:8000{endpoint}"
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                print(f"✅ {description} - {method} {endpoint}")
                results["passed"] += 1
            else:
                print(f"❌ {description} - {method} {endpoint}")
                print(f"   Status: {response.status_code}")
                print(f"   Response: {response.text[:100]}...")
                results["failed"] += 1

        except Exception as e:
            print(f"❌ {description} - {method} {endpoint}")
            print(f"   Error: {e}")
            results["failed"] += 1

    print(f"\n📊 Quick Test Results:")
    print(f"   ✅ Passed: {results['passed']}")
    print(f"   ❌ Failed: {results['failed']}")
    print(f"   📊 Total: {results['passed'] + results['failed']}")

    if results["failed"] == 0:
        print("🎉 All endpoints are working!")
    else:
        print("⚠️  Some endpoints still need fixing")


if __name__ == "__main__":
    test_fixed_endpoints()
