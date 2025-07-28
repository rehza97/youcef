#!/usr/bin/env python3
"""
Final test to demonstrate correct API usage
"""
import requests


def test_correct_usage():
    """Test the API the correct way"""
    print("Testing HTTP endpoints (the correct way):")
    print("="*50)

    # Test CORS endpoint
    try:
        response = requests.get(
            'http://127.0.0.1:8000/api/test-cors',
            headers={'Origin': 'http://localhost:5175'}
        )
        print(f"✅ CORS Test: {response.status_code}")
        if response.status_code == 200:
            print(f"✅ Response: {response.json()['message']}")
            # Check CORS headers
            cors_headers = [h for h in response.headers.keys()
                            if 'access-control' in h.lower()]
            if cors_headers:
                print(f"✅ CORS Headers present: {len(cors_headers)} headers")
            else:
                print("❌ No CORS headers found")
    except Exception as e:
        print(f"❌ CORS Test failed: {e}")

    print("-"*30)

    # Test OPTIONS (what React sends first)
    try:
        response = requests.options(
            'http://127.0.0.1:8000/api/login/',
            headers={
                'Origin': 'http://localhost:5175',
                'Access-Control-Request-Method': 'POST'
            }
        )
        print(f"✅ OPTIONS (preflight): {response.status_code}")
    except Exception as e:
        print(f"❌ OPTIONS failed: {e}")

    print("-"*30)

    # Test actual login
    try:
        response = requests.post(
            'http://127.0.0.1:8000/api/login/',
            json={'username': 'fetho', 'password': 'fetho'},
            headers={'Origin': 'http://localhost:5175'}
        )
        print(f"✅ Login POST: {response.status_code}")
        if response.status_code == 401:
            print("✅ Expected 401 for wrong password")
    except Exception as e:
        print(f"❌ Login failed: {e}")

    print("\n" + "="*50)
    print("💡 For your React app:")
    print("1. Make sure it uses: http://127.0.0.1:8000 (HTTP)")
    print("2. Clear browser HSTS cache")
    print("3. Use incognito mode to test")
    print("4. Never use https:// URLs with Django dev server")


if __name__ == "__main__":
    test_correct_usage()
