#!/usr/bin/env python3
"""
Quick test script to verify the auth token and test key endpoints
"""

import requests
import json


def test_token_validity():
    """Test if the provided token is valid"""
    print("🔑 Testing Token Validity")
    print("-" * 30)

    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOjEsImV4cCI6MTc1MzczMzA4MywidHlwZSI6ImFjY2VzcyJ9.EBg9H80bRoY1t4bBbD7uKD2BZ5ThTGnOFLLfraeWDqk"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    try:
        # Test protected endpoint
        response = requests.get(
            "http://127.0.0.1:8000/api/auth/protected", headers=headers)

        if response.status_code == 200:
            data = response.json()
            print("✅ Token is valid!")
            print(f"   User: {data.get('user', 'N/A')}")
            print(f"   Message: {data.get('message', 'N/A')}")
            return True
        else:
            print(f"❌ Token validation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error testing token: {e}")
        return False


def test_key_endpoints():
    """Test key endpoints with the token"""
    print("\n🎯 Testing Key Endpoints")
    print("-" * 30)

    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOjEsImV4cCI6MTc1MzczMzA4MywidHlwZSI6ImFjY2VzcyJ9.EBg9H80bRoY1t4bBbD7uKD2BZ5ThTGnOFLLfraeWDqk"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    endpoints = [
        ("GET", "/health", "Health Check"),
        ("GET", "/api/users/me", "Current User Profile"),
        ("GET", "/api/users/", "All Users"),
        ("GET", "/api/users/roles/", "All Roles"),
        ("GET", "/api/users/permissions/", "All Permissions"),
        ("GET", "/api/notifications/", "User Notifications"),
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


def test_login_endpoint():
    """Test login endpoint"""
    print("\n🔐 Testing Login Endpoint")
    print("-" * 30)

    login_data = {
        "username": "admin@a.com",
        "password": "admin"
    }

    try:
        response = requests.post(
            "http://127.0.0.1:8000/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(
                f"   Access token: {data.get('access_token', 'N/A')[:30]}...")
            print(f"   Token type: {data.get('token_type', 'N/A')}")
            return True
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Login error: {e}")
        return False


def main():
    """Main test function"""
    print("🚀 Quick FastAPI Endpoint Test")
    print("=" * 40)

    # Check if server is running
    print("🔍 Checking server connection...")
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running!")
        else:
            print(f"⚠️  Server responded with status: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Please start the server with: python main.py")
        return

    print()

    # Run tests
    test_login_endpoint()
    test_token_validity()
    test_key_endpoints()

    print("\n🎉 Quick test completed!")
    print("\n📝 Next steps:")
    print("1. Run comprehensive test: python test_all_endpoints.py")
    print("2. Visit API docs: http://127.0.0.1:8000/docs")
    print("3. Test with different users")


if __name__ == "__main__":
    main()
