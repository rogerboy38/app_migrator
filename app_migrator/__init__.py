"""
App Migrator - Enterprise Multi-Bench Migration System
Main module with command registration
"""

import click
import frappe
import os
import subprocess
from frappe.utils import get_sites

__version__ = "4.0.0"
app_name = "app_migrator"

print("🚀 App Migrator v4.0.0 - Enterprise Ready!")

# ========== BASIC FUNCTIONS ==========
def detect_available_benches():
    """Detect all available benches"""
    benches = []
    frappe_home = os.path.expanduser('~')
    for item in os.listdir(frappe_home):
        if item.startswith('frappe-bench') and os.path.isdir(os.path.join(frappe_home, item)):
            benches.append(item)
    return sorted(benches)

@click.command('migrate-app')
@click.argument('action')
def migrate_app(action):
    """🚀 App Migrator - Enterprise Multi-Bench Migration System"""
    print(f"🚀 App Migrator: {action}")
    
    if action == 'list-benches':
        benches = detect_available_benches()
        print("🏗️ AVAILABLE BENCHES:")
        for i, bench in enumerate(benches, 1):
            print(f"   {i}. {bench}")
    elif action == 'test':
        print("✅ App Migrator is working!")
    else:
        print(f"❌ Unknown action: {action}")
        print("Available: list-benches, test")

# Frappe requires this commands list
commands = [migrate_app]

print("✅ App Migrator commands registered successfully!")
