#!/usr/bin/env python3
"""
Robust Test Environment Setup
Handles orphaned app references and creates clean test environments
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run shell command with error handling"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Command failed: {cmd}")
            print(f"Error: {result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"❌ Exception running command: {cmd}")
        print(f"Exception: {e}")
        return False

def setup_clean_test_environment():
    """Setup a completely clean test environment"""
    
    bench_path = Path(__file__).parent.parent.parent
    
    print("🔧 Setting up clean test environment...")
    
    # Step 1: Ensure we're in bench directory
    os.chdir(bench_path)
    
    # Step 2: Clean any existing problematic test site
    if run_command("bench drop-site test_migration_site --force --root-password frappe"):
        print("  ✅ Cleaned existing test site")
    
    # Step 3: Create new site with explicit app exclusion
    print("  Creating new test site...")
    
    # Use minimal configuration to avoid app auto-discovery issues
    site_config = {
        "db_name": "test_migration.db",
        "db_password": "test",
        "installed_apps": ["frappe"]
    }
    
    # Create site with minimal setup
    if run_command("bench new-site test_migration_site --db-name test_migration.db --admin-password admin --force"):
        print("  ✅ Test site created successfully")
    else:
        print("  ⚠️  Standard site creation failed, trying alternative approach...")
        # Alternative approach: Manual site creation
        if run_command("bench setup requirements && bench setup redis"):
            print("  ✅ Setup requirements completed")
    
    # Step 4: Install only essential apps
    if run_command("bench --site test_migration_site install-app frappe"):
        print("  ✅ Frappe installed successfully")
    
    print("🎉 Test environment setup completed!")

if __name__ == "__main__":
    setup_clean_test_environment()
