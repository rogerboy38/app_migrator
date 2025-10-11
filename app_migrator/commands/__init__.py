"""App Migrator Commands"""

from .fix_app import fix_app

# Only register our working fix_app command for now
commands = [
    fix_app
]

__all__ = ["commands"]
