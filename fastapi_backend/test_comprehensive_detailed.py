#!/usr/bin/env python3
"""
Comprehensive and Detailed API Test Script
Tests all endpoints thoroughly with detailed reporting and admin login verification
"""

import requests
import json
import time
from datetime import datetime
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "errors": []
}


def log_test_result(endpoint, method, status_code, expected_status, success, error_msg=None):
    """Log test result with detailed information"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_icon = "✅" if success else "❌"
    print(
        f"{status_icon} [{timestamp}] {method} {endpoint}: {status_code} (expected: {expected_status})")

    if not success and error_msg:
        print(f"    Error: {error_msg}")

    if success:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1
        test_results["errors"].append({
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "expected_status": expected_status,
            "error": error_msg
        })


def test_endpoint(method, endpoint, data=None, expected_status=200, description="", headers=None):
    """Test an endpoint with detailed reporting"""
    url = f"{BASE_URL}{endpoint}"

    if headers is None:
        headers = {
            "Content-Type": "application/json"
        }

    if description:
        print(f"\n🔍 Testing: {description}")
        print(f"   Endpoint: {method} {endpoint}")

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
            print(f"❌ Unsupported method: {method}")
            test_results["failed"] += 1
            return None

        success = response.status_code == expected_status

        if success:
            try:
                result = response.json()
                if isinstance(result, dict) and len(result) > 0:
                    print(
                        f"    Response: {json.dumps(result, indent=4)[:300]}...")
                else:
                    print(f"    Response: {result}")
            except:
                print(f"    Response: {response.text[:200]}...")
        else:
            print(
                f"    Expected: {expected_status}, Got: {response.status_code}")
            print(f"    Error Response: {response.text}")

        log_test_result(endpoint, method, response.status_code,
                        expected_status, success, response.text if not success else None)
        return response

    except Exception as e:
        error_msg = f"Request failed: {str(e)}"
        log_test_result(endpoint, method, 0, expected_status, False, error_msg)
        return None


def test_admin_login():
    """Test admin login functionality specifically"""
    print("\n" + "="*60)
    print("🔐 ADMIN LOGIN TESTING")
    print("="*60)

    # Test login with admin credentials
    login_data = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    }

    response = test_endpoint(
        "POST",
        "/api/auth/login",
        login_data,
        200,
        "Admin Login Test"
    )

    if response and response.status_code == 200:
        result = response.json()
        token = result.get("access_token")
        if token:
            print(f"✅ Admin login successful! Token obtained.")
            return token
        else:
            print("❌ Admin login failed: No token in response")
            return None
    else:
        print("❌ Admin login failed")
        return None


def test_authentication_endpoints(token):
    """Test all authentication-related endpoints"""
    print("\n" + "="*60)
    print("🔐 AUTHENTICATION ENDPOINTS TESTING")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test protected endpoint
    test_endpoint("GET", "/api/auth/protected", headers=headers,
                  description="Protected Endpoint Test")

    # Test invalid token
    invalid_headers = {
        "Authorization": "Bearer invalid_token",
        "Content-Type": "application/json"
    }
    test_endpoint("GET", "/api/auth/protected", headers=invalid_headers,
                  expected_status=401, description="Invalid Token Test")

    # Test login with invalid credentials
    invalid_login = {
        "username": "invalid_user",
        "password": "invalid_password"
    }
    test_endpoint("POST", "/api/auth/login", invalid_login,
                  expected_status=401, description="Invalid Login Test")


def test_user_endpoints(token):
    """Test all user-related endpoints"""
    print("\n" + "="*60)
    print("👥 USER ENDPOINTS TESTING")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test current user profile
    test_endpoint("GET", "/api/users/me", headers=headers,
                  description="Get Current User Profile")

    # Test update current user
    update_data = {
        "first_name": "Admin",
        "last_name": "User",
        "email": "admin@a.com"
    }
    test_endpoint("PUT", "/api/users/me", update_data, headers=headers,
                  description="Update Current User Profile")

    # Test user search
    test_endpoint("GET", "/api/users/search?q=admin", headers=headers,
                  description="Search Users by 'admin'")
    test_endpoint("GET", "/api/users/search?q=test", headers=headers,
                  description="Search Users by 'test'")

    # Test get all users
    test_endpoint("GET", "/api/users/", headers=headers,
                  description="Get All Users")

    # Test get specific user
    test_endpoint("GET", "/api/users/1", headers=headers,
                  description="Get User by ID (1)")
    test_endpoint("GET", "/api/users/2", headers=headers,
                  description="Get User by ID (2)")


def test_role_permission_endpoints(token):
    """Test all role and permission endpoints"""
    print("\n" + "="*60)
    print("🔑 ROLE & PERMISSION ENDPOINTS TESTING")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test get all roles
    test_endpoint("GET", "/api/users/roles/", headers=headers,
                  description="Get All Roles")

    # Test get all permissions
    test_endpoint("GET", "/api/users/permissions/", headers=headers,
                  description="Get All Permissions")

    # Test create new role
    new_role = {
        "name": "test_role_detailed",
        "description": "Test role for detailed testing"
    }
    test_endpoint("POST", "/api/users/roles/", new_role, headers=headers,
                  description="Create New Role")

    # Test get specific role
    test_endpoint("GET", "/api/users/roles/1", headers=headers,
                  description="Get Role by ID (1)")

    # Test get specific permission
    test_endpoint("GET", "/api/users/permissions/1", headers=headers,
                  description="Get Permission by ID (1)")

    # Test get user roles
    test_endpoint("GET", "/api/users/1/roles", headers=headers,
                  description="Get Roles for User ID 1")

    # Test get role permissions
    test_endpoint("GET", "/api/users/roles/1/permissions", headers=headers,
                  description="Get Permissions for Role ID 1")


def create_test_notification(token):
    """Create a test notification and return its ID"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    notification_data = {
        "title": "Test Notification Detailed",
        "message": "This is a detailed test notification",
        "notification_type": "info"
    }

    response = test_endpoint("POST", "/api/notifications/", notification_data,
                             headers=headers, description="Create Test Notification")

    if response and response.status_code == 200:
        result = response.json()
        notification_id = result.get("id")
        print(f"✅ Created notification with ID: {notification_id}")
        return notification_id
    else:
        print("❌ Failed to create notification")
        return None


