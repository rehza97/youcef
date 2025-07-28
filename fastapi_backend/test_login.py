#!/usr/bin/env python3
"""
Test script to demonstrate login functionality with username and email
"""

import requests
import json


def test_login_methods():
    """Test login with both username and email"""

    base_url = "http://127.0.0.1:8000"

    # Test credentials
    test_cases = [
        {
            "name": "Login with Username",
            "credentials": {
                "username": "admin",
                "password": "admin"
            }
        },
        {
            "name": "Login with Email",
            "credentials": {
                "username": "admin@a.com",
                "password": "admin"
            }
        },
        {
            "name": "Login with Another User (Username)",
            "credentials": {
                "username": "john_doe",
                "password": "password123"
            }
        },
        {
            "name": "Login with Another User (Email)",
            "credentials": {
                "username": "john@example.com",
                "password": "password123"
            }
        }
    ]

    print("🔐 Testing Login Functionality")
    print("=" * 50)

    for test_case in test_cases:
        print(f"\n🧪 {test_case['name']}")
        print(
            f"   Credentials: {test_case['credentials']['username']} / {test_case['credentials']['password']}")

        try:
            response = requests.post(
                f"{base_url}/api/login",
                json=test_case['credentials'],
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success! Token received")
                print(f"   Token Type: {data.get('token_type')}")
                print(f"   Expires In: {data.get('expires_in')} seconds")

                # Test protected endpoint with token
                headers = {"Authorization": f"Bearer {data['access_token']}"}
                protected_response = requests.get(
                    f"{base_url}/api/protected", headers=headers)

                if protected_response.status_code == 200:
                    protected_data = protected_response.json()
                    print(f"   🔒 Protected endpoint access: ✅")
                    print(
                        f"   User: {protected_data.get('user', {}).get('username')}")
                else:
                    print(f"   🔒 Protected endpoint access: ❌")

            else:
                print(f"   ❌ Failed: {response.status_code}")
                print(f"   Error: {response.text}")

        except requests.exceptions.ConnectionError:
            print(
                f"   ❌ Connection Error: Make sure the server is running on {base_url}")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "=" * 50)
    print("📝 Login Test Summary:")
    print("✅ Both username and email login should work")
    print("✅ Tokens should be generated successfully")
    print("✅ Protected endpoints should be accessible")
    print("\n🚀 To test manually:")
    print("1. Start server: python main.py")
    print("2. Visit: http://127.0.0.1:8000/docs")
    print("3. Try login with:")
    print("   - Username: admin")
    print("   - Email: admin@a.com")
    print("   - Password: admin")


if __name__ == "__main__":
    test_login_methods()
