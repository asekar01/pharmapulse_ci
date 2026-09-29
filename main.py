"""
PharmaPulse CI — Main Application Entry Point
=============================================
Run with: python main.py
"""

import sys
import os

# Ensure backend package can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.server import run_server

if __name__ == "__main__":
    run_server(port=8500, open_browser=True)
