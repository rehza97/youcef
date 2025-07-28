#!/usr/bin/env python3
"""
Enhanced test script for FastAPI endpoints with proper messaging setup
Creates necessary data before testing messaging endpoints
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"


class APITester:
    def __init__(self, base_url="http://127.0.0.1:8000", token=None):
        self.base_url = base_url
        self.token = token
        self.headers = {
            "Content-Type": "application/json"
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

        self.results = {
            "passed": 0,
            "failed": 0,
            "total": 0
        }
        
        # Store created resources for cleanup and reference
        self.created_resources = {
            "users": [],
            "conversations": [],
            "notifications": [],
            "roles": []
        }

    def test_endpoint(self, method, endpoint, data=None, expected_status=200, description="", return_response=False):
        """Test a single endpoint with option to return response"""
        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=self.headers)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, headers=self.headers)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                print(f"❌ Unknown method: {method}")
                return False

            self.results["total"] += 1

            if response.status_code == expected_status:
                print(f"✅ {description} - {method} {endpoint}")
                self.results["passed"] += 1
                if return_response:
                    return response
                return True
            else:
                print(f"❌ {description} - {method} {endpoint}")
                print(f"   Expected: {expected_status}, Got: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                self.results["failed"] += 1
                if return_response:
                    return response
                return False

        except Exception as e:
            print(f"❌ {description} - {method} {endpoint}")
            print(f"   Error: {e}")
            self.results["failed"] += 1
            if return_response:
                return None
            return False

    def setup_test_data(self):
        """Create necessary test data for messaging endpoints"""
        print("\n🔧 Setting up test data for messaging endpoints...")
        print("-" * 50)
        
        # 1. Create a test user to message with
        print("1. Creating test user...")
        test_user_data = {
            "username": "testuser",
            "email": "testuser@test.com",
            "password": "testpassword",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = self.test_endpoint(
            "POST", "/api/auth/register", 
            data=test_user_data, 
            expected_status=201,
            description="Create test user",
            return_response=True
        )
        
        if response and response.status_code == 201:
            user_data = response.json()
            self.created_resources["users"].append(user_data.get("id"))
            print(f"   ✅ Test user created with ID: {user_data.get('id')}")
        else:
            print("   ℹ️  Test user might already exist, continuing...")
        
        # 2. Create a conversation
        print("2. Creating test conversation...")
        # First, get list of users to find someone to create conversation with
        users_response = requests.get(f"{self.base_url}/api/users/", headers=self.headers)
        if users_response.status_code == 200:
            users = users_response.json()
            if len(users) > 1:
                # Find a user that's not the current admin
                other_user = None
                for user in users:
                    if user.get("username") != "admin":
                        other_user = user
                        break
                
                if other_user:
                    conversation_data = {
                        "participant_ids": [other_user.get("id")],
                        "conversation_type": "direct"
                    }
                    
                    conv_response = self.test_endpoint(
                        "POST", "/api/messaging/conversations",
                        data=conversation_data,
                        expected_status=201,
                        description="Create test conversation",
                        return_response=True
                    )
                    
                    if conv_response and conv_response.status_code == 201:
                        conv_data = conv_response.json()
                        self.created_resources["conversations"].append(conv_data.get("id"))
                        print(f"   ✅ Conversation created with ID: {conv_data.get('id')}")
                    else:
                        print("   ❌ Failed to create conversation")
                else:
                    print("   ❌ No other users found to create conversation with")
            else:
                print("   ❌ Not enough users to create conversation")
        
        # 3. Create a test notification
        print("3. Creating test notification...")
        notification_data = {
            "title": "Test Notification",
            "message": "This is a test notification for API testing",
            "notification_type": "info"
        }
        
        notif_response = self.test_endpoint(
            "POST", "/api/notifications/",
            data=notification_data,
            expected_status=201,
            description="Create test notification",
            return_response=True
        )
        
        if notif_response and notif_response.status_code == 201:
            notif_data = notif_response.json()
            self.created_resources["notifications"].append(notif_data.get("id"))
            print(f"   ✅ Notification created with ID: {notif_data.get('id')}")
        else:
            print("   ℹ️  Could not create notification, endpoint might not exist")

    def test_messaging_endpoints_enhanced(self):
        """Test messaging endpoints with proper setup"""
        print("\n💬 Testing Messaging Endpoints (Enhanced)")
        print("-" * 40)

        # Get user conversations
        response = self.test_endpoint("GET", "/api/messaging/conversations",
                                    description="Get User Conversations", return_response=True)
        
        conversations = []
        if response and response.status_code == 200:
            conversations = response.json()
            print(f"   Found {len(conversations)} conversations")

        # Test with existing conversations or created ones
        conversation_id = None
        if conversations:
            conversation_id = conversations[0].get("id")
        elif self.created_resources["conversations"]:
            conversation_id = self.created_resources["conversations"][0]

        if conversation_id:
            print(f"   Using conversation ID: {conversation_id}")
            
            # Get specific conversation
            self.test_endpoint("GET", f"/api/messaging/conversations/{conversation_id}",
                             description=f"Get Conversation {conversation_id}")

            # Get conversation messages
            self.test_endpoint("GET", f"/api/messaging/conversations/{conversation_id}/messages",
                             description=f"Get Messages from Conversation {conversation_id}")

            # Send message
            message_data = {
                "content": "Test message from API testing",
                "message_type": "text"
            }
            self.test_endpoint("POST", f"/api/messaging/conversations/{conversation_id}/messages",
                             data=message_data, description=f"Send Message to Conversation {conversation_id}")
        else:
            print("   ❌ No conversations available for testing")
            # Still test the endpoints but expect failures
            self.test_endpoint("GET", "/api/messaging/conversations/1",
                             expected_status=404, description="Get Non-existent Conversation")
            self.test_endpoint("GET", "/api/messaging/conversations/1/messages",
                             expected_status=404, description="Get Messages from Non-existent Conversation")

        # Get user blocks
        self.test_endpoint("GET", "/api/messaging/blocks",
                         description="Get User Blocks")

        # Test blocking - find a user to block
        users_response = requests.get(f"{self.base_url}/api/users/", headers=self.headers)
        if users_response.status_code == 200:
            users = users_response.json()
            # Find a user that's not the current admin and not already blocked
            target_user = None
            for user in users:
                if user.get("username") != "admin":
                    target_user = user
                    break
            
            if target_user:
                # First, try to unblock if already blocked
                requests.delete(f"{self.base_url}/api/messaging/blocks/{target_user['id']}", headers=self.headers)
                
                # Now try to block
                block_data = {
                    "blocked_user_id": target_user["id"],
                    "reason": "API testing block"
                }
                self.test_endpoint("POST", "/api/messaging/blocks",
                                 data=block_data, description=f"Block User {target_user['id']}")
            else:
                print("   ❌ No suitable user found for block testing")

    def test_notification_endpoints_enhanced(self):
        """Test notification endpoints with proper setup"""
        print("\n🔔 Testing Notification Endpoints (Enhanced)")
        print("-" * 40)

        # Get user notifications
        response = self.test_endpoint("GET", "/api/notifications/",
                                    description="Get User Notifications", return_response=True)
        
        notifications = []
        if response and response.status_code == 200:
            notifications = response.json()
            print(f"   Found {len(notifications)} notifications")

        # Get notification preferences
        self.test_endpoint("GET", "/api/notifications/preferences",
                         description="Get Notification Preferences")

        # Update notification preferences
        pref_data = {
            "email_notifications": True,
            "push_notifications": True,
            "sms_notifications": False
        }
        self.test_endpoint("PUT", "/api/notifications/preferences",
                         data=pref_data, description="Update Notification Preferences")

        # Test with existing notifications or created ones
        notification_id = None
        if notifications:
            notification_id = notifications[0].get("id")
        elif self.created_resources["notifications"]:
            notification_id = self.created_resources["notifications"][0]

        if notification_id:
            print(f"   Using notification ID: {notification_id}")
            # Mark notification as read
            self.test_endpoint("PUT", f"/api/notifications/{notification_id}/read",
                             description=f"Mark Notification {notification_id} as Read")
        else:
            print("   ❌ No notifications available for testing")
            # Test with non-existent ID
            self.test_endpoint("PUT", "/api/notifications/999/read",
                             expected_status=404, description="Mark Non-existent Notification as Read")

        # Mark all notifications as read
        self.test_endpoint("PUT", "/api/notifications/read-all",
                         description="Mark All Notifications as Read")

    def cleanup_test_data(self):
        """Clean up created test data"""
        print("\n🧹 Cleaning up test data...")
        print("-" * 30)
        
        # Note: Add cleanup logic here if your API supports deletion
        # For now, just report what was created
        if self.created_resources["users"]:
            print(f"   Created users: {self.created_resources['users']}")
        if self.created_resources["conversations"]:
            print(f"   Created conversations: {self.created_resources['conversations']}")
        if self.created_resources["notifications"]:
            print(f"   Created notifications: {self.created_resources['notifications']}")

    def print_results(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("📊 TEST RESULTS SUMMARY")
        print("="*60)
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"📊 Total: {self.results['total']}")
        success_rate = (self.results['passed']/self.results['total']*100) if self.results['total'] > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print("="*60)


def test_admin_login():
    """Test admin login and return token"""
    print("🔐 ADMIN LOGIN")
    print("="*30)

    login_data = {
        "username": ADMIN_USERNAME,
        "password": ADMIN_PASSWORD
    }

    try:
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            result = response.json()
            token = result.get("access_token")
            print("✅ Login successful!")
            return token
        else:
            print(f"❌ Login failed: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Login error: {e}")
        return None


def test_basic_endpoints(tester):
    """Test basic endpoints"""
    print("\n🏥 Testing Basic Endpoints")
    print("-" * 40)
    tester.test_endpoint("GET", "/health", description="Health Check")
    tester.test_endpoint("GET", "/", description="Root Endpoint")


def test_auth_endpoints(tester):
    """Test authentication endpoints"""
    print("\n🔐 Testing Authentication Endpoints")  
    print("-" * 40)
    tester.test_endpoint("GET", "/api/auth/protected", description="Protected Endpoint")


def test_user_endpoints(tester):
    """Test user endpoints"""
    print("\n👥 Testing User Management Endpoints")
    print("-" * 40)
    tester.test_endpoint("GET", "/api/users/me", description="Get Current User Profile")
    tester.test_endpoint("GET", "/api/users/", description="Get All Users")


def main():
    """Main test function"""
    print("🧪 Enhanced FastAPI Messaging Endpoint Testing")
    print("=" * 60)
    print(f"🕐 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Check server connection
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Server is running!")
        else:
            print(f"⚠️  Server status: {response.status_code}")
    except Exception as e:
        print(f"❌ Server connection failed: {e}")
        return

    # Get authentication token
    token = test_admin_login()
    if not token:
        print("❌ Cannot proceed without authentication token")
        return

    # Initialize tester
    tester = APITester(base_url=BASE_URL, token=token)
    
    # Setup test data first
    tester.setup_test_data()
    
    # Run basic tests
    test_basic_endpoints(tester)
    test_auth_endpoints(tester)
    test_user_endpoints(tester)
    
    # Run enhanced messaging tests
    tester.test_messaging_endpoints_enhanced()
    tester.test_notification_endpoints_enhanced()
    
    # Print results
    tester.print_results()
    
    # Cleanup
    tester.cleanup_test_data()

    print("\n🎯 What this enhanced test does:")
    print("1. ✅ Creates test users for messaging")
    print("2. ✅ Creates test conversations") 
    print("3. ✅ Creates test notifications")
    print("4. ✅ Tests messaging with actual data")
    print("5. ✅ Handles missing resources gracefully")

    print(f"\n🏁 Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()