def test_notification_endpoints(token):
    """Test all notification endpoints"""
    print("\n" + "="*60)
    print("🔔 NOTIFICATION ENDPOINTS TESTING")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test get all notifications
    test_endpoint("GET", "/api/notifications/", headers=headers,
                  description="Get All Notifications")

    # Create test notification
    notification_id = create_test_notification(token)

    if notification_id:
        # Test get specific notification
        test_endpoint("GET", f"/api/notifications/{notification_id}", headers=headers,
                      description=f"Get Notification by ID ({notification_id})")

        # Test mark notification as read
        test_endpoint("PUT", f"/api/notifications/{notification_id}/read", headers=headers,
                      description=f"Mark Notification as Read ({notification_id})")

        # Test get notification again to verify it's marked as read
        test_endpoint("GET", f"/api/notifications/{notification_id}", headers=headers,
                      description=f"Verify Notification Read Status ({notification_id})")
    else:
        # Try to test with existing notifications
        response = test_endpoint("GET", "/api/notifications/", headers=headers,
                                 description="Get Existing Notifications")
        if response and response.status_code == 200:
            notifications = response.json()
            if notifications:
                existing_id = notifications[0].get("id")
                test_endpoint("GET", f"/api/notifications/{existing_id}", headers=headers,
                              description=f"Get Existing Notification ({existing_id})")
                test_endpoint("PUT", f"/api/notifications/{existing_id}/read", headers=headers,
                              description=f"Mark Existing Notification as Read ({existing_id})")

    # Test mark all notifications as read
    test_endpoint("PUT", "/api/notifications/read-all", headers=headers,
                  description="Mark All Notifications as Read")

    # Test update notification preferences
    preferences = {
        "email_notifications": True,
        "push_notifications": True,
        "sms_notifications": False
    }
    test_endpoint("PUT", "/api/notifications/preferences", preferences, headers=headers,
                  description="Update Notification Preferences")


