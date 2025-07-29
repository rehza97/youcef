#!/usr/bin/env python3
"""
Test server routes
"""
import requests
import json


def test_server_routes():
    """Test server routes"""
    print("🔍 Testing server routes...")

    base_url = "http://127.0.0.1:8000"

    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Health endpoint: {response.status_code}")
    except Exception as e:
        print(f"❌ Health endpoint error: {e}")

    # Test root endpoint
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ Root endpoint: {response.status_code}")
    except Exception as e:
        print(f"❌ Root endpoint error: {e}")

    # Test API info endpoint
    try:
        response = requests.get(f"{base_url}/api/info")
        print(f"✅ API info endpoint: {response.status_code}")
    except Exception as e:
        print(f"❌ API info endpoint error: {e}")

    # Test OpenAPI docs
    try:
        response = requests.get(f"{base_url}/docs")
        print(f"✅ OpenAPI docs: {response.status_code}")
    except Exception as e:
        print(f"❌ OpenAPI docs error: {e}")

    # Test WebSocket endpoint (should return 405 Method Not Allowed for GET)
    try:
        response = requests.get(f"{base_url}/ws/notifications/1/")
        print(f"✅ WebSocket endpoint (GET): {response.status_code}")
    except Exception as e:
        print(f"❌ WebSocket endpoint error: {e}")


if __name__ == "__main__":
    test_server_routes()
