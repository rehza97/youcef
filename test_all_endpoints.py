#!/usr/bin/env python3
"""
Comprehensive FastAPI Endpoint Testing Script
Tests all endpoints across all modules with proper authentication and data setup
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configuration
BASE_URL = "http://127.0.0.1:8000"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# Test data
TEST_USER = {
    "username": "testuser",
    "email": "testuser@test.com",
    "password": "TestPass123",
    "first_name": "Test",
    "last_name": "User",
    "bio": "Test user for API testing"
}

TEST_ROLE = {
    "name": "test_role",
    "description": "Test role for API testing"
}

TEST_PERMISSION = {
    "codename": "test_permission",
    "name": "Test Permission",
    "description": "Test permission for API testing"
}

TEST_NOTIFICATION = {
    "title": "Test Notification",
    "message": "This is a test notification",
    "notification_type": "info",
    "user_id": 1  # Add the required user_id field
}

TEST_CONVERSATION = {
    "name": "Test Conversation",
    "conversation_type": "group",
    "participant_ids": []
}

TEST_MESSAGE = {
    "content": "This is a test message",
    "message_type": "text"
}

TEST_FILE_CONTENT = "name,age,city\nJohn,25,New York\nJane,30,Los Angeles"

TEST_ENCAISSEMENT_CONTENT = """Org Name,N FACT,Typ Fact,Date Fact,Montant Ht,Montant Taxe,Montant Ttc,Chiffre Aff Exe,Encaissement
DOT_ALGER,1001,FACTURE,2024-01-15,1000.00,200.00,1200.00,1200.00,1000.00
DOT_ORAN,1002,FACTURE,2024-01-16,1500.00,300.00,1800.00,1800.00,1620.00
DOT_CONSTANTINE,1003,FACTURE,2024-01-17,800.00,160.00,960.00,960.00,720.00"""


class ComprehensiveAPITester:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "errors": []
        }

        # Store created resources for cleanup
        self.created_resources = {
            "users": [],
            "roles": [],
            "permissions": [],
            "conversations": [],
            "notifications": [],
            "files": []
        }

    def test_endpoint(self, method: str, endpoint: str, data: Optional[Dict] = None,
                      expected_status: int = 200, description: str = "",
                      return_response: bool = False, files: Optional[Dict] = None):
        """Test a single endpoint"""
        url = f"{self.base_url}{endpoint}"
        headers = {"Content-Type": "application/json"}

        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            if method.upper() == "GET":
                response = self.session.get(url, headers=headers)
            elif method.upper() == "POST":
                if files:
                    # Remove Content-Type for file uploads
                    headers.pop("Content-Type", None)
                    response = self.session.post(
                        url, data=data, files=files, headers=headers)
                else:
                    response = self.session.post(
                        url, json=data, headers=headers)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data, headers=headers)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, headers=headers)
            else:
                print(f"❌ Unknown method: {method}")
                return False

            self.test_results["total"] += 1

            if response.status_code == expected_status:
                print(f"✅ {description} - {method} {endpoint}")
                self.test_results["passed"] += 1
                if return_response:
                    return response
                return True
            else:
                print(f"❌ {description} - {method} {endpoint}")
                print(
                    f"   Expected: {expected_status}, Got: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                self.test_results["failed"] += 1
                self.test_results["errors"].append({
                    "endpoint": endpoint,
                    "method": method,
                    "expected": expected_status,
                    "got": response.status_code,
                    "response": response.text[:200]
                })
                if return_response:
                    return response
                return False

        except Exception as e:
            print(f"❌ {description} - {method} {endpoint}")
            print(f"   Error: {e}")
            self.test_results["failed"] += 1
            self.test_results["errors"].append({
                "endpoint": endpoint,
                "method": method,
                "error": str(e)
            })
            if return_response:
                return None
            return False

    def login(self, username: str, password: str) -> bool:
        """Login and get auth token"""
        login_data = {
            "username": username,
            "password": password
        }

        response = self.test_endpoint(
            "POST", "/api/auth/login",
            data=login_data,
            expected_status=200,
            description="Admin Login",
            return_response=True
        )

        if response and response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            print(f"✅ Login successful for {username}")
            return True
        else:
            print(f"❌ Login failed for {username}")
            return False

    def test_health_endpoints(self):
        """Test health and info endpoints"""
        print("\n🏥 Testing Health & Info Endpoints")
        print("-" * 50)

        self.test_endpoint("GET", "/", description="Root Endpoint")
        self.test_endpoint("GET", "/health", description="Health Check")
        self.test_endpoint("GET", "/api/health",
                           description="API Health Check")
        self.test_endpoint("GET", "/api/health/detailed",
                           description="Detailed Health Check")
        self.test_endpoint("GET", "/api/info", description="API Info")

    def test_auth_endpoints(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication Endpoints")
        print("-" * 50)

        # Test registration
        self.test_endpoint("POST", "/api/auth/register",
                           data=TEST_USER, expected_status=201,
                           description="Register New User")

        # Test login
        self.test_endpoint("POST", "/api/auth/login",
                           data={"username": "admin", "password": "admin"},
                           expected_status=200, description="Admin Login")

        # Test protected endpoint
        self.test_endpoint("GET", "/api/auth/protected",
                           description="Protected Endpoint")

        # Test CORS
        self.test_endpoint("GET", "/api/auth/test-cors",
                           description="CORS Test")

    def test_user_endpoints(self):
        """Test user management endpoints"""
        print("\n👥 Testing User Management Endpoints")
        print("-" * 50)

        # Get current user
        self.test_endpoint("GET", "/api/users/me",
                           description="Get Current User")

        # Get all users
        response = self.test_endpoint("GET", "/api/users/",
                                      description="Get All Users", return_response=True)

        # Create user (admin only)
        self.test_endpoint("POST", "/api/users/",
                           data=TEST_USER, expected_status=201,
                           description="Create User (Admin)")

        # Get specific user
        if response and response.status_code == 200:
            users = response.json()
            if users:
                user_id = users[0].get("id")
                self.test_endpoint("GET", f"/api/users/{user_id}",
                                   description=f"Get User {user_id}")

        # Update user
        update_data = {"first_name": "Updated Test"}
        self.test_endpoint("PUT", "/api/users/me",
                           data=update_data, description="Update Current User")

        # Search users
        self.test_endpoint("GET", "/api/users/search?q=test",
                           description="Search Users")

    def test_role_endpoints(self):
        """Test role management endpoints"""
        print("\n👑 Testing Role Management Endpoints")
        print("-" * 50)

        # Get all roles
        response = self.test_endpoint("GET", "/api/users/roles/",
                                      description="Get All Roles", return_response=True)

        # Create role
        response = self.test_endpoint("POST", "/api/users/roles/",
                                      data=TEST_ROLE, expected_status=201,
                                      description="Create Role", return_response=True)

        if response and response.status_code == 201:
            role_data = response.json()
            role_id = role_data.get("id")
            self.created_resources["roles"].append(role_id)

            # Get specific role
            self.test_endpoint("GET", f"/api/users/roles/{role_id}",
                               description=f"Get Role {role_id}")

            # Update role
            update_data = {"description": "Updated test role"}
            self.test_endpoint("PUT", f"/api/users/roles/{role_id}",
                               data=update_data, description=f"Update Role {role_id}")

            # Get role permissions
            self.test_endpoint("GET", f"/api/users/roles/{role_id}/permissions",
                               description=f"Get Role Permissions {role_id}")

        # Check role
        self.test_endpoint("GET", "/api/users/check-role/admin?user_id=1",
                           description="Check Admin Role")

    def test_permission_endpoints(self):
        """Test permission management endpoints"""
        print("\n🔑 Testing Permission Management Endpoints")
        print("-" * 50)

        # Get all permissions
        response = self.test_endpoint("GET", "/api/users/permissions/",
                                      description="Get All Permissions", return_response=True)

        # Create permission
        response = self.test_endpoint("POST", "/api/users/permissions/",
                                      data=TEST_PERMISSION, expected_status=201,
                                      description="Create Permission", return_response=True)

        if response and response.status_code == 201:
            permission_data = response.json()
            permission_id = permission_data.get("id")
            self.created_resources["permissions"].append(permission_id)

            # Get specific permission
            self.test_endpoint("GET", f"/api/users/permissions/{permission_id}",
                               description=f"Get Permission {permission_id}")

            # Update permission
            update_data = {"description": "Updated test permission"}
            self.test_endpoint("PUT", f"/api/users/permissions/{permission_id}",
                               data=update_data, description=f"Update Permission {permission_id}")

        # Check permission
        self.test_endpoint("GET", "/api/users/check-permission/test_permission?user_id=1",
                           description="Check Permission")

    def test_notification_endpoints(self):
        """Test notification endpoints"""
        print("\n🔔 Testing Notification Endpoints")
        print("-" * 50)

        # Get notifications
        response = self.test_endpoint("GET", "/api/notifications/",
                                      description="Get Notifications", return_response=True)

        # Get notification stats
        self.test_endpoint("GET", "/api/notifications/stats",
                           description="Get Notification Stats")

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

        # Create notification
        response = self.test_endpoint("POST", "/api/notifications/",
                                      data=TEST_NOTIFICATION, expected_status=201,
                                      description="Create Notification", return_response=True)

        if response and response.status_code == 201:
            notification_data = response.json()
            notification_id = notification_data.get("id")
            self.created_resources["notifications"].append(notification_id)

            # Get specific notification
            self.test_endpoint("GET", f"/api/notifications/{notification_id}",
                               description=f"Get Notification {notification_id}")

            # Update notification
            update_data = {"title": "Updated Test Notification"}
            self.test_endpoint("PUT", f"/api/notifications/{notification_id}",
                               data=update_data, description=f"Update Notification {notification_id}")

            # Mark as read
            self.test_endpoint("PUT", f"/api/notifications/{notification_id}/read",
                               description=f"Mark Notification {notification_id} as Read")

    def test_messaging_endpoints(self):
        """Test messaging endpoints"""
        print("\n💬 Testing Messaging Endpoints")
        print("-" * 50)

        # Get conversations
        response = self.test_endpoint("GET", "/api/messaging/conversations",
                                      description="Get Conversations", return_response=True)

        # Create conversation
        response = self.test_endpoint("POST", "/api/messaging/conversations",
                                      data=TEST_CONVERSATION, expected_status=201,
                                      description="Create Conversation", return_response=True)

        if response and response.status_code == 201:
            conversation_data = response.json()
            conversation_id = conversation_data.get("id")
            self.created_resources["conversations"].append(conversation_id)

            # Get specific conversation
            self.test_endpoint("GET", f"/api/messaging/conversations/{conversation_id}",
                               description=f"Get Conversation {conversation_id}")

            # Get conversation messages
            self.test_endpoint("GET", f"/api/messaging/conversations/{conversation_id}/messages",
                               description=f"Get Conversation Messages {conversation_id}")

            # Send message
            response = self.test_endpoint("POST", f"/api/messaging/conversations/{conversation_id}/messages",
                                          data=TEST_MESSAGE, expected_status=201,
                                          description=f"Send Message to Conversation {conversation_id}",
                                          return_response=True)

            if response and response.status_code == 201:
                message_data = response.json()
                message_id = message_data.get("id")

                # Get specific message
                self.test_endpoint("GET", f"/api/messaging/messages/{message_id}",
                                   description=f"Get Message {message_id}")

                # Update message
                update_data = {"content": "Updated test message"}
                self.test_endpoint("PUT", f"/api/messaging/messages/{message_id}",
                                   data=update_data, description=f"Update Message {message_id}")

        # Get blocked users
        self.test_endpoint("GET", "/api/messaging/blocks",
                           description="Get Blocked Users")

        # Block user (if we have other users)
        users_response = self.test_endpoint(
            "GET", "/api/users/", return_response=True)
        if users_response and users_response.status_code == 200:
            users = users_response.json()
            if len(users) > 1:
                target_user = users[1]  # Second user
                block_data = {
                    "blocked_user_id": target_user.get("id"),
                    "reason": "API testing block"
                }
                self.test_endpoint("POST", "/api/messaging/blocks",
                                   data=block_data, description=f"Block User {target_user.get('id')}")

    def test_file_endpoints(self):
        """Test file management endpoints"""
        print("\n📁 Testing File Management Endpoints")
        print("-" * 50)

        # Get files
        self.test_endpoint("GET", "/api/files/", description="Get User Files")

        # Upload file
        files = {"file": ("test.csv", TEST_FILE_CONTENT, "text/csv")}
        response = self.test_endpoint("POST", "/api/files/upload",
                                      data={}, files=files, expected_status=201,
                                      description="Upload File", return_response=True)

        if response and response.status_code == 201:
            file_data = response.json()
            file_id = file_data.get("id")
            self.created_resources["files"].append(file_id)

            # Get specific file
            self.test_endpoint("GET", f"/api/files/{file_id}",
                               description=f"Get File {file_id}")

            # Get file previews
            self.test_endpoint("GET", f"/api/files/{file_id}/previews",
                               description=f"Get File Previews {file_id}")

            # Get file status
            self.test_endpoint("GET", f"/api/files/{file_id}/status",
                               description=f"Get File Status {file_id}")

            # Update file
            update_data = {"original_filename": "updated_test.csv"}
            self.test_endpoint("PUT", f"/api/files/{file_id}",
                               data=update_data, description=f"Update File {file_id}")

            # Generate preview
            self.test_endpoint("POST", f"/api/files/{file_id}/preview",
                               description=f"Generate File Preview {file_id}")

        # Get file statistics
        self.test_endpoint("GET", "/api/files/stats/summary",
                           description="Get File Statistics")

        # Admin endpoints
        self.test_endpoint("GET", "/api/files/admin/all",
                           description="Get All Files (Admin)")

    def test_encaissement_endpoints(self):
        """Test encaissement endpoints"""
        print("\n💰 Testing Encaissement Endpoints")
        print("-" * 50)

        # Get overview
        self.test_endpoint("GET", "/api/encaissement/overview",
                           description="Get Encaissement Overview")

        # Get by organisation
        self.test_endpoint("GET", "/api/encaissement/by-organisation",
                           description="Get Encaissement by Organisation")

        # Get by date
        self.test_endpoint("GET", "/api/encaissement/by-date",
                           description="Get Encaissement by Date")

        # Get by encaisse rate
        self.test_endpoint("GET", "/api/encaissement/by-encaisse-rate",
                           description="Get Encaissement by Rate")

        # Get chart data
        chart_types = ["histogram_combined", "pie_3d", "histogram_dot_rate"]
        for chart_type in chart_types:
            self.test_endpoint("GET", f"/api/encaissement/chart-data?chart_type={chart_type}",
                               description=f"Get Chart Data - {chart_type}")

        # Upload encaissement data
        files = {"file": ("test_encaissement.csv",
                          TEST_ENCAISSEMENT_CONTENT, "text/csv")}
        self.test_endpoint("POST", "/api/encaissement/upload-data",
                           data={}, files=files, expected_status=200,
                           description="Upload Encaissement Data")

    def cleanup_resources(self):
        """Clean up created test resources"""
        print("\n🧹 Cleaning up test resources...")
        print("-" * 40)

        # Delete created resources in reverse order
        for resource_type, ids in self.created_resources.items():
            for resource_id in ids:
                if resource_type == "files":
                    self.test_endpoint("DELETE", f"/api/files/{resource_id}",
                                       description=f"Delete File {resource_id}")
                elif resource_type == "notifications":
                    self.test_endpoint("DELETE", f"/api/notifications/{resource_id}",
                                       description=f"Delete Notification {resource_id}")
                elif resource_type == "conversations":
                    self.test_endpoint("DELETE", f"/api/messaging/conversations/{resource_id}",
                                       description=f"Delete Conversation {resource_id}")
                elif resource_type == "roles":
                    self.test_endpoint("DELETE", f"/api/users/roles/{resource_id}",
                                       description=f"Delete Role {resource_id}")
                elif resource_type == "permissions":
                    self.test_endpoint("DELETE", f"/api/users/permissions/{resource_id}",
                                       description=f"Delete Permission {resource_id}")

    def print_results(self):
        """Print comprehensive test results"""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("="*80)
        print(f"✅ Passed: {self.test_results['passed']}")
        print(f"❌ Failed: {self.test_results['failed']}")
        print(f"📊 Total: {self.test_results['total']}")

        if self.test_results['total'] > 0:
            success_rate = (
                self.test_results['passed'] / self.test_results['total']) * 100
            print(f"📈 Success Rate: {success_rate:.1f}%")

        if self.test_results['errors']:
            print(f"\n❌ Errors ({len(self.test_results['errors'])}):")
            # Show first 5 errors
            for error in self.test_results['errors'][:5]:
                print(
                    f"   - {error.get('method', '')} {error.get('endpoint', '')}: {error.get('got', '')}")
            if len(self.test_results['errors']) > 5:
                print(
                    f"   ... and {len(self.test_results['errors']) - 5} more errors")

        print("="*80)

    def run_all_tests(self):
        """Run all comprehensive tests"""
        print("🚀 COMPREHENSIVE FASTAPI ENDPOINT TESTING")
        print("=" * 80)
        print(
            f"🕐 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # Check server connection
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Server is running!")
            else:
                print(f"⚠️  Server status: {response.status_code}")
        except Exception as e:
            print(f"❌ Server connection failed: {e}")
            return

        # Login as admin
        if not self.login(ADMIN_USERNAME, ADMIN_PASSWORD):
            print("❌ Cannot proceed without authentication")
            return

        # Run all test suites
        self.test_health_endpoints()
        self.test_auth_endpoints()
        self.test_user_endpoints()
        self.test_role_endpoints()
        self.test_permission_endpoints()
        self.test_notification_endpoints()
        self.test_messaging_endpoints()
        self.test_file_endpoints()
        self.test_encaissement_endpoints()

        # Print results
        self.print_results()

        # Cleanup
        self.cleanup_resources()

        print(
            f"\n🏁 Testing completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n📋 Test Coverage Summary:")
        print("✅ Health & Info Endpoints")
        print("✅ Authentication Endpoints")
        print("✅ User Management (CRUD)")
        print("✅ Role Management (CRUD)")
        print("✅ Permission Management (CRUD)")
        print("✅ Notification System (CRUD)")
        print("✅ Messaging System (CRUD)")
        print("✅ File Management (CRUD)")
        print("✅ Encaissement Module")


def main():
    """Main function"""
    tester = ComprehensiveAPITester(BASE_URL)
    tester.run_all_tests()


if __name__ == "__main__":
    main()
