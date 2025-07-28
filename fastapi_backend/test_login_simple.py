#!/usr/bin/env python3
"""
Simple script to test login endpoint
"""

import requests
import json


def test_login():
    """Test login with admin credentials"""

    # Test data
    login_data = {
        "username": "admin",
        "password": "admin"
    }

    try:
        print("🔐 Testing login endpoint...")
        print(f"URL: http://127.0.0.1:8000/api/auth/login")
        print(f"Data: {json.dumps(login_data, indent=2)}")

        response = requests.post(
            "http://127.0.0.1:8000/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )

        print(f"\n📊 Response Status: {response.status_code}")
        print(f"📄 Response Headers: {dict(response.headers)}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Login successful!")
            print(f"📋 Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"❌ Login failed!")
            print(f"📋 Error Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Connection error - server might not be running")
        print("💡 Make sure to start the FastAPI server with: python main.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_health():
    """Test if server is running"""
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running!")
            return True
        else:
            print(f"⚠️  Server responded with status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Server connection failed: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Simple Login Test")
    print("=" * 30)

    # First check if server is running
    if test_health():
        # Then test login
        test_login()
    else:
        print("\n💡 To start the server, run:")
        print("   cd fastapi_backend")
        print("   python main.py")
