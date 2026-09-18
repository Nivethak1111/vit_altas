"""
ATLAS / Study Sentinel Server Launcher
Usage:
    python run_server.py [port]
Defaults to port 8080.
"""
import sys
import os
from api.main import run_server

if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    print(f"Starting ATLAS / Study Sentinel on port {port}...")
    run_server(port=port)
