#!/usr/bin/env python3
"""
GHOST v6.0 — Main Entry Point
Grey Hat Operational Security Tool — Generation 6

Usage:
    python ghost.py                     # Start with defaults (port 5000)
    python ghost.py --port 8080         # Custom port
    python ghost.py --model dolphin-mistral  # Custom Ollama model
    python ghost.py --no-browser        # Don't auto-open browser
"""

import argparse
import os
import sys
import webbrowser
import time

# Ensure project root is in path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from backend.server import create_app


BANNER = r"""
   ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗    ██╗   ██╗██████╗    ██████╗
  ██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝    ██║   ██║╚════██╗  ██╔═████╗
  ██║  ███╗███████║██║   ██║███████╗   ██║       ██║   ██║ █████╔╝  ██║██╔██║
  ██║   ██║██╔══██║██║   ██║╚════██║   ██║       ╚██╗ ██╔╝ ╚═══██╗  ████╔╝██║
  ╚██████╔╝██║  ██║╚██████╔╝███████║   ██║        ╚████╔╝ ██████╔╝  ╚██████╔╝
   ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝         ╚═══╝  ╚═════╝    ╚═════╝

  Grey Hat Operational Security Tool — Full Spectrum Capability
  Architecture: Local LLM + Python Bridge + Kali Linux Subsystem
  ─────────────────────────────────────────────────────────────────
  "Maximum capability. Learned restraint. Documented accountability."
"""


def main():
    parser = argparse.ArgumentParser(
        description="GHOST v6.0 — Grey Hat Operational Security Tool"
    )
    parser.add_argument("--port", type=int, default=5000, help="Server port (default: 5000)")
    parser.add_argument("--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--model", default="qwen3:4b", help="Ollama model name (default: qwen3:4b)")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--mode", default="TEACHING",
                        choices=["TEACHING", "SUPERVISED", "AUTONOMOUS", "STEALTH"],
                        help="Initial operational mode (default: TEACHING)")
    parser.add_argument("--shadow", action="store_true", help="Launch in Stealth/Zero-Trace mode (Bypasses UI approval loops)")
    args = parser.parse_args()

    print(BANNER)
    print(f"  PORT: {args.port}")
    print(f"  MODEL: {args.model}")
    print(f"  MODE: {args.mode}")
    print(f"  DEBUG: {args.debug}")
    print()

    # Create app with startup runtime configuration
    app, socketio = create_app(
        BASE_DIR,
        initial_mode=args.mode,
        shadow_mode=args.shadow,
        initial_model=args.model,
    )

    # Open browser after short delay
    if not args.no_browser:
        def open_browser():
            time.sleep(1.5)
            url = f"http://localhost:{args.port}"
            print(f"\n  ▸ Opening dashboard: {url}\n")
            webbrowser.open(url)

        import threading
        threading.Thread(target=open_browser, daemon=True).start()

    # Start server
    print(f"\n  ▸ Server starting on http://{args.host}:{args.port}")
    print("  ▸ Press Ctrl+C to shutdown\n")

    socketio.run(
        app,
        host=args.host,
        port=args.port,
        debug=args.debug,
        allow_unsafe_werkzeug=True,
    )


if __name__ == "__main__":
    main()
