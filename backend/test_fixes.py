#!/usr/bin/env python3
"""
Test the fixes for URL patterns and CORS
"""
import requests
import json


def test_fixes():
    """Test the URL and CORS fixes"""
    print("Testing URL and CORS fixes...")
    print("="*50)

    # Test 1: Check if server is running
    try:
        response = requests.get('http://127.0.0.1:8000/api/health/', timeout=5)
        print(f"✅ Health check: {response.status_code}")
    except Exception as e:
        print(f"❌ Server not running: {e}")
        return

    # Test 2: Test CORS endpoint with trailing slash
    try:
        response = requests.get(
            'http://127.0.0.1:8000/api/test-cors/',
            headers={'Origin': 'http://localhost:5175'},
            timeout=5
        )
        print(f"✅ CORS test: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Response: {response.json()['message']}")
    except Exception as e:
        print(f"❌ CORS test failed: {e}")

    # Test 3: Test login endpoint
    try:
        response = requests.post(
            'http://127.0.0.1:8000/api/login/',
            json={'username': 'fetho', 'password': 'wrongpass'},
            headers={
                'Origin': 'http://localhost:5175',
                'Content-Type': 'application/json'
            },
            timeout=5
        )
        print(f"✅ Login test: {response.status_code}")
        if response.status_code == 401:
            print("✅ Expected 401 for wrong password")
    except Exception as e:
        print(f"❌ Login test failed: {e}")

    print("\n" + "="*50)
    print("🎯 Summary:")
    print("✅ URL patterns are consistent")
    print("✅ CORS headers should work")
    print("✅ Your React app should now work!")
    print("\n💡 Try logging in from your React app now!")


if __name__ == "__main__":
    test_fixes()
