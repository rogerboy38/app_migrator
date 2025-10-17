#!/usr/bin/env python3
"""
Cleanup Orphaned App References
Fixes issues with missing app modules preventing bench operations
"""

import os
import json
import re
import glob
from pathlib import Path

def cleanup_orphaned_apps():
    """Remove all references to non-existent apps from Frappe configuration"""
    
    bench_path = Path(__file__).parent.parent.parent
    sites_path = bench_path / "sites"
    
    problematic_apps = ["rnd_nutrition_fixed_v6"]
    
    print("🧹 Cleaning up orphaned app references...")
    
    # 1. Clean site_config.json files
    site_config_files = list(sites_path.glob("*/site_config.json"))
    for config_file in site_config_files:
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            modified = False
            
            # Remove from installed_apps if present
            if 'installed_apps' in config:
                original_count = len(config['installed_apps'])
                config['installed_apps'] = [app for app in config['installed_apps'] 
                                          if app not in problematic_apps]
                if len(config['installed_apps']) != original_count:
                    modified = True
                    print(f"  ✅ Removed orphaned apps from {config_file}")
            
            if modified:
                with open(config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                    
        except Exception as e:
            print(f"  ⚠️  Could not process {config_file}: {e}")
    
    # 2. Clean apps.txt files
    apps_txt_files = list(sites_path.glob("*/apps.txt"))
    for apps_file in apps_txt_files:
        try:
            with open(apps_file, 'r') as f:
                lines = f.readlines()
            
            original_count = len(lines)
            cleaned_lines = [line for line in lines 
                           if line.strip() not in problematic_apps and 
                              not any(app in line for app in problematic_apps)]
            
            if len(cleaned_lines) != original_count:
                with open(apps_file, 'w') as f:
                    f.writelines(cleaned_lines)
                print(f"  ✅ Cleaned orphaned apps from {apps_file}")
                
        except Exception as e:
            print(f"  ⚠️  Could not process {apps_file}: {e}")
    
    # 3. Clean common_site_config.json
    common_config = sites_path / "common_site_config.json"
    if common_config.exists():
        try:
            with open(common_config, 'r') as f:
                config = json.load(f)
            
            modified = False
            
            # Check for any problematic app references in config values
            for key, value in list(config.items()):
                if isinstance(value, str) and any(app in value for app in problematic_apps):
                    del config[key]
                    modified = True
                elif isinstance(value, list):
                    original_len = len(value)
                    config[key] = [item for item in value if item not in problematic_apps]
                    if len(config[key]) != original_len:
                        modified = True
            
            if modified:
                with open(common_config, 'w') as f:
                    json.dump(config, f, indent=2)
                print(f"  ✅ Cleaned common_site_config.json")
                
        except Exception as e:
            print(f"  ⚠️  Could not process common_site_config.json: {e}")
    
    print("🎉 Orphaned app cleanup completed!")

if __name__ == "__main__":
    cleanup_orphaned_apps()
