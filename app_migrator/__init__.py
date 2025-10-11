"""
App Migrator v5.0.2 - Ultimate Edition
Merged from V2 (Feature-Rich) + V4 (Enterprise Modular)

Author: MiniMax Agent
License: MIT
"""

__version__ = "5.0.2"

app_name = "app_migrator"
app_title = "App Migrator Ultimate"
app_publisher = "Frappe Community"
app_description = "Ultimate Frappe App Migration System with Enhanced DocType Classification"
app_email = "fcrm@amb-wellness.com"
app_license = "mit"

# Import all commands from modular structure
from .commands import commands

print(f"🚀 App Migrator v{__version__} - Ultimate Edition")
print("✅ Enhanced interactive features with doctype classification loaded!")
