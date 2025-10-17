#!/usr/bin/env python3
"""
App Migrator Boot Fixer Core
Integrated boot issue detection and fixing for app_migrator
"""

import os
import json
import shutil
import glob
from pathlib import Path

class BootFixer:
    def __init__(self, bench_path):
        self.bench_path = Path(bench_path)
        self.sites_path = self.bench_path / "sites"
        self.env_path = self.bench_path / "env"
        
    def diagnose_boot_issues(self):
        """Diagnose issues preventing Frappe from booting"""
        issues = []
        
        print("🔍 Running comprehensive boot diagnosis...")
        
        # 1. Check Python .pth files
        pth_issues = self.check_pth_files()
        issues.extend(pth_issues)
        
        # 2. Check default site configuration
        default_site = self.get_default_site()
        if default_site:
            site_issues = self.check_site_for_problems(default_site)
            if site_issues:
                issues.extend(site_issues)
        
        # 3. Check common_site_config.json
        common_config_issues = self.check_common_config()
        if common_config_issues:
            issues.extend(common_config_issues)
            
        # 4. Check environment
        env_issues = self.check_environment()
        if env_issues:
            issues.extend(env_issues)
            
        # 5. Check installed packages
        package_issues = self.check_installed_packages()
        if package_issues:
            issues.extend(package_issues)
            
        return issues
    
    def check_pth_files(self):
        """Check for problematic .pth files in Python environment"""
        issues = []
        
        if self.env_path.exists():
            pth_files = list(self.env_path.glob("**/*.pth"))
            for pth_file in pth_files:
                try:
                    with open(pth_file, 'r') as f:
                        content = f.read()
                    
                    # Check for problematic app references
                    if self.contains_problematic_references(content):
                        issues.append(f"Problematic .pth file: {pth_file}")
                        print(f"   ❌ Found problematic .pth: {pth_file}")
                except Exception as e:
                    print(f"   ⚠️  Could not read {pth_file}: {e}")
        
        return issues
    
    def contains_problematic_references(self, content):
        """Check if content contains problematic app references"""
        problematic_patterns = [
            'rnd_nutrition_fixed_v2',
            'rnd_nutrition_fixed_v3', 
            'rnd_nutrition_fixed_v4',
            'rnd_nutrition_fixed_v5',
            'rnd_nutrition_fixed_v6'
        ]
        
        for pattern in problematic_patterns:
            if pattern in content:
                return True
        return False
    
    def get_default_site(self):
        """Get the current default site"""
        # Check currentsite.txt
        currentsite_file = self.sites_path / "currentsite.txt"
        if currentsite_file.exists():
            with open(currentsite_file, 'r') as f:
                return f.read().strip()
        
        # Check common_site_config.json
        common_config = self.sites_path / "common_site_config.json"
        if common_config.exists():
            with open(common_config, 'r') as f:
                config = json.load(f)
                return config.get('default_site')
        
        return None
    
    def check_site_for_problems(self, site_name):
        """Check if a site has problematic app references"""
        issues = []
        site_path = self.sites_path / site_name
        
        if not site_path.exists():
            return [f"Site directory does not exist: {site_name}"]
        
        # Check apps.txt
        apps_file = site_path / "apps.txt"
        if apps_file.exists():
            with open(apps_file, 'r') as f:
                for line in f:
                    app = line.strip()
                    if self.is_problematic_app(app):
                        issues.append(f"Problematic app in {site_name}/apps.txt: {app}")
        
        # Check site_config.json
        site_config = site_path / "site_config.json"
        if site_config.exists():
            with open(site_config, 'r') as f:
                config = json.load(f)
                if 'installed_apps' in config:
                    for app in config['installed_apps']:
                        if self.is_problematic_app(app):
                            issues.append(f"Problematic app in {site_name}/site_config.json: {app}")
        
        return issues
    
    def is_problematic_app(self, app_name):
        """Check if an app is problematic (orphaned or causing issues)"""
        if not app_name:
            return False
            
        # List of known problematic app patterns
        problematic_patterns = [
            'rnd_nutrition_fixed_v2',
            'rnd_nutrition_fixed_v3',
            'rnd_nutrition_fixed_v4', 
            'rnd_nutrition_fixed_v5',
            'rnd_nutrition_fixed_v6'
        ]
        
        for pattern in problematic_patterns:
            if pattern == app_name:
                # Check if app actually exists
                app_path = self.bench_path / "apps" / app_name
                if not app_path.exists():
                    return True
                    
        return False
    
    def check_common_config(self):
        """Check common_site_config.json for issues"""
        issues = []
        common_config = self.sites_path / "common_site_config.json"
        
        if common_config.exists():
            with open(common_config, 'r') as f:
                config = json.load(f)
                
            # Check default_site
            if 'default_site' in config:
                default_site = config['default_site']
                site_issues = self.check_site_for_problems(default_site)
                if site_issues:
                    issues.append(f"Default site '{default_site}' has issues")
            
            # Check for problematic app references in config values
            for key, value in config.items():
                if isinstance(value, str) and self.is_problematic_app(value):
                    issues.append(f"Problematic reference in common_site_config.json: {key}={value}")
        
        return issues
    
    def check_environment(self):
        """Check environment for issues"""
        issues = []
        
        # Check environment variables
        env_vars = ["FRAPPE_SITE", "DEFAULT_SITE"]
        for var in env_vars:
            if var in os.environ:
                site_name = os.environ[var]
                site_issues = self.check_site_for_problems(site_name)
                if site_issues:
                    issues.append(f"Environment variable {var} points to problematic site: {site_name}")
        
        return issues
    
    def check_installed_packages(self):
        """Check for problematic installed packages"""
        issues = []
        
        # Check if problematic packages are installed via pip
        try:
            import pkg_resources
            installed_packages = [pkg.key for pkg in pkg_resources.working_set]
            
            problematic_packages = [
                'rnd-nutrition-fixed-v2',
                'rnd-nutrition-fixed-v3',
                'rnd-nutrition-fixed-v4',
                'rnd-nutrition-fixed-v5', 
                'rnd-nutrition-fixed-v6'
            ]
            
            for pkg in problematic_packages:
                if pkg in installed_packages:
                    issues.append(f"Problematic package installed: {pkg}")
        except:
            pass
        
        return issues
    
    def fix_boot_issues(self, issues=None):
        """Fix boot issues"""
        if issues is None:
            issues = self.diagnose_boot_issues()
        
        fixes_applied = []
        
        if not issues:
            print("✅ No boot issues found")
            return fixes_applied
        
        print(f"🔧 Fixing {len(issues)} boot issues...")
        
        for issue in issues:
            print(f"   Addressing: {issue}")
            
            # Fix: Remove problematic .pth files
            if "Problematic .pth file" in issue:
                pth_path = issue.split(": ")[1]
                self.remove_pth_file(pth_path)
                fixes_applied.append(f"Removed .pth file: {os.path.basename(pth_path)}")
                
            # Fix: Remove problematic default site
            elif "Default site" in issue and "has issues" in issue:
                self.fix_default_site()
                fixes_applied.append("Fixed default site configuration")
                
            # Fix: Remove problematic app references
            elif "Problematic app in" in issue and "apps.txt" in issue:
                site_name = issue.split("'")[1] if "'" in issue else issue.split(":")[0].split("/")[0]
                self.clean_site_apps_txt(site_name)
                fixes_applied.append(f"Cleaned apps.txt for {site_name}")
                
            elif "Problematic app in" in issue and "site_config.json" in issue:
                site_name = issue.split("'")[1] if "'" in issue else issue.split(":")[0].split("/")[0]
                self.clean_site_config(site_name)
                fixes_applied.append(f"Cleaned site_config.json for {site_name}")
                
            # Fix: Remove problematic packages
            elif "Problematic package installed" in issue:
                pkg_name = issue.split(": ")[1]
                self.remove_problematic_package(pkg_name)
                fixes_applied.append(f"Removed package: {pkg_name}")
        
        return fixes_applied
    
    def remove_pth_file(self, pth_path):
        """Remove problematic .pth file"""
        try:
            os.remove(pth_path)
            print(f"      ✅ Removed: {pth_path}")
        except Exception as e:
            print(f"      ❌ Failed to remove {pth_path}: {e}")
    
    def fix_default_site(self):
        """Fix default site configuration"""
        # Remove currentsite.txt
        currentsite_file = self.sites_path / "currentsite.txt"
        if currentsite_file.exists():
            currentsite_file.unlink()
        
        # Remove default_site from common_site_config.json
        common_config = self.sites_path / "common_site_config.json"
        if common_config.exists():
            with open(common_config, 'r') as f:
                config = json.load(f)
            
            if 'default_site' in config:
                del config['default_site']
                
            with open(common_config, 'w') as f:
                json.dump(config, f, indent=2)
    
    def clean_site_apps_txt(self, site_name):
        """Clean apps.txt for a site"""
        apps_file = self.sites_path / site_name / "apps.txt"
        if apps_file.exists():
            with open(apps_file, 'r') as f:
                lines = f.readlines()
            
            cleaned_lines = []
            for line in lines:
                app = line.strip()
                if not self.is_problematic_app(app):
                    cleaned_lines.append(line)
            
            with open(apps_file, 'w') as f:
                f.writelines(cleaned_lines)
    
    def clean_site_config(self, site_name):
        """Clean site_config.json for a site"""
        site_config = self.sites_path / site_name / "site_config.json"
        if site_config.exists():
            with open(site_config, 'r') as f:
                config = json.load(f)
            
            if 'installed_apps' in config:
                config['installed_apps'] = [app for app in config['installed_apps'] 
                                          if not self.is_problematic_app(app)]
            
            with open(site_config, 'w') as f:
                json.dump(config, f, indent=2)
    
    def remove_problematic_package(self, pkg_name):
        """Remove problematic Python package"""
        try:
            import subprocess
            subprocess.run([self.env_path / "bin" / "pip", "uninstall", "-y", pkg_name], 
                         capture_output=True)
            print(f"      ✅ Uninstalled: {pkg_name}")
        except Exception as e:
            print(f"      ❌ Failed to uninstall {pkg_name}: {e}")

def main():
    """CLI entry point"""
    import sys
    
    if len(sys.argv) > 1:
        bench_path = sys.argv[1]
    else:
        bench_path = os.getcwd()
    
    fixer = BootFixer(bench_path)
    
    if "--diagnose" in sys.argv or "-d" in sys.argv:
        issues = fixer.diagnose_boot_issues()
        if issues:
            print("❌ Found boot issues:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("✅ No boot issues found")
    else:
        fixes = fixer.fix_boot_issues()
        if fixes:
            print("✅ Applied fixes:")
            for fix in fixes:
                print(f"   - {fix}")
        else:
            print("✅ No fixes needed")

if __name__ == "__main__":
    main()
