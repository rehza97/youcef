#!/usr/bin/env python3
"""
Test script for WebSocket functionality
"""
import asyncio
import websockets
import json
import requests

# Test configuration
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"
TEST_USER_ID = 1
TEST_CONVERSATION_ID = 1


async def test_websocket_connection():
    """Test WebSocket connections"""
    print("🧪 Testing WebSocket functionality...")

    # First, get a valid token
    try:
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })

        if login_response.status_code != 200:
            print("❌ Failed to login")
            return

        token_data = login_response.json()
        token = token_data.get("access_token")

        if not token:
            print("❌ No token received")
            return

        print(f"✅ Login successful, token: {token[:20]}...")

    except Exception as e:
        print(f"❌ Login failed: {e}")
        return

    # Test notifications WebSocket
    print("\n📡 Testing notifications WebSocket...")
    try:
        uri = f"{WS_URL}/ws/notifications/{TEST_USER_ID}?token={token}"
        async with websockets.connect(uri) as websocket:
            # Wait for connection message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"✅ Notifications WebSocket connected: {data}")

            # Send ping
            await websocket.send(json.dumps({"type": "ping"}))
            pong = await websocket.recv()
            print(f"✅ Ping/Pong working: {pong}")

    except Exception as e:
        print(f"❌ Notifications WebSocket failed: {e}")

    # Test chat WebSocket
    print("\n💬 Testing chat WebSocket...")
    try:
        uri = f"{WS_URL}/ws/chat/{TEST_CONVERSATION_ID}?token={token}"
        async with websockets.connect(uri) as websocket:
            # Wait for connection message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"✅ Chat WebSocket connected: {data}")

            # Send a test message
            test_message = {
                "type": "message",
                "content": "Hello from WebSocket test!"
            }
            await websocket.send(json.dumps(test_message))
            print("✅ Test message sent")

    except Exception as e:
        print(f"❌ Chat WebSocket failed: {e}")


def test_rest_endpoints():
    """Test REST endpoints"""
    print("\n🌐 Testing REST endpoints...")

    try:
        # Test health endpoint
        health_response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Health check: {health_response.status_code}")

        # Test API info
        info_response = requests.get(f"{BASE_URL}/api/info")
        print(f"✅ API info: {info_response.status_code}")

        if info_response.status_code == 200:
            info = info_response.json()
            print(
                f"📋 WebSocket endpoints: {info.get('websocket_endpoints', [])}")

    except Exception as e:
        print(f"❌ REST endpoints failed: {e}")


async def main():
    """Main test function"""
    print("🚀 Starting FastAPI WebSocket tests...")

    # Test REST endpoints first
    test_rest_endpoints()

    # Test WebSocket connections
    await test_websocket_connection()

    print("\n✅ WebSocket tests completed!")

if __name__ == "__main__":
    asyncio.run(main())
