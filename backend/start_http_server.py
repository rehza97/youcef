#!/usr/bin/env python3
"""
Start Django server with explicit HTTP-only configuration
"""
import os
import sys
import django
from django.core.management import execute_from_command_line


def start_http_server():
    """Start Django server with HTTP-only settings"""

    # Set environment variables to force HTTP
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    os.environ['DJANGO_DEBUG'] = 'True'
    os.environ['FORCE_HTTP'] = 'True'

    # Disable any potential HTTPS redirects at environment level
    os.environ['SECURE_SSL_REDIRECT'] = 'False'
    os.environ['SECURE_HSTS_SECONDS'] = '0'

    django.setup()

    print("🚀 Starting HTTP-only Django server...")
    print("📡 Server will run on: http://127.0.0.1:8000")
    print("🔧 CORS enabled for: http://localhost:5175")
    print("💡 This server is configured to prevent HTTPS redirects")
    print("\n🎯 Test endpoints:")
    print("   - http://127.0.0.1:8000/api/test-cors")
    print("   - http://127.0.0.1:8000/api/login/")
    print("   - http://127.0.0.1:8000/api/health/")
    print("\nPress Ctrl+C to stop")

    # Start the server
    sys.argv = ['manage.py', 'runserver', '127.0.0.1:8000', '--insecure']
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    start_http_server()
