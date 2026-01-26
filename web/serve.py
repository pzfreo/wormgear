#!/usr/bin/env python3
"""
Development server for wormgear web interface.

Serves the built site from /dist/ directory.
Run 'bash web/build.sh' before starting the server.
"""

import sys
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler


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

        # Disable caching for development
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')

        super().end_headers()

    def do_OPTIONS(self):
        """Handle preflight requests."""
        self.send_response(200)
        self.end_headers()


def run_server(port=8000):
    """Run the development server."""

    # Change to the dist/ directory (the built site)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    dist_dir = os.path.join(project_root, 'dist')

    if not os.path.exists(dist_dir):
        print(f"❌ Error: dist/ directory not found at: {dist_dir}")
        print(f"")
        print(f"Please run the build script first:")
        print(f"    cd {project_root}")
        print(f"    bash web/build.sh")
        sys.exit(1)

    os.chdir(dist_dir)

    print(f"📁 Serving from: {dist_dir}")

    server_address = ('', port)
    httpd = HTTPServer(server_address, CORSRequestHandler)

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  Worm Gear 3D Web Interface - Development Server            ║
╚══════════════════════════════════════════════════════════════╝

📍 Server running at:

    http://localhost:{port}/

🌐 Access from network:

    http://<your-ip>:{port}/

💡 Usage:
    - Open the URL above in your browser
    - Modify files in /web/ or /src/
    - Run 'bash web/build.sh' to rebuild
    - Refresh browser to see changes

📁 Serving:
    {dist_dir}

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
