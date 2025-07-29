#!/usr/bin/env python3
"""
Test script to debug create conversation 422 error
"""

import requests
import json


def test_create_conversation():
    """Test create conversation endpoint"""
    print("🔍 Testing create conversation endpoint...")

    # First, get authentication token
    auth_url = "http://127.0.0.1:8000/api/auth/login"
    auth_data = {
        "username": "admin",
        "password": "admin123"
    }

    try:
        auth_response = requests.post(auth_url, json=auth_data)
        if auth_response.status_code != 200:
            print(f"❌ Authentication failed: {auth_response.status_code}")
            print(f"Response: {auth_response.text}")
            return False

        token = auth_response.json()["access_token"]
        print(f"✅ Got token: {token[:20]}...")

    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False

    # Test create conversation
    try:
        conversation_url = "http://127.0.0.1:8000/api/messaging/conversations"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        # Test data similar to what frontend sends
        conversation_data = {
            "name": "Test Conversation",
            "conversation_type": "direct",
            "participant_ids": [2]  # Assuming user ID 2 exists
        }

        print(f"📤 Creating conversation...")
        print(f"📁 Data: {json.dumps(conversation_data, indent=2)}")
        print(f"🔐 Headers: {headers}")

        response = requests.post(
            conversation_url, json=conversation_data, headers=headers)

        print(f"📥 Response status: {response.status_code}")
        print(f"📥 Response headers: {dict(response.headers)}")
        print(f"📥 Response body: {response.text}")

        if response.status_code == 200:
            print("✅ Conversation creation successful!")
            return True
        else:
            print(
                f"❌ Conversation creation failed with status {response.status_code}")

            # Try to parse the error details
            try:
                error_data = response.json()
                print(f"📄 Error details: {json.dumps(error_data, indent=2)}")
            except:
                print(f"📄 Raw error: {response.text}")

            return False

    except Exception as e:
        print(f"❌ Request error: {e}")
        return False


if __name__ == "__main__":
    test_create_conversation()
