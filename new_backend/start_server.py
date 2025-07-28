#!/usr/bin/env python3
"""
Start Django development server with CORS enabled
"""
import os
import sys
import django
from django.core.management import execute_from_command_line


def main():
    """Start Django server with proper configuration"""
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

    # Setup Django
    django.setup()

    print("🚀 Starting New Django Development Server...")
    print("📡 Server will run on: http://127.0.0.1:8000/")
    print("🔧 CORS is enabled for development")
    print("🌐 Allowed origins: localhost:5173, localhost:5174, etc.")
    print("\n📋 Available endpoints:")
    print("   • Health:  http://127.0.0.1:8000/api/health/")
    print("   • Login:   http://127.0.0.1:8000/api/login/")
    print("   • Register: http://127.0.0.1:8000/api/register/")
    print("   • Admin:   http://127.0.0.1:8000/admin/")
    print("\n💡 Frontend should connect to: http://127.0.0.1:8000/")
    print("   (Make sure frontend/api.js has the correct port)")
    print("\n⏹️  Press Ctrl+C to stop the server")
    print("=" * 60)

    # Start the server
    execute_from_command_line(['manage.py', 'runserver', '127.0.0.1:8000'])


if __name__ == "__main__":
    main()
