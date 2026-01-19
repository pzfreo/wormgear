#!/usr/bin/env python3
"""
Simple HTTP server for local development of the web interface.

This server enables CORS headers and serves both the web interface
and the parent directory (for accessing ../examples/ and ../src/).

Usage:
    python3 serve.py [port]

Default port: 8000
"""

import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os


class CORSRequestHandler(SimpleHTTPRequestHandler):
    """HTTP request handler with CORS headers enabled."""

    def end_headers(self):
        # Enable CORS for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

        # Enable proper MIME types for Pyodide
        self.send_header('Cross-Origin-Opener-Policy', 'same-origin')
        self.send_header('Cross-Origin-Embedder-Policy', 'require-corp')

        super().end_headers()

    def do_OPTIONS(self):
        """Handle preflight requests."""
        self.send_response(200)
        self.end_headers()


def run_server(port=8000):
    """Run the development server."""

    # Change to the web directory
    web_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(web_dir)

    server_address = ('', port)
    httpd = HTTPServer(server_address, CORSRequestHandler)

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  Worm Gear 3D Web Interface - Development Server            ║
╚══════════════════════════════════════════════════════════════╝

📍 Server running at:

    http://localhost:{port}

🌐 Access from network:

    http://<your-ip>:{port}

💡 Usage:
    - Open the URL above in your browser
    - Test with sample designs or upload JSON
    - Check browser console for detailed logs

⌨️  Press Ctrl+C to stop the server

""")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped. Goodbye!")
        sys.exit(0)


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)
