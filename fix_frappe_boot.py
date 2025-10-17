#!/usr/bin/env python3
"""
Frappe Boot Fixer
Fix issues preventing Frappe from starting due to missing modules
"""

import os
import json
import shutil
from pathlib import Path

def fix_frappe_boot():
    bench_path = Path(__file__).parent.parent.parent
    sites_path = bench_path / "sites"
    
    print("🔧 Fixing Frappe Boot Issues...")
    
    fixes_applied = []
    
    # 1. Remove default site file if it points to problematic site
    default_site_file = sites_path / "currentsite.txt"
    if default_site_file.exists():
        with open(default_site_file, 'r') as f:
            default_site = f.read().strip()
        
        # Check if default site has issues
        site_config = sites_path / default_site / "site_config.json"
        if site_config.exists():
            try:
                with open(site_config, 'r') as f:
                    config = json.load(f)
                
                if 'installed_apps' in config:
                    for app in config['installed_apps']:
                        if 'rnd_nutrition' in app:
                            print(f"   ❌ Default site {default_site} has problematic app: {app}")
                            # Remove default site file
                            default_site_file.unlink()
                            fixes_applied.append(f"Removed default site reference to {default_site}")
                            print(f"   ✅ Removed default site file")
                            break
            except:
                pass
    
    # 2. Clear common_site_config.json default_site if problematic
    common_config = sites_path / "common_site_config.json"
    if common_config.exists():
        with open(common_config, 'r') as f:
            config = json.load(f)
        
        modified = False
        if 'default_site' in config:
            default_site = config['default_site']
            # Check if this site has issues
            site_dir = sites_path / default_site
            if site_dir.exists():
                apps_file = site_dir / "apps.txt"
                if apps_file.exists():
                    with open(apps_file, 'r') as f:
                        apps_content = f.read()
                        if 'rnd_nutrition' in apps_content:
                            del config['default_site']
                            modified = True
                            fixes_applied.append(f"Removed default_site from common_site_config.json")
        
        if modified:
            with open(common_config, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"   ✅ Cleaned common_site_config.json")
    
    # 3. Create a clean default site
    clean_site_name = "clean_default_site"
    clean_site_path = sites_path / clean_site_name
    
    if not clean_site_path.exists():
        print(f"   Creating clean default site: {clean_site_name}")
        
        # Create minimal site directory
        clean_site_path.mkdir(exist_ok=True)
        
        # Create minimal site_config.json
        site_config = {
            "db_name": f"{clean_site_name}.db",
            "db_password": "test",
            "installed_apps": ["frappe"]
        }
        
        with open(clean_site_path / "site_config.json", 'w') as f:
            json.dump(site_config, f, indent=2)
        
        # Create apps.txt with only frappe
        with open(clean_site_path / "apps.txt", 'w') as f:
            f.write("frappe\n")
        
        # Set as default site
        with open(default_site_file, 'w') as f:
            f.write(clean_site_name)
        
        # Update common_site_config.json
        if common_config.exists():
            with open(common_config, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        config['default_site'] = clean_site_name
        
        with open(common_config, 'w') as f:
            json.dump(config, f, indent=2)
        
        fixes_applied.append(f"Created clean default site: {clean_site_name}")
        print(f"   ✅ Created clean default site")
    
    # 4. Clean environment files
    env_files = [
        sites_path / ".env",
        bench_path / ".env"
    ]
    
    for env_file in env_files:
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    content = f.read()
                
                if 'rnd_nutrition' in content:
                    # Backup and remove
                    backup_file = env_file.with_suffix('.env.backup')
                    shutil.copy2(env_file, backup_file)
                    env_file.unlink()
                    fixes_applied.append(f"Removed problematic env file: {env_file}")
                    print(f"   ✅ Removed problematic env file: {env_file}")
            except:
                pass
    
    # 5. Report fixes
    if fixes_applied:
        print(f"\n✅ Applied {len(fixes_applied)} fixes:")
        for fix in fixes_applied:
            print(f"   - {fix}")
    else:
        print(f"\n✅ No fixes needed - system appears clean")
    
    return len(fixes_applied) > 0

if __name__ == "__main__":
    fix_frappe_boot()
