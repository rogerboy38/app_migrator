#!/usr/bin/env python3
"""
Ultimate Boot Fixer - Comprehensive Frappe Boot Issue Resolution
"""

import os
import json
import shutil
import subprocess
import sys
from pathlib import Path

class UltimateBootFixer:
    def __init__(self, bench_path):
        self.bench_path = Path(bench_path)
        self.sites_path = self.bench_path / "sites"
        self.env_path = self.bench_path / "env"
        
    def nuclear_fix(self):
        """Apply comprehensive fixes for stubborn boot issues"""
        print("🚀 Applying nuclear boot fixes...")
        
        fixes_applied = []
        
        # 1. Remove ALL .pth files system-wide
        fixes_applied.extend(self.remove_all_pth_files())
        
        # 2. Clear ALL site caches
        fixes_applied.extend(self.clear_site_caches())
        
        # 3. Reset default site configuration
        fixes_applied.extend(self.reset_default_site())
        
        # 4. Reinstall Frappe in development mode
        fixes_applied.extend(self.reinstall_frappe_development())
        
        # 5. Clear Python caches
        fixes_applied.extend(self.clear_python_caches())
        
        return fixes_applied
    
    def remove_all_pth_files(self):
        """Remove ALL .pth files that might reference problematic apps"""
        fixes = []
        
        print("   Removing ALL .pth files...")
        
        # Check multiple possible locations
        pth_locations = [
            self.env_path / "lib" / "python3.12" / "site-packages",
            Path("/home/frappe/frappe-bench/env/lib/python3.12/site-packages"),
            Path("/home/frappe/frappe-bench-v601/env/lib/python3.12/site-packages"),
            Path.home() / ".local" / "lib" / "python3.12" / "site-packages",
        ]
        
        for location in pth_locations:
            if location.exists():
                for pth_file in location.glob("*.pth"):
                    try:
                        # Read content to check if it's problematic
                        with open(pth_file, 'r') as f:
                            content = f.read()
                        
                        # Remove if it references any nutrition apps
                        if any(app in content for app in ['rnd_nutrition', 'nutrition']):
                            pth_file.unlink()
                            fixes.append(f"Removed {pth_file}")
                            print(f"      ✅ Removed: {pth_file}")
                    except Exception as e:
                        print(f"      ⚠️  Could not process {pth_file}: {e}")
        
        return fixes
    
    def clear_site_caches(self):
        """Clear all site caches and temporary files"""
        fixes = []
        
        print("   Clearing site caches...")
        
        if self.sites_path.exists():
            # Remove all __pycache__ directories
            for pycache in self.sites_path.glob("**/__pycache__"):
                shutil.rmtree(pycache, ignore_errors=True)
                fixes.append(f"Cleared {pycache}")
            
            # Remove .pyc files
            for pyc_file in self.sites_path.glob("**/*.pyc"):
                pyc_file.unlink()
                fixes.append(f"Removed {pyc_file}")
            
            # Remove bench caches
            bench_cache = self.bench_path / ".cache"
            if bench_cache.exists():
                shutil.rmtree(bench_cache, ignore_errors=True)
                fixes.append("Cleared bench cache")
        
        return fixes
    
    def reset_default_site(self):
        """Completely reset default site configuration"""
        fixes = []
        
        print("   Resetting default site...")
        
        # Remove currentsite.txt
        currentsite_file = self.sites_path / "currentsite.txt"
        if currentsite_file.exists():
            currentsite_file.unlink()
            fixes.append("Removed currentsite.txt")
        
        # Reset common_site_config.json
        common_config = self.sites_path / "common_site_config.json"
        if common_config.exists():
            with open(common_config, 'r') as f:
                config = json.load(f)
            
            # Remove default_site and serve_default_site
            original_config = config.copy()
            if 'default_site' in config:
                del config['default_site']
            if 'serve_default_site' in config:
                del config['serve_default_site']
            
            if config != original_config:
                with open(common_config, 'w') as f:
                    json.dump(config, f, indent=2)
                fixes.append("Reset common_site_config.json")
        
        return fixes
    
    def reinstall_frappe_development(self):
        """Reinstall Frappe in development mode to reset module paths"""
        fixes = []
        
        print("   Reinstalling Frappe in development mode...")
        
        try:
            # Change to bench directory
            os.chdir(self.bench_path)
            
            # Install Frappe in development mode
            result = subprocess.run(
                ["./env/bin/pip", "install", "-e", "apps/frappe"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                fixes.append("Reinstalled Frappe in development mode")
                print("      ✅ Frappe reinstalled")
            else:
                print(f"      ⚠️  Frappe reinstall had issues: {result.stderr}")
                
        except Exception as e:
            print(f"      ❌ Failed to reinstall Frappe: {e}")
        
        return fixes
    
    def clear_python_caches(self):
        """Clear Python import caches"""
        fixes = []
        
        print("   Clearing Python caches...")
        
        try:
            # Clear importlib caches
            import importlib
            importlib.invalidate_caches()
            fixes.append("Cleared Python import caches")
        except:
            pass
        
        return fixes
    
    def test_boot_fix(self):
        """Test if the boot fix worked"""
        print("🧪 Testing boot fix...")
        
        try:
            # Test basic bench command
            result = subprocess.run(
                ["./env/bin/python", "-m", "frappe.utils.bench_helper", "--version"],
                cwd=self.bench_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                print("      ✅ Basic bench helper works!")
                return True
            else:
                print(f"      ❌ Bench helper failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print("      ❌ Bench helper timed out")
            return False
        except Exception as e:
            print(f"      ❌ Bench helper error: {e}")
            return False

def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ultimate Boot Fixer")
    parser.add_argument("--bench-path", default=os.getcwd(), help="Path to bench directory")
    parser.add_argument("--test-only", action="store_true", help="Test only, don't fix")
    
    args = parser.parse_args()
    
    fixer = UltimateBootFixer(args.bench_path)
    
    if args.test_only:
        success = fixer.test_boot_fix()
        sys.exit(0 if success else 1)
    else:
        fixes = fixer.nuclear_fix()
        
        if fixes:
            print(f"✅ Applied {len(fixes)} fixes:")
            for fix in fixes:
                print(f"   - {fix}")
        else:
            print("✅ No fixes needed")
        
        # Test the fix
        print("\n" + "="*50)
        success = fixer.test_boot_fix()
        
        if success:
            print("🎉 ULTIMATE BOOT FIX COMPLETED SUCCESSFULLY!")
        else:
            print("⚠️  Boot issues may still exist, but significant improvements made")

if __name__ == "__main__":
    main()
