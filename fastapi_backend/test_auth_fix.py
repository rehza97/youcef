#!/usr/bin/env python3
"""
Quick test script to verify authentication fixes
"""

import requests
import json

# Configuration
BASE_URL = "http://127.0.0.1:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOjEsImV4cCI6MTc1MzczMzA4MywidHlwZSI6ImFjY2VzcyJ9.EBg9H80bRoY1t4bBbD7uKD2BZ5ThTGnOFLLfraeWDqk"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


def test_endpoint(method, endpoint, data=None):
    """Test an endpoint and return the result"""
    url = f"{BASE_URL}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        else:
            print(f"Unsupported method: {method}")
            return None

        print(f"{method} {endpoint}: {response.status_code}")
        if response.status_code != 200:
            print(f"  Error: {response.text}")
        else:
            try:
                result = response.json()
                print(f"  Success: {json.dumps(result, indent=2)[:200]}...")
            except:
                print(f"  Success: {response.text[:200]}...")
        return response

    except Exception as e:
        print(f"{method} {endpoint}: Error - {e}")
        return None


def main():
    print("Testing authentication fixes...")
    print("=" * 50)

    # Test protected endpoints that were failing
    test_endpoint("GET", "/api/auth/protected")
    test_endpoint("GET", "/api/users/me")
    test_endpoint("PUT", "/api/users/me", {
        "first_name": "Admin",
        "last_name": "User"
    })

    # Test search endpoint
    test_endpoint("GET", "/api/users/search?q=admin")

    # Test role creation (should be idempotent now)
    test_endpoint("POST", "/api/users/roles/", {
        "name": "test_role",
        "description": "Test role for testing"
    })

    # Test other endpoints
    test_endpoint("GET", "/api/users/")
    test_endpoint("GET", "/api/users/roles/")
    test_endpoint("GET", "/api/users/permissions/")

    print("\n" + "=" * 50)
    print("Test completed!")


if __name__ == "__main__":
    main()
