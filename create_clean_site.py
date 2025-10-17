#!/usr/bin/env python3
"""
Create Clean Site - Bypass Frappe Boot Issues
"""

import os
import json
import sqlite3
from pathlib import Path

def create_clean_site_manual(site_name="clean_test_site", db_name="clean_test.db"):
    bench_path = Path(__file__).parent.parent.parent
    sites_path = bench_path / "sites"
    
    print(f"🔧 Creating clean site manually: {site_name}")
    
    # Create site directory
    site_path = sites_path / site_name
    site_path.mkdir(exist_ok=True)
    
    # Create site_config.json
    site_config = {
        "db_name": db_name,
        "db_password": "test",
        "installed_apps": ["frappe"],
        "maintenance_mode": 0,
        "developer_mode": 1
    }
    
    with open(site_path / "site_config.json", 'w') as f:
        json.dump(site_config, f, indent=2)
    
    # Create apps.txt
    with open(site_path / "apps.txt", 'w') as f:
        f.write("frappe\n")
    
    # Create database file
    db_path = sites_path / db_name
    if not db_path.exists():
        # Create SQLite database
        conn = sqlite3.connect(db_path)
        conn.close()
        print(f"   ✅ Created database: {db_name}")
    
    print(f"   ✅ Created site directory: {site_name}")
    print(f"   ✅ Created site configuration")
    
    return True

if __name__ == "__main__":
    create_clean_site_manual()
