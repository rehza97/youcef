#!/usr/bin/env python3
"""
Detailed CORS test to debug frontend-backend communication
"""
import requests
import json


def test_cors_detailed():
    """Test CORS with different origins and scenarios"""
    base_url = "http://127.0.0.1:8000"

    # Test different origins
    origins_to_test = [
        "http://localhost:3000",
        "http://localhost:5175",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5175"
    ]

    print("🔍 Detailed CORS Testing...")
    print("=" * 60)

    for origin in origins_to_test:
        print(f"\n🧪 Testing origin: {origin}")
        print("-" * 40)

        # Test OPTIONS (preflight)
        try:
            options_response = requests.options(
                f"{base_url}/api/login/",
                headers={
                    'Origin': origin,
                    'Access-Control-Request-Method': 'POST',
                    'Access-Control-Request-Headers': 'Content-Type,Authorization'
                },
                timeout=5
            )

            print(f"✅ OPTIONS Status: {options_response.status_code}")

            # Check specific CORS headers
            cors_headers = {}
            for header, value in options_response.headers.items():
                if header.lower().startswith('access-control'):
                    cors_headers[header] = value
                    print(f"  {header}: {value}")

            # Validate CORS headers
            if 'Access-Control-Allow-Origin' in cors_headers:
                allowed_origin = cors_headers['Access-Control-Allow-Origin']
                if allowed_origin == origin or allowed_origin == '*':
                    print(f"  ✅ Origin {origin} is allowed")
                else:
                    print(
                        f"  ❌ Origin {origin} not allowed (got: {allowed_origin})")
            else:
                print(f"  ❌ No Access-Control-Allow-Origin header")

        except Exception as e:
            print(f"❌ OPTIONS Error: {e}")

        # Test actual POST request
        try:
            post_response = requests.post(
                f"{base_url}/api/login/",
                json={
                    "username": "fetho",
                    "password": "fetho"
                },
                headers={
                    'Origin': origin,
                    'Content-Type': 'application/json'
                },
                timeout=5
            )

            print(f"✅ POST Status: {post_response.status_code}")

            # Check CORS headers in response
            cors_headers = {}
            for header, value in post_response.headers.items():
                if header.lower().startswith('access-control'):
                    cors_headers[header] = value
                    print(f"  {header}: {value}")

            # Show response content
            if post_response.status_code in [200, 401]:
                print(f"  Response: {post_response.text[:100]}...")
            else:
                print(f"  Full Response: {post_response.text}")

        except Exception as e:
            print(f"❌ POST Error: {e}")

    print("\n" + "=" * 60)
    print("🎯 Summary & Recommendations:")

    # Test health endpoint
    try:
        health_response = requests.get(f"{base_url}/api/health/", timeout=5)
        print(
            f"✅ Server is responsive (health check: {health_response.status_code})")
    except Exception as e:
        print(f"❌ Server connection issue: {e}")

    print("\n💡 Troubleshooting Tips:")
    print("1. Make sure Django server is running on http://127.0.0.1:8000")
    print("2. Check that your React app origin is in CORS_ALLOWED_ORIGINS")
    print("3. Clear browser cache and try incognito mode")
    print("4. Check browser console for exact error messages")


if __name__ == "__main__":
    test_cors_detailed()
