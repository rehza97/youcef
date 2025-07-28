#!/usr/bin/env python3
"""
Focused Admin Login Test Script
Tests admin login functionality specifically with detailed verification
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"


def test_admin_login_detailed():
    """Test admin login with detailed verification"""
    print("🔐 ADMIN LOGIN DETAILED TESTING")
    print("="*50)

    # Test 1: Valid admin login
    print("\n1️⃣ Testing Valid Admin Login")
    print("-" * 30)

    login_data = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )

        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Login successful!")
            print(f"Response: {json.dumps(result, indent=2)}")

            # Extract token
            token = result.get("access_token")
            if token:
                print(f"✅ Token obtained: {token[:50]}...")
                return token
            else:
                print("❌ No access_token in response")
                return None
        else:
            print(f"❌ Login failed with status {response.status_code}")
            print(f"Error: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None


def test_invalid_login_scenarios():
    """Test various invalid login scenarios"""
    print("\n2️⃣ Testing Invalid Login Scenarios")
    print("-" * 30)

    test_cases = [
        {
            "name": "Invalid Username",
            "data": {"username": "invalid_admin", "password": ADMIN_PASSWORD}
        },
        {
            "name": "Invalid Password",
            "data": {"username": ADMIN_USERNAME, "password": "wrong_password"}
        },
        {
            "name": "Empty Username",
            "data": {"username": "", "password": ADMIN_PASSWORD}
        },
        {
            "name": "Empty Password",
            "data": {"username": ADMIN_USERNAME, "password": ""}
        },
        {
            "name": "Missing Username",
            "data": {"password": ADMIN_PASSWORD}
        },
        {
            "name": "Missing Password",
            "data": {"username": ADMIN_USERNAME}
        },
        {
            "name": "Empty Request",
            "data": {}
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['name']}")
        try:
            response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json=test_case['data'],
                headers={"Content-Type": "application/json"}
            )

            print(f"   Status: {response.status_code}")
            if response.status_code != 200:
                print(f"   Expected failure: {response.text[:100]}...")
            else:
                print("   ⚠️ Unexpected success!")

        except Exception as e:
            print(f"   Error: {e}")


def test_protected_endpoint_with_token(token):
    """Test protected endpoint with the obtained token"""
    print("\n3️⃣ Testing Protected Endpoint with Admin Token")
    print("-" * 30)

    if not token:
        print("❌ No token available for testing")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            f"{BASE_URL}/api/auth/protected",
            headers=headers
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ Protected endpoint accessible!")
            print(f"Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ Protected endpoint failed: {response.text}")

    except Exception as e:
        print(f"❌ Request failed: {e}")


def test_user_profile_with_token(token):
    """Test user profile endpoint with admin token"""
    print("\n4️⃣ Testing User Profile with Admin Token")
    print("-" * 30)

    if not token:
        print("❌ No token available for testing")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            f"{BASE_URL}/api/users/me",
            headers=headers
        )

        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ User profile accessible!")
            print(f"User Data: {json.dumps(result, indent=2)}")

            # Verify it's the admin user
            username = result.get("username")
            if username == ADMIN_USERNAME:
                print("✅ Confirmed: Admin user profile retrieved")
            else:
                print(f"⚠️ Warning: Expected admin user, got {username}")
        else:
            print(f"❌ User profile failed: {response.text}")

    except Exception as e:
        print(f"❌ Request failed: {e}")


def main():
    """Main test execution"""
    print("🚀 ADMIN LOGIN COMPREHENSIVE TESTING")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # Test 1: Valid admin login
    token = test_admin_login_detailed()

    # Test 2: Invalid login scenarios
    test_invalid_login_scenarios()

    # Test 3: Protected endpoint with token
    if token:
        test_protected_endpoint_with_token(token)

        # Test 4: User profile with token
        test_user_profile_with_token(token)

    print("\n" + "="*60)
    print("🏁 ADMIN LOGIN TESTING COMPLETED")
    print(f"📅 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
