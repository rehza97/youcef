#!/usr/bin/env python3
"""
Test script to debug file upload 422 error
"""

import requests
import os
from pathlib import Path


def test_file_upload():
    """Test file upload endpoint"""
    print("🔍 Testing file upload endpoint...")

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

    # Create a test file
    test_file_path = "test_upload.csv"
    test_content = "name,age,city\nJohn,25,New York\nJane,30,Los Angeles"

    with open(test_file_path, "w") as f:
        f.write(test_content)

    try:
        # Test file upload
        upload_url = "http://127.0.0.1:8000/api/files/upload"
        headers = {
            "Authorization": f"Bearer {token}"
        }

        with open(test_file_path, "rb") as f:
            files = {"file": ("test_upload.csv", f, "text/csv")}

            print(f"📤 Uploading file to: {upload_url}")
            print(f"📁 File: test_upload.csv")
            print(f"🔐 Headers: {headers}")

            response = requests.post(upload_url, files=files, headers=headers)

            print(f"📥 Response status: {response.status_code}")
            print(f"📥 Response headers: {dict(response.headers)}")
            print(f"📥 Response body: {response.text}")

            if response.status_code == 200:
                print("✅ File upload successful!")
                return True
            else:
                print(
                    f"❌ File upload failed with status {response.status_code}")
                return False

    except Exception as e:
        print(f"❌ Upload error: {e}")
        return False
    finally:
        # Clean up test file
        if os.path.exists(test_file_path):
            os.remove(test_file_path)


if __name__ == "__main__":
    test_file_upload()
