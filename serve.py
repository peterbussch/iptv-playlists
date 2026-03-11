#!/usr/bin/env python3
"""Serve IPTV playlists on the local network for Apple TV / iPlayTV.

Usage:
    python3 serve.py          # start on port 8642
    python3 serve.py 9000     # custom port

Then in iPlayTV on your Apple TV, add a playlist:
    http://<your-mac-ip>:8642/post-soviet-tv.m3u
    http://<your-mac-ip>:8642/us-tv.m3u
"""

import http.server
import os
import socket
import sys
from pathlib import Path

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8642

# Serve from output/ if it exists (consolidated layout), else current dir
SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
SERVE_DIR = str(OUTPUT_DIR if OUTPUT_DIR.exists() else SCRIPT_DIR)


def get_local_ip():
    """Get the Mac's LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


class M3UHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that serves .m3u/.m3u8 with correct MIME types."""

    # iPlayTV needs proper content-type or it rejects the playlist
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".m3u": "audio/mpegurl",
        ".m3u8": "application/vnd.apple.mpegurl",
    }

    def end_headers(self):
        # Allow cross-origin requests (some IPTV apps need this)
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, format, *args):
        # Cleaner logging
        print(f"   {self.address_string()} → {args[0]}")


def main():
    os.chdir(SERVE_DIR)
    ip = get_local_ip()

    playlists = sorted(Path(SERVE_DIR).glob("*.m3u")) + sorted(Path(SERVE_DIR).glob("*.m3u8"))

    print(f"\n📡 IPTV Server running on http://{ip}:{PORT}")
    print(f"   Serving from: {SERVE_DIR}\n")

    if playlists:
        print("   Playlists for iPlayTV:")
        for p in playlists:
            print(f"     http://{ip}:{PORT}/{p.name}")
    else:
        print("   ⚠️  No .m3u files found — run build.py first")

    print(f"\n   Press Ctrl+C to stop.\n")

    # SO_REUSEADDR lets us restart immediately without "Address already in use"
    http.server.HTTPServer.allow_reuse_address = True
    httpd = http.server.HTTPServer(("0.0.0.0", PORT), M3UHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")
        httpd.server_close()


if __name__ == "__main__":
    main()
