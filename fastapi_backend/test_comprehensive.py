#!/usr/bin/env python3
"""
Comprehensive test script that creates test data and tests all endpoints
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://127.0.0.1:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOjEsImV4cCI6MTc1MzczMzA4MywidHlwZSI6ImFjY2VzcyJ9.EBg9H80bRoY1t4bBbD7uKD2BZ5ThTGnOFLLfraeWDqk"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


def test_endpoint(method, endpoint, data=None, expected_status=200):
    """Test an endpoint and return the result"""
    url = f"{BASE_URL}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            print(f"Unsupported method: {method}")
            return None

        print(f"{method} {endpoint}: {response.status_code}")
        if response.status_code != expected_status:
            print(f"  Expected {expected_status}, got {response.status_code}")
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


def create_test_data():
    """Create test data for notifications and messaging"""
    print("Creating test data...")

    # Create a test notification
    notification_data = {
        "title": "Test Notification",
        "message": "This is a test notification",
        "notification_type": "info"
    }

    response = test_endpoint("POST", "/api/notifications/", notification_data)
    if response and response.status_code == 200:
        notification_id = response.json().get("id")
        print(f"Created notification with ID: {notification_id}")
        return notification_id
    else:
        print("Failed to create notification, using ID 1")
        return 1


def create_test_conversation():
    """Create a test conversation"""
    print("Creating test conversation...")

    # Create a test conversation
    conversation_data = {
        "title": "Test Conversation",
        "conversation_type": "direct"
    }

    response = test_endpoint(
        "POST", "/api/messaging/conversations", conversation_data)
    if response and response.status_code == 200:
        conversation_id = response.json().get("id")
        print(f"Created conversation with ID: {conversation_id}")
        return conversation_id
    else:
        print("Failed to create conversation, using ID 1")
        return 1


def main():
    print("Comprehensive API Testing")
    print("=" * 50)

    # Test health endpoint
    test_endpoint("GET", "/health")

    # Test authentication endpoints
    print("\n--- Authentication Tests ---")
    test_endpoint("GET", "/api/auth/protected")

    # Test user endpoints
    print("\n--- User Tests ---")
    test_endpoint("GET", "/api/users/me")
    test_endpoint("PUT", "/api/users/me", {
        "first_name": "Admin",
        "last_name": "User"
    })
    test_endpoint("GET", "/api/users/search?q=admin")
    test_endpoint("GET", "/api/users/")
    test_endpoint("GET", "/api/users/1")  # Get specific user

    # Test role and permission endpoints
    print("\n--- Role and Permission Tests ---")
    test_endpoint("GET", "/api/users/roles/")
    test_endpoint("GET", "/api/users/permissions/")
    test_endpoint("POST", "/api/users/roles/", {
        "name": "test_role",
        "description": "Test role for testing"
    })
    test_endpoint("GET", "/api/users/roles/1")
    test_endpoint("GET", "/api/users/permissions/1")

    # Create test data for notifications and messaging
    print("\n--- Creating Test Data ---")
    notification_id = create_test_data()
    conversation_id = create_test_conversation()

    # Test notification endpoints
    print("\n--- Notification Tests ---")
    test_endpoint("GET", "/api/notifications/")
    test_endpoint("GET", f"/api/notifications/{notification_id}")
    test_endpoint("PUT", f"/api/notifications/{notification_id}/read")
    test_endpoint("PUT", "/api/notifications/read-all")
    test_endpoint("PUT", "/api/notifications/preferences", {
        "email_notifications": True,
        "push_notifications": True,
        "sms_notifications": False
    })

    # Test messaging endpoints
    print("\n--- Messaging Tests ---")
    test_endpoint("GET", "/api/messaging/conversations")
    test_endpoint("GET", f"/api/messaging/conversations/{conversation_id}")
    test_endpoint(
        "GET", f"/api/messaging/conversations/{conversation_id}/messages")
    test_endpoint("POST", f"/api/messaging/conversations/{conversation_id}/messages", {
        "content": "Hello, this is a test message",
        "message_type": "text"
    })
    test_endpoint("GET", "/api/messaging/blocks")
    test_endpoint("POST", "/api/messaging/blocks", {
        "blocked_user_id": 2,
        "reason": "Test blocking"
    })

    print("\n" + "=" * 50)
    print("Comprehensive test completed!")


if __name__ == "__main__":
    main()
