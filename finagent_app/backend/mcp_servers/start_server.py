"""
Start Yahoo Finance MCP Server

This script starts the Yahoo Finance MCP server in SSE (HTTP) mode
so that agents can connect to it via HTTP instead of stdio.
"""

import subprocess
import sys
from pathlib import Path

def start_server():
    """Start the Yahoo Finance MCP server."""
    
    server_script = Path(__file__).parent / "yahoo_finance_server.py"
    
    print("=" * 80)
    print("Yahoo Finance MCP Server Startup")
    print("=" * 80)
    print()
    print(f"Server script: {server_script}")
    print(f"Endpoint: http://localhost:8001/sse")
    print()
    print("Starting server...")
    print("Press Ctrl+C to stop")
    print("=" * 80)
    print()
    
    # Start server in SSE mode
    try:
        subprocess.run(
            [sys.executable, str(server_script), "--sse"],
            check=True
        )
    except KeyboardInterrupt:
        print()
        print("=" * 80)
        print("Server stopped")
        print("=" * 80)
    except Exception as e:
        print()
        print("=" * 80)
        print(f"Error starting server: {e}")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    start_server()
