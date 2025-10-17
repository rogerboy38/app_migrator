#!/usr/bin/env python3
"""
Diagnose Frappe Boot Issues
Find why Frappe is trying to import non-existent modules during boot
"""

import os
import json
import subprocess
import sys
from pathlib import Path

def run_command(cmd):
    """Run command and return output"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def diagnose_frappe_boot():
    bench_path = Path(__file__).parent.parent.parent
    sites_path = bench_path / "sites"
    
    print("🔍 Diagnosing Frappe Boot Issues...")
    
    # 1. Check default site
    print("\n1. Checking default site configuration...")
    default_site_file = sites_path / "currentsite.txt"
    if default_site_file.exists():
        with open(default_site_file, 'r') as f:
            default_site = f.read().strip()
        print(f"   Default site: {default_site}")
    else:
        print("   No default site file found")
    
    # 2. Check common_site_config.json for default_site
    common_config = sites_path / "common_site_config.json"
    if common_config.exists():
        with open(common_config, 'r') as f:
            config = json.load(f)
        if 'default_site' in config:
            print(f"   common_site_config.json default_site: {config['default_site']}")
    
    # 3. Check environment variables
    print("\n2. Checking environment variables...")
    env_vars = ["FRAPPE_SITE", "DEFAULT_SITE"]
    for var in env_vars:
        if var in os.environ:
            print(f"   {var}: {os.environ[var]}")
    
    # 4. Check Python path and installed packages
    print("\n3. Checking Python environment...")
    stdout, stderr, code = run_command("python -c \"import sys; print('Python path:'); [print(p) for p in sys.path]\"")
    if stdout:
        lines = stdout.split('\n')
        for line in lines[:10]:  # First 10 paths
            if line and 'rnd_nutrition' in line.lower():
                print(f"   ❌ Found rnd_nutrition in Python path: {line}")
    
    # 5. Check for any .pth files
    print("\n4. Checking for .pth files...")
    for python_path in sys.path:
        if os.path.isdir(python_path):
            for item in os.listdir(python_path):
                if item.endswith('.pth'):
                    pth_path = os.path.join(python_path, item)
                    try:
                        with open(pth_path, 'r') as f:
                            content = f.read()
                            if 'rnd_nutrition' in content:
                                print(f"   ❌ Found rnd_nutrition in {pth_path}")
                    except:
                        pass
    
    # 6. Check all site configs for installed_apps
    print("\n5. Checking all site configurations...")
    for config_file in sites_path.glob("*/site_config.json"):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            if 'installed_apps' in config:
                for app in config['installed_apps']:
                    if 'rnd_nutrition' in app:
                        print(f"   ❌ Found {app} in {config_file}")
        except Exception as e:
            print(f"   ⚠️  Could not read {config_file}: {e}")
    
    # 7. Check bench config
    print("\n6. Checking bench configuration...")
    bench_config_path = bench_path / "config"
    if bench_config_path.exists():
        for config_file in bench_config_path.glob("*.json"):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                # Search recursively for rnd_nutrition
                def search_dict(d, path=""):
                    found = []
                    if isinstance(d, dict):
                        for k, v in d.items():
                            new_path = f"{path}.{k}" if path else k
                            if 'rnd_nutrition' in str(k).lower() or 'rnd_nutrition' in str(v).lower():
                                found.append((new_path, v))
                            found.extend(search_dict(v, new_path))
                    elif isinstance(d, list):
                        for i, item in enumerate(d):
                            new_path = f"{path}[{i}]"
                            if 'rnd_nutrition' in str(item).lower():
                                found.append((new_path, item))
                            found.extend(search_dict(item, new_path))
                    return found
                
                found_items = search_dict(config)
                for path, value in found_items:
                    print(f"   ❌ Found rnd_nutrition in {config_file} at {path}: {value}")
            except Exception as e:
                print(f"   ⚠️  Could not read {config_file}: {e}")
    
    print("\n🎯 Diagnosis complete!")

if __name__ == "__main__":
    diagnose_frappe_boot()
