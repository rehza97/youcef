#!/usr/bin/env python3
"""
Simple HTTP server for testing
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json


class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response = {
            "status": "ok",
            "message": "Simple server is working!",
            "path": self.path
        }

        self.wfile.write(json.dumps(response).encode())


def run_server():
    server_address = ('127.0.0.1', 8002)
    httpd = HTTPServer(server_address, SimpleHandler)
    print(f"Starting simple server on http://127.0.0.1:8002")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
