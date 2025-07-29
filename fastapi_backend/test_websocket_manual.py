#!/usr/bin/env python3
"""
Manual WebSocket test with authentication
"""
import asyncio
import websockets
import json
import requests


async def test_websocket_with_auth():
    """Test WebSocket with authentication"""
    print("🔌 Manual WebSocket test...")

    # First, get a valid token
    try:
        auth_response = requests.post("http://127.0.0.1:8000/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })

        if auth_response.status_code != 200:
            print(f"❌ Authentication failed: {auth_response.status_code}")
            return False

        token = auth_response.json()["access_token"]
        print(f"✅ Got token: {token[:20]}...")

    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return False

    # Test WebSocket connection with query parameters
    try:
        uri = f"ws://127.0.0.1:8000/ws/notifications/?user_id=1&token={token}"
        print(f"🔗 Connecting to: {uri}")

        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected!")

            # Wait for welcome message
            welcome = await websocket.recv()
            print(f"📥 Welcome message: {welcome}")

            # Send ping
            ping_message = {"type": "ping"}
            await websocket.send(json.dumps(ping_message))
            print("📤 Ping sent")

            # Wait for pong
            pong = await websocket.recv()
            print(f"📥 Pong received: {pong}")

            return True

    except websockets.exceptions.InvalidStatus as e:
        print(f"❌ WebSocket error: {e}")
        print(f"❌ Error type: {type(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print(f"❌ Error type: {type(e)}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_websocket_with_auth())
    if result:
        print("✅ WebSocket test passed!")
    else:
        print("❌ WebSocket test failed!")
