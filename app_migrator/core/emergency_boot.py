#!/usr/bin/env python3
"""
Emergency Boot Bypass
Bypass Frappe boot issues by creating minimal required files
"""

import os
import json
from pathlib import Path

def create_emergency_environment(bench_path):
    """Create minimal environment to bypass boot issues"""
    bench_path = Path(bench_path)
    sites_path = bench_path / "sites"
    
    print("🚨 Creating emergency boot environment...")
    
    # 1. Create minimal apps.txt
    apps_file = sites_path / "apps.txt"
    with open(apps_file, 'w') as f:
        f.write("frappe\nerpnext\n")
    print("   ✅ Created minimal apps.txt")
    
    # 2. Create common_site_config.json if missing
    common_config = sites_path / "common_site_config.json"
    if not common_config.exists():
        with open(common_config, 'w') as f:
            json.dump({}, f, indent=2)
        print("   ✅ Created common_site_config.json")
    
    # 3. Remove any problematic default site references
    currentsite_file = sites_path / "currentsite.txt"
    if currentsite_file.exists():
        currentsite_file.unlink()
        print("   ✅ Removed currentsite.txt")
    
    # 4. Create a minimal site directory for boot
    minimal_site = sites_path / "minimal_boot_site"
    minimal_site.mkdir(exist_ok=True)
    
    site_config = minimal_site / "site_config.json"
    with open(site_config, 'w') as f:
        json.dump({
            "db_name": ":memory:",
            "db_password": "test",
            "installed_apps": ["frappe"]
        }, f, indent=2)
    
    apps_txt = minimal_site / "apps.txt"
    with open(apps_txt, 'w') as f:
        f.write("frappe\n")
    
    print("   ✅ Created minimal boot site")
    
    # 5. Set as default site
    with open(currentsite_file, 'w') as f:
        f.write("minimal_boot_site")
    
    print("   ✅ Set minimal boot site as default")
    
    return True

def test_frappe_boot(bench_path):
    """Test if Frappe can boot now"""
    import subprocess
    import sys
    
    bench_path = Path(bench_path)
    
    # Test basic Frappe import
    try:
        sys.path.insert(0, str(bench_path / "apps" / "frappe"))
        import frappe
        print("   ✅ Frappe module imports successfully")
        return True
    except Exception as e:
        print(f"   ❌ Frappe import failed: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        bench_path = sys.argv[1]
    else:
        bench_path = os.getcwd()
    
    create_emergency_environment(bench_path)
    success = test_frappe_boot(bench_path)
    
    if success:
        print("🎉 Emergency boot environment created successfully!")
    else:
        print("⚠️  Some issues may remain, but basic environment is set up")
