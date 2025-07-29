#!/usr/bin/env python3
"""
Test script to check file upload functionality
"""
import requests
import json
import os


def test_file_upload():
    """Test file upload functionality"""
    base_url = "http://127.0.0.1:8000"

    # Test authentication first
    print("🔍 Testing authentication...")
    try:
        auth_response = requests.post(f"{base_url}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })

        if auth_response.status_code == 200:
            token = auth_response.json()["access_token"]
            print("✅ Authentication successful")
        else:
            print(f"❌ Authentication failed: {auth_response.status_code}")
            print(auth_response.text)
            return
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return

    # Test file upload
    print("\n📁 Testing file upload...")
    try:
        # Create a test CSV file
        test_file_content = "name,age,city\nJohn,25,Paris\nJane,30,London"
        with open("test_upload.csv", "w") as f:
            f.write(test_file_content)

        # Upload the file
        with open("test_upload.csv", "rb") as f:
            files = {"file": ("test_upload.csv", f, "text/csv")}
            headers = {"Authorization": f"Bearer {token}"}

            upload_response = requests.post(
                f"{base_url}/api/files/upload",
                files=files,
                headers=headers
            )

        print(f"Upload response status: {upload_response.status_code}")
        print(f"Upload response: {upload_response.text}")

        if upload_response.status_code == 200:
            print("✅ File upload successful")
        else:
            print(f"❌ File upload failed: {upload_response.status_code}")

        # Clean up test file
        os.remove("test_upload.csv")

    except Exception as e:
        print(f"❌ File upload error: {e}")

    # Test WebSocket connection
    print("\n🔌 Testing WebSocket connection...")
    try:
        import websockets
        import asyncio

        async def test_websocket():
            uri = f"ws://127.0.0.1:8000/ws/notifications/1/?token={token}"
            try:
                async with websockets.connect(uri) as websocket:
                    print("✅ WebSocket connection successful")

                    # Send ping
                    await websocket.send(json.dumps({"type": "ping"}))

                    # Wait for pong
                    response = await websocket.recv()
                    print(f"✅ WebSocket response: {response}")

            except Exception as e:
                print(f"❌ WebSocket error: {e}")

        asyncio.run(test_websocket())

    except ImportError:
        print("⚠️ websockets library not installed, skipping WebSocket test")
    except Exception as e:
        print(f"❌ WebSocket test error: {e}")


if __name__ == "__main__":
    print("🚀 Starting file upload and WebSocket tests...")
    test_file_upload()
    print("✅ Tests completed!")
