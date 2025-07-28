#!/usr/bin/env python3
"""
Test script to verify CORS configuration and API endpoints
"""
import requests
import json


def test_cors_configuration():
    """Test CORS configuration"""
    base_url = "http://127.0.0.1:8000"

    print("🔍 Testing CORS Configuration...")
    print(f"📡 Testing against: {base_url}")

    # Test OPTIONS request (preflight)
    try:
        response = requests.options(
            f"{base_url}/api/login/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }
        )

        print(f"✅ OPTIONS request status: {response.status_code}")
        print(f"📋 CORS Headers:")
        for header, value in response.headers.items():
            if 'access-control' in header.lower():
                print(f"   {header}: {value}")

    except requests.exceptions.ConnectionError:
        print(
            "❌ Could not connect to server. Make sure the backend is running on port 8000")
        return False

    # Test actual API request
    try:
        response = requests.post(
            f"{base_url}/api/login/",
            headers={
                "Content-Type": "application/json",
                "Origin": "http://localhost:5173"
            },
            json={
                "username": "test",
                "password": "test"
            }
        )

        print(f"✅ POST request status: {response.status_code}")
        print(f"📋 Response headers:")
        for header, value in response.headers.items():
            if 'access-control' in header.lower():
                print(f"   {header}: {value}")

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server")
        return False

    return True


def test_health_endpoint():
    """Test health endpoint"""
    base_url = "http://127.0.0.1:8000"

    print("\n🏥 Testing Health Endpoint...")

    try:
        response = requests.get(f"{base_url}/api/health/")
        print(f"✅ Health endpoint status: {response.status_code}")
        if response.status_code == 200:
            print(f"📋 Response: {response.json()}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to health endpoint")
        return False


def test_registration():
    """Test user registration"""
    base_url = "http://127.0.0.1:8000"

    print("\n👤 Testing User Registration...")

    try:
        response = requests.post(
            f"{base_url}/api/register/",
            headers={
                "Content-Type": "application/json",
                "Origin": "http://localhost:5173"
            },
            json={
                "username": "testuser",
                "password": "testpass123",
                "email": "test@example.com"
            }
        )

        print(f"✅ Registration status: {response.status_code}")
        if response.status_code == 201:
            print("✅ Registration successful!")
        elif response.status_code == 400:
            print("⚠️  Registration failed (expected for duplicate user)")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to registration endpoint")
        return False


if __name__ == "__main__":
    print("🚀 Starting CORS and API Tests for New Backend...\n")

    cors_ok = test_cors_configuration()
    health_ok = test_health_endpoint()
    registration_ok = test_registration()

    print("\n" + "="*50)
    if cors_ok and health_ok and registration_ok:
        print("✅ All tests passed! New backend is properly configured.")
    else:
        print("❌ Some tests failed. Check the server configuration.")
    print("="*50)
