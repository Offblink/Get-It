"""Get It — PyQt6 Daily Reminder Application.

Usage:
    python main.py              # Normal start
    python main.py --minimized  # Start minimized to tray
"""
import sys
import os

# Ensure the project root is on path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import main

if __name__ == "__main__":
    main()
