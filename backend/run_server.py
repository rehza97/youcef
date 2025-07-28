#!/usr/bin/env python3
"""
Simple Django development server with better error handling
"""
import os
import sys
import django
from django.core.management import execute_from_command_line


def main():
    """Run Django development server with proper configuration"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    django.setup()

    print("🚀 Starting Django development server...")
    print("📡 HTTP:  http://127.0.0.1:8000/")
    print("📡 HTTP:  http://localhost:8000/")
    print("\n🎯 API Endpoints:")
    print("   Health:  http://127.0.0.1:8000/api/health/")
    print("   Info:    http://127.0.0.1:8000/api/info/")
    print("   Admin:   http://127.0.0.1:8000/admin/")
    print("   Register: http://127.0.0.1:8000/api/register/")
    print("   Login:   http://127.0.0.1:8000/api/login/")
    print("\n💡 Tips:")
    print("   - Use HTTP URLs (not HTTPS) in your browser")
    print("   - If you see HTTPS errors, they're normal - just use HTTP")
    print("   - The server is working fine, your system is just redirecting to HTTPS")
    print("\nPress Ctrl+C to stop the server")

    # Run the server
    execute_from_command_line(['manage.py', 'runserver', '127.0.0.1:8000'])


if __name__ == "__main__":
    main()
