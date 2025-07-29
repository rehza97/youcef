#!/usr/bin/env python3
"""
Comprehensive CRUD Test Script
Tests all CRUD operations for users, roles, permissions, notifications, messaging, and files
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api"

# Test data
TEST_USER = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "testpass123",
    "first_name": "Test",
    "last_name": "User"
}

TEST_ROLE = {
    "name": "test_role",
    "description": "Test role for CRUD operations"
}

TEST_PERMISSION = {
    "codename": "test_permission",
    "name": "Test Permission",
    "description": "Test permission for CRUD operations"
}

TEST_NOTIFICATION = {
    "title": "Test Notification",
    "message": "This is a test notification",
    "notification_type": "info",
    "user_id": 1
}

TEST_CONVERSATION = {
    "name": "Test Conversation",
    "conversation_type": "group",
    "participant_ids": [1, 2]
}

TEST_MESSAGE = {
    "content": "This is a test message",
    "conversation_id": 1
}


class CRUDTester:
    def __init__(self):
        self.session = requests.Session()
        self.auth_token = None
        self.test_results = {}

    def login(self, username: str, password: str) -> bool:
        """Login and get auth token"""
        try:
            response = self.session.post(f"{BASE_URL}/api/auth/login", json={
                "username": username,
                "password": password
            })

            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                if self.auth_token:
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.auth_token}"
                    })
                return True
            else:
                print(
                    f"Login failed: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Login error: {e}")
            return False

    def test_health(self) -> bool:
        """Test health endpoint"""
        try:
            response = self.session.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("✅ Health check passed")
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False

    def test_user_crud(self) -> Dict[str, Any]:
        """Test User CRUD operations"""
        results = {"create": False, "read": False,
                   "update": False, "delete": False}

        try:
            # CREATE
            response = self.session.post(f"{API_BASE}/users/", json=TEST_USER)
            if response.status_code == 201 or response.status_code == 200:
                user_data = response.json()
                user_id = user_data.get("id")
                print(f"✅ User created: {user_id}")
                results["create"] = True

                # READ
                response = self.session.get(f"{API_BASE}/users/{user_id}")
                if response.status_code == 200:
                    print(f"✅ User read: {user_id}")
                    results["read"] = True

                    # UPDATE
                    update_data = {"first_name": "Updated Test"}
                    response = self.session.put(
                        f"{API_BASE}/users/{user_id}", json=update_data)
                    if response.status_code == 200:
                        print(f"✅ User updated: {user_id}")
                        results["update"] = True

                        # DELETE
                        response = self.session.delete(
                            f"{API_BASE}/users/{user_id}")
                        if response.status_code == 200:
                            print(f"✅ User deleted: {user_id}")
                            results["delete"] = True
                        else:
                            print(
                                f"❌ User delete failed: {response.status_code}")
                    else:
                        print(f"❌ User update failed: {response.status_code}")
                else:
                    print(f"❌ User read failed: {response.status_code}")
            else:
                print(f"❌ User create failed: {response.status_code}")

        except Exception as e:
            print(f"❌ User CRUD error: {e}")

        return results

    def test_role_crud(self) -> Dict[str, Any]:
        """Test Role CRUD operations"""
        results = {"create": False, "read": False,
                   "update": False, "delete": False}

        try:
            # CREATE
            response = self.session.post(
                f"{API_BASE}/users/roles/", json=TEST_ROLE)
            if response.status_code == 201 or response.status_code == 200:
                role_data = response.json()
                role_id = role_data.get("id")
                print(f"✅ Role created: {role_id}")
                results["create"] = True

                # READ
                response = self.session.get(
                    f"{API_BASE}/users/roles/{role_id}")
                if response.status_code == 200:
                    print(f"✅ Role read: {role_id}")
                    results["read"] = True

                    # UPDATE
                    update_data = {"description": "Updated test role"}
                    response = self.session.put(
                        f"{API_BASE}/users/roles/{role_id}", json=update_data)
                    if response.status_code == 200:
                        print(f"✅ Role updated: {role_id}")
                        results["update"] = True

                        # DELETE
                        response = self.session.delete(
                            f"{API_BASE}/users/roles/{role_id}")
                        if response.status_code == 200:
                            print(f"✅ Role deleted: {role_id}")
                            results["delete"] = True
                        else:
                            print(
                                f"❌ Role delete failed: {response.status_code}")
                    else:
                        print(f"❌ Role update failed: {response.status_code}")
                else:
                    print(f"❌ Role read failed: {response.status_code}")
            else:
                print(f"❌ Role create failed: {response.status_code}")

        except Exception as e:
            print(f"❌ Role CRUD error: {e}")

        return results

    def test_permission_crud(self) -> Dict[str, Any]:
        """Test Permission CRUD operations"""
        results = {"create": False, "read": False,
                   "update": False, "delete": False}

        try:
            # CREATE
            response = self.session.post(
                f"{API_BASE}/users/permissions/", json=TEST_PERMISSION)
            if response.status_code == 201 or response.status_code == 200:
                permission_data = response.json()
                permission_id = permission_data.get("id")
                print(f"✅ Permission created: {permission_id}")
                results["create"] = True

                # READ
                response = self.session.get(
                    f"{API_BASE}/users/permissions/{permission_id}")
                if response.status_code == 200:
                    print(f"✅ Permission read: {permission_id}")
                    results["read"] = True

                    # UPDATE
                    update_data = {"description": "Updated test permission"}
                    response = self.session.put(
                        f"{API_BASE}/users/permissions/{permission_id}", json=update_data)
                    if response.status_code == 200:
                        print(f"✅ Permission updated: {permission_id}")
                        results["update"] = True

                        # DELETE
                        response = self.session.delete(
                            f"{API_BASE}/users/permissions/{permission_id}")
                        if response.status_code == 200:
                            print(f"✅ Permission deleted: {permission_id}")
                            results["delete"] = True
                        else:
                            print(
                                f"❌ Permission delete failed: {response.status_code}")
                    else:
                        print(
                            f"❌ Permission update failed: {response.status_code}")
                else:
                    print(f"❌ Permission read failed: {response.status_code}")
            else:
                print(f"❌ Permission create failed: {response.status_code}")

        except Exception as e:
            print(f"❌ Permission CRUD error: {e}")

        return results

    def test_notification_crud(self) -> Dict[str, Any]:
        """Test Notification CRUD operations"""
        results = {"create": False, "read": False,
                   "update": False, "delete": False}

        try:
            # CREATE
            response = self.session.post(
                f"{API_BASE}/notifications/", json=TEST_NOTIFICATION)
            if response.status_code == 201 or response.status_code == 200:
                notification_data = response.json()
                notification_id = notification_data.get("id")
                print(f"✅ Notification created: {notification_id}")
                results["create"] = True

                # READ
                response = self.session.get(
                    f"{API_BASE}/notifications/{notification_id}")
                if response.status_code == 200:
                    print(f"✅ Notification read: {notification_id}")
                    results["read"] = True

                    # UPDATE
                    update_data = {"title": "Updated Test Notification"}
                    response = self.session.put(
                        f"{API_BASE}/notifications/{notification_id}", json=update_data)
                    if response.status_code == 200:
                        print(f"✅ Notification updated: {notification_id}")
                        results["update"] = True

                        # DELETE
                        response = self.session.delete(
                            f"{API_BASE}/notifications/{notification_id}")
                        if response.status_code == 200:
                            print(f"✅ Notification deleted: {notification_id}")
                            results["delete"] = True
                        else:
                            print(
                                f"❌ Notification delete failed: {response.status_code}")
                    else:
                        print(
                            f"❌ Notification update failed: {response.status_code}")
                else:
                    print(
                        f"❌ Notification read failed: {response.status_code}")
            else:
                print(f"❌ Notification create failed: {response.status_code}")

        except Exception as e:
            print(f"❌ Notification CRUD error: {e}")

        return results

    def test_messaging_crud(self) -> Dict[str, Any]:
        """Test Messaging CRUD operations"""
        results = {"create": False, "read": False,
                   "update": False, "delete": False}

        try:
            # CREATE Conversation
            response = self.session.post(
                f"{API_BASE}/messaging/conversations", json=TEST_CONVERSATION)
            if response.status_code == 201 or response.status_code == 200:
                conversation_data = response.json()
                conversation_id = conversation_data.get("id")
                print(f"✅ Conversation created: {conversation_id}")
                results["create"] = True

                # READ Conversation
                response = self.session.get(
                    f"{API_BASE}/messaging/conversations/{conversation_id}")
                if response.status_code == 200:
                    print(f"✅ Conversation read: {conversation_id}")
                    results["read"] = True

                    # CREATE Message
                    message_data = {"content": "Test message",
                                    "conversation_id": conversation_id}
                    response = self.session.post(
                        f"{API_BASE}/messaging/conversations/{conversation_id}/messages", json=message_data)
                    if response.status_code == 201 or response.status_code == 200:
                        message_data = response.json()
                        message_id = message_data.get("id")
                        print(f"✅ Message created: {message_id}")

                        # UPDATE Message
                        update_data = {"content": "Updated test message"}
                        response = self.session.put(
                            f"{API_BASE}/messaging/messages/{message_id}", json=update_data)
                        if response.status_code == 200:
                            print(f"✅ Message updated: {message_id}")
                            results["update"] = True

                            # DELETE Message
                            response = self.session.delete(
                                f"{API_BASE}/messaging/messages/{message_id}")
                            if response.status_code == 200:
                                print(f"✅ Message deleted: {message_id}")

                                # DELETE Conversation
                                response = self.session.delete(
                                    f"{API_BASE}/messaging/conversations/{conversation_id}")
                                if response.status_code == 200:
                                    print(
                                        f"✅ Conversation deleted: {conversation_id}")
                                    results["delete"] = True
                                else:
                                    print(
                                        f"❌ Conversation delete failed: {response.status_code}")
                            else:
                                print(
                                    f"❌ Message delete failed: {response.status_code}")
                        else:
                            print(
                                f"❌ Message update failed: {response.status_code}")
                    else:
                        print(
                            f"❌ Message create failed: {response.status_code}")
                else:
                    print(
                        f"❌ Conversation read failed: {response.status_code}")
            else:
                print(f"❌ Conversation create failed: {response.status_code}")

        except Exception as e:
            print(f"❌ Messaging CRUD error: {e}")

        return results

    def test_file_crud(self) -> Dict[str, Any]:
        """Test File CRUD operations"""
        results = {"create": False, "read": False,
                   "update": False, "delete": False}

        try:
            # CREATE (Upload file)
            test_file_content = "name,age,city\nJohn,25,New York\nJane,30,Los Angeles"
            files = {"file": ("test.csv", test_file_content, "text/csv")}
            response = self.session.post(
                f"{API_BASE}/files/upload", files=files)

            if response.status_code == 201 or response.status_code == 200:
                file_data = response.json()
                file_id = file_data.get("id")
                print(f"✅ File uploaded: {file_id}")
                results["create"] = True

                # READ
                response = self.session.get(f"{API_BASE}/files/{file_id}")
                if response.status_code == 200:
                    print(f"✅ File read: {file_id}")
                    results["read"] = True

                    # UPDATE
                    update_data = {"original_filename": "updated_test.csv"}
                    response = self.session.put(
                        f"{API_BASE}/files/{file_id}", json=update_data)
                    if response.status_code == 200:
                        print(f"✅ File updated: {file_id}")
                        results["update"] = True

                        # DELETE
                        response = self.session.delete(
                            f"{API_BASE}/files/{file_id}")
                        if response.status_code == 200:
                            print(f"✅ File deleted: {file_id}")
                            results["delete"] = True
                        else:
                            print(
                                f"❌ File delete failed: {response.status_code}")
                    else:
                        print(f"❌ File update failed: {response.status_code}")
                else:
                    print(f"❌ File read failed: {response.status_code}")
            else:
                print(f"❌ File upload failed: {response.status_code}")

        except Exception as e:
            print(f"❌ File CRUD error: {e}")

        return results

    def run_all_tests(self):
        """Run all CRUD tests"""
        print("🚀 Starting Comprehensive CRUD Tests...")
        print("=" * 60)

        # Test health first
        if not self.test_health():
            print("❌ Health check failed. Stopping tests.")
            return

        # Login (you'll need to create a test user first)
        if not self.login("admin", "admin"):
            print("⚠️  Login failed. Some tests may fail due to authentication.")

        print("\n📋 Running CRUD Tests...")
        print("-" * 60)

        # Test all CRUD operations
        self.test_results = {
            "users": self.test_user_crud(),
            "roles": self.test_role_crud(),
            "permissions": self.test_permission_crud(),
            "notifications": self.test_notification_crud(),
            "messaging": self.test_messaging_crud(),
            "files": self.test_file_crud()
        }

        # Print summary
        print("\n📊 Test Results Summary")
        print("=" * 60)

        for module, results in self.test_results.items():
            passed = sum(1 for result in results.values() if result)
            total = len(results)
            status = "✅ PASS" if passed == total else "❌ FAIL"
            print(f"{module.upper():12} | {passed}/{total} | {status}")

            for operation, success in results.items():
                status = "✅" if success else "❌"
                print(f"  {operation:8} | {status}")


if __name__ == "__main__":
    tester = CRUDTester()
    tester.run_all_tests()
