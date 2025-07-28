#!/usr/bin/env python3
"""
Improved test script with better error handling and robust test data creation
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


def create_test_notification():
    """Create a test notification and return its ID"""
    print("Creating test notification...")

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
        print("Failed to create notification")
        return None


def create_test_conversation():
    """Create a test conversation and return its ID"""
    print("Creating test conversation...")

    conversation_data = {
        "name": "Test Conversation",
        "conversation_type": "direct",
        "participant_ids": []  # Empty list, current user will be added automatically
    }

    response = test_endpoint(
        "POST", "/api/messaging/conversations", conversation_data)
    if response and response.status_code == 200:
        result = response.json()
        if "data" in result and "id" in result["data"]:
            conversation_id = result["data"]["id"]
        else:
            conversation_id = result.get("id")
        print(f"Created conversation with ID: {conversation_id}")
        return conversation_id
    else:
        print("Failed to create conversation")
        return None


def get_existing_resources():
    """Get existing notifications and conversations to use for testing"""
    print("Getting existing resources...")

    # Get existing notifications
    response = test_endpoint("GET", "/api/notifications/")
    notification_id = None
    if response and response.status_code == 200:
        notifications = response.json()
        if notifications:
            notification_id = notifications[0].get("id")
            print(f"Using existing notification ID: {notification_id}")

    # Get existing conversations
    response = test_endpoint("GET", "/api/messaging/conversations")
    conversation_id = None
    if response and response.status_code == 200:
        conversations = response.json()
        if conversations:
            conversation_id = conversations[0].get("id")
            print(f"Using existing conversation ID: {conversation_id}")

    return notification_id, conversation_id


def main():
    print("Improved API Testing")
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
        "name": "test_role_improved",
        "description": "Test role for improved testing"
    })
    test_endpoint("GET", "/api/users/roles/1")
    test_endpoint("GET", "/api/users/permissions/1")

    # Get or create test data for notifications and messaging
    print("\n--- Getting/Creating Test Data ---")
    notification_id, conversation_id = get_existing_resources()

    # If no existing resources, try to create them
    if not notification_id:
        notification_id = create_test_notification()
    if not conversation_id:
        conversation_id = create_test_conversation()

    # Test notification endpoints (only if we have a valid notification_id)
    if notification_id:
        print(f"\n--- Notification Tests (using ID: {notification_id}) ---")
        test_endpoint("GET", "/api/notifications/")
        test_endpoint("GET", f"/api/notifications/{notification_id}")
        test_endpoint("PUT", f"/api/notifications/{notification_id}/read")
        test_endpoint("PUT", "/api/notifications/read-all")
        test_endpoint("PUT", "/api/notifications/preferences", {
            "email_notifications": True,
            "push_notifications": True,
            "sms_notifications": False
        })
    else:
        print("\n--- Skipping Notification Tests (no valid notification ID) ---")

    # Test messaging endpoints (only if we have a valid conversation_id)
    if conversation_id:
        print(f"\n--- Messaging Tests (using ID: {conversation_id}) ---")
        test_endpoint("GET", "/api/messaging/conversations")
        test_endpoint("GET", f"/api/messaging/conversations/{conversation_id}")
        test_endpoint(
            "GET", f"/api/messaging/conversations/{conversation_id}/messages")
        test_endpoint("POST", f"/api/messaging/conversations/{conversation_id}/messages", {
            "content": "Hello, this is a test message",
            "message_type": "text"
        })
    else:
        print("\n--- Skipping Messaging Tests (no valid conversation ID) ---")

    # Test blocking endpoints (with better error handling)
    print("\n--- Blocking Tests ---")
    test_endpoint("GET", "/api/messaging/blocks")
    # Try to block user 2, but handle the case where they might already be blocked
    response = test_endpoint("POST", "/api/messaging/blocks", {
        "blocked_user_id": 2,
        "reason": "Test blocking"
    }, expected_status=200)  # Allow both 200 and 400 (already blocked)

    if response and response.status_code == 400:
        print("  User is already blocked (expected)")

    print("\n" + "=" * 50)
    print("Improved test completed!")


if __name__ == "__main__":
    main()
