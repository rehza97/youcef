#!/usr/bin/env python3
"""
Simple WebSocket test without authentication
"""
import asyncio
import websockets
import json


async def test_websocket_simple():
    """Test WebSocket connection without authentication"""
    print("🔌 Simple WebSocket test...")

    # Test WebSocket connection without token
    uri = "ws://127.0.0.1:8000/ws/notifications/1/"
    print(f"🔗 Connecting to: {uri}")

    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected!")

            # Send ping
            await websocket.send(json.dumps({"type": "ping"}))
            print("📤 Ping sent")

            # Wait for response
            response = await websocket.recv()
            print(f"📥 Response: {response}")

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket connection failed with status {e.status_code}")
        print(f"❌ Headers: {e.headers}")
        print(f"❌ Body: {e.body}")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        print(f"❌ Error type: {type(e)}")

if __name__ == "__main__":
    asyncio.run(test_websocket_simple())
