#!/usr/bin/env python3
"""
Simple API test script to verify endpoints are working
"""
import urllib.request
import json
import sys


def test_api():
    base_url = "http://127.0.0.1:8000"

    endpoints = [
        "/api/health/",
        "/api/info/",
        "/admin/",
    ]

    print("🔍 Testing API endpoints...")
    print("=" * 50)

    for endpoint in endpoints:
        try:
            url = base_url + endpoint
            print(f"Testing: {url}")

            # Create request with proper headers
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'API-Test-Script')

            with urllib.request.urlopen(req, timeout=5) as response:
                status = response.status
                data = response.read().decode('utf-8')

                print(f"✅ Status: {status}")
                print(f"Response: {data[:200]}...")

        except Exception as e:
            print(f"❌ Error: {e}")

        print("-" * 30)

    print("\n🎉 API test completed!")


if __name__ == "__main__":
    test_api()
