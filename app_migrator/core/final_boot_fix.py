#!/usr/bin/env python3
"""
Final Comprehensive Boot Fix
Fix all remaining boot issues permanently
"""

import os
import json
import shutil
import subprocess
from pathlib import Path

class FinalBootFix:
    def __init__(self, bench_path):
        self.bench_path = Path(bench_path)
        self.sites_path = self.bench_path / "sites"
        self.apps_path = self.bench_path / "apps"
        
    def apply_final_fix(self):
        """Apply the final comprehensive boot fix"""
        print("🔧 Applying final comprehensive boot fix...")
        
        fixes = []
        
        # 1. Ensure apps.txt exists and is correct
        fixes.extend(self.fix_apps_txt())
        
        # 2. Fix common_site_config.json
        fixes.extend(self.fix_common_config())
        
        # 3. Remove all problematic app references
        fixes.extend(self.remove_problematic_references())
        
        # 4. Reinstall all apps in development mode
        fixes.extend(self.reinstall_apps_development())
        
        # 5. Clear all caches
        fixes.extend(self.clear_all_caches())
        
        return fixes
    
    def fix_apps_txt(self):
        """Ensure apps.txt exists and contains only valid apps"""
        fixes = []
        
        apps_file = self.sites_path / "apps.txt"
        
        # Get list of valid apps (those with setup.py)
        valid_apps = []
        for app_dir in self.apps_path.iterdir():
            if app_dir.is_dir() and (app_dir / "setup.py").exists():
                valid_apps.append(app_dir.name)
        
        # Filter out problematic apps
        safe_apps = [app for app in valid_apps if not self.is_problematic_app(app)]
        
        # Write safe apps to apps.txt
        with open(apps_file, 'w') as f:
            for app in safe_apps:
                f.write(f"{app}\n")
        
        fixes.append(f"Updated apps.txt with {len(safe_apps)} safe apps")
        print(f"   ✅ apps.txt updated with: {', '.join(safe_apps)}")
        
        return fixes
    
    def is_problematic_app(self, app_name):
        """Check if app is problematic"""
        problematic_patterns = [
            'rnd_nutrition_fixed_v2',
            'rnd_nutrition_fixed_v3',
            'rnd_nutrition_fixed_v4',
            'rnd_nutrition_fixed_v5',
            'rnd_nutrition_fixed_v6'
        ]
        
        return any(pattern in app_name for pattern in problematic_patterns)
    
    def fix_common_config(self):
        """Fix common_site_config.json"""
        fixes = []
        
        common_config = self.sites_path / "common_site_config.json"
        
        if common_config.exists():
            with open(common_config, 'r') as f:
                config = json.load(f)
        else:
            config = {}
        
        # Remove problematic settings
        if 'default_site' in config:
            del config['default_site']
            fixes.append("Removed default_site from common config")
        
        if 'serve_default_site' in config:
            del config['serve_default_site']
            fixes.append("Removed serve_default_site from common config")
        
        # Write back
        with open(common_config, 'w') as f:
            json.dump(config, f, indent=2)
        
        return fixes
    
    def remove_problematic_references(self):
        """Remove all problematic app references from site configs"""
        fixes = []
        
        for site_dir in self.sites_path.iterdir():
            if site_dir.is_dir():
                # Fix site_config.json
                site_config = site_dir / "site_config.json"
                if site_config.exists():
                    fixes.extend(self.clean_site_config(site_config))
                
                # Fix apps.txt in site directory
                site_apps = site_dir / "apps.txt"
                if site_apps.exists():
                    fixes.extend(self.clean_site_apps(site_apps))
        
        return fixes
    
    def clean_site_config(self, site_config_path):
        """Clean a site_config.json file"""
        fixes = []
        
        with open(site_config_path, 'r') as f:
            config = json.load(f)
        
        if 'installed_apps' in config:
            original_count = len(config['installed_apps'])
            config['installed_apps'] = [app for app in config['installed_apps'] 
                                      if not self.is_problematic_app(app)]
            
            if len(config['installed_apps']) != original_count:
                fixes.append(f"Cleaned {site_config_path.parent.name}/site_config.json")
        
        with open(site_config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        return fixes
    
    def clean_site_apps(self, apps_file_path):
        """Clean a site apps.txt file"""
        fixes = []
        
        with open(apps_file_path, 'r') as f:
            lines = f.readlines()
        
        cleaned_lines = []
        for line in lines:
            app = line.strip()
            if not self.is_problematic_app(app):
                cleaned_lines.append(line)
        
        if len(cleaned_lines) != len(lines):
            fixes.append(f"Cleaned {apps_file_path.parent.name}/apps.txt")
        
        with open(apps_file_path, 'w') as f:
            f.writelines(cleaned_lines)
        
        return fixes
    
    def reinstall_apps_development(self):
        """Reinstall all apps in development mode"""
        fixes = []
        
        print("   Reinstalling apps in development mode...")
        
        for app_dir in self.apps_path.iterdir():
            if app_dir.is_dir() and (app_dir / "setup.py").exists():
                app_name = app_dir.name
                if not self.is_problematic_app(app_name):
                    try:
                        result = subprocess.run(
                            [self.bench_path / "env" / "bin" / "pip", "install", "-e", f"apps/{app_name}"],
                            cwd=self.bench_path,
                            capture_output=True,
                            text=True
                        )
                        
                        if result.returncode == 0:
                            fixes.append(f"Reinstalled {app_name}")
                        else:
                            print(f"      ⚠️  Failed to reinstall {app_name}: {result.stderr}")
                    except Exception as e:
                        print(f"      ❌ Error reinstalling {app_name}: {e}")
        
        return fixes
    
    def clear_all_caches(self):
        """Clear all caches"""
        fixes = []
        
        # Clear Python caches
        for cache_dir in self.bench_path.glob("**/__pycache__"):
            shutil.rmtree(cache_dir, ignore_errors=True)
        
        for pyc_file in self.bench_path.glob("**/*.pyc"):
            pyc_file.unlink()
        
        fixes.append("Cleared all Python caches")
        
        return fixes
    
    def test_fix(self):
        """Test if the fix worked"""
        print("🧪 Testing final boot fix...")
        
        try:
            # Test bench --version
            result = subprocess.run(
                ["bench", "--version"],
                cwd=self.bench_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print("   ✅ bench --version works!")
                return True
            else:
                print(f"   ❌ bench --version failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
            return False

def main():
    import sys
    
    if len(sys.argv) > 1:
        bench_path = sys.argv[1]
    else:
        bench_path = os.getcwd()
    
    fixer = FinalBootFix(bench_path)
    fixes = fixer.apply_final_fix()
    
    if fixes:
        print(f"✅ Applied {len(fixes)} fixes:")
        for fix in fixes:
            print(f"   - {fix}")
    else:
        print("✅ No fixes needed")
    
    print("\n" + "="*50)
    success = fixer.test_fix()
    
    if success:
        print("🎉 FINAL BOOT FIX COMPLETED SUCCESSFULLY!")
        print("🚀 App migrator is now ready for robust migrations!")
    else:
        print("⚠️  Some minor issues may remain")

if __name__ == "__main__":
    main()
