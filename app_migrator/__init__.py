"""
App Migrator Package
Reads version from root package
"""

import os
import sys

# Add parent directory to path to import root package
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import version from root
try:
    from app_migrator import __version__
except ImportError:
    __version__ = "5.5.0"  # Fallback

app_name = "app_migrator"
