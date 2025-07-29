#!/usr/bin/env python3
"""
Comprehensive debug test script for backend and frontend issues
"""
import requests
import json
import os
import asyncio
import websockets
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_backend_health():
    """Test backend health and basic connectivity"""
    print("🔍 Testing backend health...")
    try:
        response = requests.get("http://127.0.0.1:8000/health")
        logger.info(f"Health check response: {response.status_code}")
        logger.info(f"Health check data: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False


def test_authentication():
    """Test authentication flow"""
    print("🔐 Testing authentication...")
    try:
        # Test login
        login_data = {
            "username": "admin",
            "password": "admin123"
        }

        response = requests.post(
            "http://127.0.0.1:8000/api/auth/login",
            json=login_data
        )

        logger.info(f"Login response status: {response.status_code}")
        logger.info(f"Login response: {response.text}")

        if response.status_code == 200:
            token = response.json()["access_token"]
            logger.info(f"✅ Authentication successful, token: {token[:20]}...")
            return token
        else:
            logger.error(f"❌ Authentication failed: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"❌ Authentication error: {e}")
        return None


def test_file_upload(token):
    """Test file upload functionality"""
    print("📁 Testing file upload...")
    try:
        # Create test file
        test_content = "name,age,city\nJohn,25,Paris\nJane,30,London"
        with open("test_debug.csv", "w") as f:
            f.write(test_content)

        # Upload file
        with open("test_debug.csv", "rb") as f:
            files = {"file": ("test_debug.csv", f, "text/csv")}
            headers = {"Authorization": f"Bearer {token}"}

            response = requests.post(
                "http://127.0.0.1:8000/api/files/upload",
                files=files,
                headers=headers
            )

        logger.info(f"Upload response status: {response.status_code}")
        logger.info(f"Upload response: {response.text}")

        # Clean up
        os.remove("test_debug.csv")

        return response.status_code == 200

    except Exception as e:
        logger.error(f"❌ File upload error: {e}")
        return False


async def test_websocket_connection(token):
    """Test WebSocket connection"""
    print("🔌 Testing WebSocket connection...")
    try:
        uri = f"ws://127.0.0.1:8000/ws/notifications/1/?token={token}"
        logger.info(f"Connecting to WebSocket: {uri}")

        async with websockets.connect(uri) as websocket:
            logger.info("✅ WebSocket connection successful")

            # Send ping
            ping_message = {"type": "ping"}
            await websocket.send(json.dumps(ping_message))
            logger.info("📤 Ping sent")

            # Wait for response
            response = await websocket.recv()
            logger.info(f"📥 Response received: {response}")

            # Parse response
            data = json.loads(response)
            logger.info(f"📝 Parsed response: {data}")

            return True

    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")
        return False


def test_api_endpoints(token):
    """Test various API endpoints"""
    print("🌐 Testing API endpoints...")

    endpoints = [
        ("/api/users/", "GET"),
        ("/api/files/", "GET"),
        ("/api/notifications/", "GET"),
        ("/api/health/detailed", "GET"),
    ]

    headers = {"Authorization": f"Bearer {token}"}

    for endpoint, method in endpoints:
        try:
            url = f"http://127.0.0.1:8000{endpoint}"
            logger.info(f"Testing {method} {endpoint}")

            if method == "GET":
                response = requests.get(url, headers=headers)
            else:
                response = requests.post(url, headers=headers)

            logger.info(f"Response status: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"Response error: {response.text}")

        except Exception as e:
            logger.error(f"❌ Error testing {endpoint}: {e}")


def main():
    """Run all tests"""
    print("🚀 Starting comprehensive debug tests...")

    # Test 1: Backend health
    if not test_backend_health():
        print("❌ Backend health check failed")
        return

    # Test 2: Authentication
    token = test_authentication()
    if not token:
        print("❌ Authentication failed")
        return

    # Test 3: API endpoints
    test_api_endpoints(token)

    # Test 4: File upload
    if test_file_upload(token):
        print("✅ File upload test passed")
    else:
        print("❌ File upload test failed")

    # Test 5: WebSocket
    try:
        result = asyncio.run(test_websocket_connection(token))
        if result:
            print("✅ WebSocket test passed")
        else:
            print("❌ WebSocket test failed")
    except Exception as e:
        print(f"❌ WebSocket test error: {e}")

    print("✅ All tests completed!")


if __name__ == "__main__":
    main()
