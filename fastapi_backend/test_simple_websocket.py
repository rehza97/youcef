#!/usr/bin/env python3
"""
Test simple WebSocket connection
"""
import asyncio
import websockets
import json


async def test_simple_websocket():
    """Test simple WebSocket connection"""
    print("Testing simple WebSocket...")

    try:
        uri = "ws://127.0.0.1:8000/ws/test"
        print(f"Connecting to: {uri}")

        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connected!")

            # Wait for initial message
            response = await websocket.recv()
            print(f"📥 Initial response: {response}")

            # Send test message
            test_message = {"type": "test", "message": "Hello WebSocket!"}
            await websocket.send(json.dumps(test_message))
            print("📤 Test message sent")

            # Wait for echo
            echo_response = await websocket.recv()
            print(f"📥 Echo response: {echo_response}")

            return True

    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        print(f"❌ Error type: {type(e)}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_simple_websocket())
    if result:
        print("✅ Simple WebSocket test passed")
    else:
        print("❌ Simple WebSocket test failed")
