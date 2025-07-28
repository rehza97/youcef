#!/usr/bin/env python3
"""
Test script to verify FastAPI backend setup
"""

import requests
import json


def test_health_endpoint():
    """Test the health endpoint"""
    try:
        print("🏥 Testing health endpoint...")
        response = requests.get("http://127.0.0.1:8000/health")
        if response.status_code == 200:
            print("✅ Health endpoint working")
            return True
        else:
            print(f"❌ Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")
        return False


def test_login():
    """Test login with admin credentials"""
    try:
        print("🔐 Testing login...")

        login_data = {
            "username": "admin@a.com",  # Can be username or email
            "password": "admin"
        }

        response = requests.post(
            "http://127.0.0.1:8000/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            data = response.json()
            print("✅ Login successful!")
            print(
                f"   Access token: {data.get('access_token', 'N/A')[:20]}...")
            print(f"   Token type: {data.get('token_type', 'N/A')}")
            return True
        else:
            print(f"❌ Login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Login error: {e}")
        return False


def test_protected_endpoint():
    """Test accessing a protected endpoint"""
    try:
        print("🔒 Testing protected endpoint...")

        # First login to get token
        login_data = {
            "username": "admin@a.com",
            "password": "admin"
        }

        response = requests.post(
            "http://127.0.0.1:8000/api/auth/login",
            json=login_data
        )

        if response.status_code != 200:
            print("❌ Login failed for protected endpoint test")
            return False

        token = response.json().get("access_token")

        # Test protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            "http://127.0.0.1:8000/api/auth/protected",
            headers=headers
        )

        if response.status_code == 200:
            print("✅ Protected endpoint working")
            return True
        else:
            print(f"❌ Protected endpoint failed: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Protected endpoint error: {e}")
        return False


def main():
    """Main test function"""
    print("🧪 Testing FastAPI Backend Setup")
    print("=" * 50)

    # Check if server is running
    print("🔍 Checking if server is running...")
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        print("✅ Server is running!")
    except:
        print("❌ Server is not running!")
        print("Please start the server with: python main.py")
        return

    # Run tests
    tests = [
        test_health_endpoint,
        test_login,
        test_protected_endpoint
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("📊 Test Results:")
    print(f"   Passed: {passed}/{total}")
    print(f"   Failed: {total - passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! Setup is working correctly.")
        print("\n📝 Next steps:")
        print("1. Visit: http://127.0.0.1:8000/docs")
        print("2. Explore the API endpoints")
        print("3. Test with other users (john@example.com / password123)")
    else:
        print("❌ Some tests failed. Please check the setup.")


if __name__ == "__main__":
    main()