def create_test_conversation(token):
    """Create a test conversation and return its ID"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    conversation_data = {
        "name": "Test Conversation Detailed",
        "conversation_type": "direct",
        "participant_ids": []
    }

    response = test_endpoint("POST", "/api/messaging/conversations", conversation_data,
                             headers=headers, description="Create Test Conversation")

    if response and response.status_code == 200:
        result = response.json()
        if "data" in result and "id" in result["data"]:
            conversation_id = result["data"]["id"]
        else:
            conversation_id = result.get("id")
        print(f"✅ Created conversation with ID: {conversation_id}")
        return conversation_id
    else:
        print("❌ Failed to create conversation")
        return None


def test_messaging_endpoints(token):
    """Test all messaging endpoints"""
    print("\n" + "="*60)
    print("💬 MESSAGING ENDPOINTS TESTING")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test get all conversations
    test_endpoint("GET", "/api/messaging/conversations", headers=headers,
                  description="Get All Conversations")

    # Create test conversation
    conversation_id = create_test_conversation(token)

    if conversation_id:
        # Test get specific conversation
        test_endpoint("GET", f"/api/messaging/conversations/{conversation_id}", headers=headers,
                      description=f"Get Conversation by ID ({conversation_id})")

        # Test get messages in conversation
        test_endpoint("GET", f"/api/messaging/conversations/{conversation_id}/messages", headers=headers,
                      description=f"Get Messages in Conversation ({conversation_id})")

        # Test send message
        message_data = {
            "content": "Hello, this is a detailed test message",
            "message_type": "text"
        }
        test_endpoint("POST", f"/api/messaging/conversations/{conversation_id}/messages", message_data,
                      headers=headers, description=f"Send Message to Conversation ({conversation_id})")

        # Test get messages again to verify the new message
        test_endpoint("GET", f"/api/messaging/conversations/{conversation_id}/messages", headers=headers,
                      description=f"Verify New Message in Conversation ({conversation_id})")
    else:
        # Try to test with existing conversations
        response = test_endpoint("GET", "/api/messaging/conversations", headers=headers,
                                 description="Get Existing Conversations")
        if response and response.status_code == 200:
            conversations = response.json()
            if conversations:
                existing_id = conversations[0].get("id")
                test_endpoint("GET", f"/api/messaging/conversations/{existing_id}", headers=headers,
                              description=f"Get Existing Conversation ({existing_id})")
                test_endpoint("GET", f"/api/messaging/conversations/{existing_id}/messages", headers=headers,
                              description=f"Get Messages in Existing Conversation ({existing_id})")


def test_blocking_endpoints(token):
    """Test all user blocking endpoints"""
    print("\n" + "="*60)
    print("🚫 USER BLOCKING ENDPOINTS TESTING")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test get all blocks
    test_endpoint("GET", "/api/messaging/blocks", headers=headers,
                  description="Get All User Blocks")

    # Test block user
    block_data = {
        "blocked_user_id": 2,
        "reason": "Test blocking for detailed testing"
    }
    response = test_endpoint("POST", "/api/messaging/blocks", block_data, headers=headers,
                             description="Block User ID 2")

    if response and response.status_code == 400:
        print("    Note: User might already be blocked (expected behavior)")

    # Test block user again (should fail)
    test_endpoint("POST", "/api/messaging/blocks", block_data, headers=headers,
                  expected_status=400, description="Try to Block Already Blocked User")


def test_file_upload_endpoints(token):
    """Test file upload and preview endpoints"""
    print("\n" + "="*60)
    print("📁 FILE UPLOAD & PREVIEW ENDPOINTS TESTING")
    print("="*60)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # Test get user files
    test_endpoint("GET", "/api/files/", headers=headers,
                  description="Get User Files")

    # Test file statistics
    test_endpoint("GET", "/api/files/stats/summary", headers=headers,
                  description="Get File Upload Statistics")

    # Test file upload endpoints (without actual file upload for comprehensive test)
    test_endpoint("GET", "/api/files/1", headers=headers,
                  expected_status=404, description="Get Non-existent File Details")

    test_endpoint("GET", "/api/files/1/previews", headers=headers,
                  expected_status=404, description="Get Non-existent File Previews")

    test_endpoint("GET", "/api/files/1/status", headers=headers,
                  expected_status=404, description="Get Non-existent File Status")

    test_endpoint("DELETE", "/api/files/1", headers=headers,
                  expected_status=404, description="Delete Non-existent File")


def test_health_endpoint():
    """Test health check endpoint"""
    print("\n" + "="*60)
    print("🏥 HEALTH CHECK TESTING")
    print("="*60)

    test_endpoint("GET", "/health", description="Health Check Endpoint")


def print_test_summary():
    """Print comprehensive test summary"""
    print("\n" + "="*60)
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print("="*60)

    total_tests = test_results["passed"] + \
        test_results["failed"] + test_results["skipped"]

    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"⏭️  Skipped: {test_results['skipped']}")

    if test_results["failed"] > 0:
        success_rate = (test_results["passed"] / total_tests) * 100
        print(f"Success Rate: {success_rate:.1f}%")

        print("\n❌ Failed Tests:")
        for error in test_results["errors"]:
            print(
                f"  - {error['method']} {error['endpoint']}: {error['status_code']} (expected: {error['expected_status']})")
            if error['error']:
                print(f"    Error: {error['error'][:100]}...")
    else:
        print("🎉 All tests passed successfully!")


def main():
    """Main test execution function"""
    print("🚀 COMPREHENSIVE API TESTING STARTED")
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    try:
        # Test health endpoint first
        test_health_endpoint()

        # Test admin login and get token
        token = test_admin_login()

        if not token:
            print("❌ Cannot proceed without valid admin token")
            sys.exit(1)

        # Test all endpoints with the token
        test_authentication_endpoints(token)
        test_user_endpoints(token)
        test_role_permission_endpoints(token)
        test_notification_endpoints(token)
        test_messaging_endpoints(token)
        test_blocking_endpoints(token)
        test_file_upload_endpoints(token)

        # Print final summary
        print_test_summary()

    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        test_results["failed"] += 1

    print(
        f"\n🏁 Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
