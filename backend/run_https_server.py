#!/usr/bin/env python3
"""
Custom Django development server with HTTPS support
"""
import os
import sys
import django
from django.core.management import execute_from_command_line
from django.core.servers.basehttp import WSGIServer
from django.core.wsgi import get_wsgi_application
from wsgiref.simple_server import make_server
import ssl
import tempfile
import subprocess


def create_self_signed_cert():
    """Create a self-signed certificate for development"""
    try:
        # Create temporary directory for certificates
        cert_dir = tempfile.mkdtemp()
        cert_file = os.path.join(cert_dir, 'cert.pem')
        key_file = os.path.join(cert_dir, 'key.pem')

        # Generate self-signed certificate
        subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:4096',
            '-keyout', key_file, '-out', cert_file, '-days', '365', '-nodes',
            '-subj', '/C=US/ST=State/L=City/O=Organization/CN=localhost'
        ], check=True, capture_output=True)

        return cert_file, key_file
    except Exception as e:
        print(f"Warning: Could not create SSL certificate: {e}")
        print("HTTPS will not be available. Using HTTP only.")
        return None, None


def run_https_server():
    """Run Django server with HTTPS support"""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    django.setup()

    # Create self-signed certificate
    cert_file, key_file = create_self_signed_cert()

    # Get WSGI application
    application = get_wsgi_application()

    if cert_file and key_file:
        # Create HTTPS server
        server = make_server('127.0.0.1', 8443, application)

        # Wrap with SSL
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)

        server.socket = context.wrap_socket(server.socket, server_side=True)

        print("🚀 Starting Django development server...")
        print("📡 HTTP:  http://127.0.0.1:8000/")
        print("🔒 HTTPS: https://127.0.0.1:8443/")
        print("⚠️  Note: HTTPS uses self-signed certificate (browser will show warning)")
        print("   Click 'Advanced' and 'Proceed to localhost' to continue")
        print("\n🎯 API Endpoints:")
        print("   HTTP:  http://127.0.0.1:8000/api/health/")
        print("   HTTPS: https://127.0.0.1:8443/api/health/")
        print("\nPress Ctrl+C to stop the server")

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Server stopped")
        finally:
            # Clean up certificate files
            try:
                os.remove(cert_file)
                os.remove(key_file)
                os.rmdir(os.path.dirname(cert_file))
            except:
                pass
    else:
        print("❌ Could not create SSL certificate. Running HTTP only.")
        print("📡 HTTP: http://127.0.0.1:8000/")
        execute_from_command_line(['manage.py', 'runserver', '127.0.0.1:8000'])


if __name__ == "__main__":
    run_https_server()
