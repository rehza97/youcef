#!/usr/bin/env python3
"""
Simple verification script to test the key fixes
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
    print("Verifying Key Fixes")
    print("=" * 50)

    # Test 1: Fixed protected endpoint (should no longer have AttributeError)
    print("\n1. Testing protected endpoint fix:")
    test_endpoint("GET", "/api/auth/protected")

    # Test 2: Fixed user search routing (should no longer have 422 error)
    print("\n2. Testing user search routing fix:")
    test_endpoint("GET", "/api/users/search?q=admin")

    # Test 3: Test conversation creation with proper data format
    print("\n3. Testing conversation creation:")
    conversation_data = {
        "name": "Test Conversation",
        "conversation_type": "direct",
        "participant_ids": []
    }
    response = test_endpoint(
        "POST", "/api/messaging/conversations", conversation_data)

    if response and response.status_code == 200:
        result = response.json()
        if "data" in result and "id" in result["data"]:
            conversation_id = result["data"]["id"]
            print(f"  Created conversation with ID: {conversation_id}")

            # Test 4: Test messaging endpoints with the created conversation
            print(
                f"\n4. Testing messaging endpoints with conversation {conversation_id}:")
            test_endpoint(
                "GET", f"/api/messaging/conversations/{conversation_id}")
            test_endpoint(
                "GET", f"/api/messaging/conversations/{conversation_id}/messages")
            test_endpoint("POST", f"/api/messaging/conversations/{conversation_id}/messages", {
                "content": "Hello, this is a test message",
                "message_type": "text"
            })
        else:
            print("  Failed to get conversation ID from response")
    else:
        print("  Failed to create conversation")

    # Test 5: Test notification creation
    print("\n5. Testing notification creation:")
    notification_data = {
        "title": "Test Notification",
        "message": "This is a test notification",
        "notification_type": "info"
    }
    response = test_endpoint("POST", "/api/notifications/", notification_data)

    if response and response.status_code == 200:
        result = response.json()
        notification_id = result.get("id")
        if notification_id:
            print(f"  Created notification with ID: {notification_id}")

            # Test 6: Test notification endpoints with the created notification
            print(
                f"\n6. Testing notification endpoints with notification {notification_id}:")
            test_endpoint("GET", f"/api/notifications/{notification_id}")
            test_endpoint("PUT", f"/api/notifications/{notification_id}/read")
        else:
            print("  Failed to get notification ID from response")
    else:
        print("  Failed to create notification")

    print("\n" + "=" * 50)
    print("Verification completed!")


if __name__ == "__main__":
    main()
