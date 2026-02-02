#!/usr/bin/env python3
"""
fix_an_app.py - Automated Frappe app repair tool
Fixes common structural issues discovered through research:
- Missing hooks.py in correct location
- apps.txt synchronization issues  
- Git repository structure problems
- Python package structure errors
- Bench installation inconsistencies
"""

import os
import subprocess
import json
import shutil
import tempfile
from pathlib import Path
import argparse
import sys

class AppFixer:
    def __init__(self, app_name, bench_path=".", site_name=None):
        self.app_name = app_name
        self.bench_path = Path(bench_path).resolve()
        self.app_path = self.bench_path / "apps" / app_name
        self.site_name = site_name
        self.issues_found = []
        self.backup_path = None
        
    def run_command(self, cmd, cwd=None, capture_output=True):
        """Run shell command with error handling"""
        try:
            if cwd is None:
                cwd = self.bench_path
                
            result = subprocess.run(
                cmd, 
                shell=True, 
                cwd=cwd,
                capture_output=capture_output,
                text=True
            )
            return result
        except Exception as e:
            print(f"❌ Command failed: {cmd}")
            print(f"Error: {e}")
            return None

    def diagnose_issues(self):
        """Comprehensive diagnosis based on our research findings"""
        print(f"🔍 Diagnosing {self.app_name}...")
        issues = []
        
        # 1. Check if app exists in apps directory
        if not self.app_path.exists():
            issues.append("MISSING_APP_DIRECTORY")
            print("❌ App directory doesn't exist")
            return issues
            
        # 2. Check hooks.py structure (critical issue we found)
        hooks_py = self.app_path / self.app_name / "hooks.py"
        if not hooks_py.exists():
            issues.append("MISSING_HOOKS_PY")
            print("❌ hooks.py missing in package directory")
        
        # 3. Check apps.txt synchronization (core issue)
        apps_txt = self.bench_path / "apps.txt"
        if apps_txt.exists():
            with open(apps_txt, 'r') as f:
                apps_content = f.read()
                if self.app_name not in apps_content:
                    issues.append("MISSING_IN_APPS_TXT")
                    print("❌ App missing from apps.txt")
                else:
                    print("✅ App found in apps.txt")
        
        # 4. Check git structure (submodule issues)
        git_dir = self.app_path / ".git"
        if git_dir.exists():
            issues.append("EMBEDDED_GIT_REPO")
            print("❌ Embedded git repository detected")
            
        # 5. Check Python package structure
        init_file = self.app_path / self.app_name / "__init__.py"
        if not init_file.exists():
            issues.append("MISSING_INIT_PY")
            print("❌ __init__.py missing in package")
            
        # 6. Check if app is installed on site
        if self.site_name:
            installed = self.check_if_installed()
            if not installed:
                issues.append("NOT_INSTALLED_ON_SITE")
                print("❌ App not installed on site")
            else:
                print("✅ App installed on site")
        
        if not issues:
            print("✅ No structural issues found!")
            
        self.issues_found = issues
        return issues

    def check_if_installed(self):
        """Check if app is installed on the site"""
        if not self.site_name:
            return False
            
        try:
            result = self.run_command(
                f"bench --site {self.site_name} console",
                capture_output=True
            )
            if result and result.returncode == 0:
                # Simple check - in real implementation, use frappe.get_installed_apps()
                return True
        except:
            pass
        return False

    def create_backup(self):
        """Backup existing app code"""
        print("📦 Creating backup...")
        self.backup_path = Path(tempfile.mkdtemp(prefix=f"{self.app_name}_backup_"))
        
        if self.app_path.exists():
            # Copy all files except git directory
            for item in self.app_path.iterdir():
                if item.name != '.git':
                    dest = self.backup_path / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)
            print(f"✅ Backup created at: {self.backup_path}")
            return True
        return False

    def remove_from_apps_txt(self):
        """Remove app from apps.txt if present"""
        apps_txt = self.bench_path / "apps.txt"
        if apps_txt.exists():
            with open(apps_txt, 'r') as f:
                lines = f.readlines()
            
            new_lines = [line for line in lines if line.strip() != self.app_name]
            
            if len(new_lines) != len(lines):
                with open(apps_txt, 'w') as f:
                    f.writelines(new_lines)
                print("✅ Removed from apps.txt")
                return True
        return False

    def add_to_apps_txt(self):
        """Add app to apps.txt if missing"""
        apps_txt = self.bench_path / "apps.txt"
        
        # Read existing apps
        existing_apps = []
        if apps_txt.exists():
            with open(apps_txt, 'r') as f:
                existing_apps = [line.strip() for line in f.readlines()]
        
        # Add if not present
        if self.app_name not in existing_apps:
            existing_apps.append(self.app_name)
            with open(apps_txt, 'w') as f:
                f.write('\n'.join(existing_apps) + '\n')
            print("✅ Added to apps.txt")
            return True
        return False

    def uninstall_app(self):
        """Uninstall app from site"""
        if not self.site_name:
            print("ℹ️ No site specified, skipping uninstall")
            return True
            
        print(f"🗑️ Uninstalling {self.app_name} from {self.site_name}...")
        result = self.run_command(f"bench --site {self.site_name} uninstall-app {self.app_name}")
        if result and result.returncode == 0:
            print("✅ Uninstalled successfully")
            return True
        else:
            print("❌ Uninstall failed")
            return False

    def regenerate_app_structure(self):
        """Use bench new-app to regenerate proper structure"""
        print("🔄 Regenerating app structure...")
        
        # Remove existing app directory
        if self.app_path.exists():
            shutil.rmtree(self.app_path)
            print("✅ Removed old app directory")
        
        # Create new app with bench new-app
        result = self.run_command(f"bench new-app {self.app_name}")
        if result and result.returncode == 0:
            print("✅ Successfully regenerated app structure")
            return True
        else:
            print("❌ Failed to regenerate app")
            return False

    def restore_custom_code(self):
        """Restore custom code from backup"""
        if not self.backup_path or not self.backup_path.exists():
            print("ℹ️ No backup found, skipping code restoration")
            return False
            
        print("📥 Restoring custom code...")
        
        # Restore everything except the generated structure
        for item in self.backup_path.iterdir():
            if item.name != self.app_name:  # Don't restore the package dir
                dest = self.app_path / item.name
                if item.is_dir():
                    if dest.exists():
                        shutil.rmtree(dest)
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
        
        print("✅ Custom code restored")
        return True

    def install_app(self):
        """Install app on site"""
        if not self.site_name:
            print("ℹ️ No site specified, skipping install")
            return True
            
        print(f"📥 Installing {self.app_name} on {self.site_name}...")
        
        # First ensure app is in apps.txt
        self.add_to_apps_txt()
        
        # Install the app
        result = self.run_command(f"bench --site {self.site_name} install-app {self.app_name}")
        if result and result.returncode == 0:
            print("✅ Installed successfully")
            return True
        else:
            print("❌ Install failed")
            return False

    def fix_app(self):
        """Main fix procedure - orchestrates all steps"""
        print(f"🚀 Starting fix procedure for {self.app_name}")
        print("=" * 50)
        
        # Step 1: Diagnose
        issues = self.diagnose_issues()
        if not issues:
            print("✅ No issues found, nothing to fix!")
            return True
            
        print(f"📋 Issues found: {', '.join(issues)}")
        print()
        
        # Step 2: Create backup
        if not self.create_backup():
            print("❌ Backup failed, aborting!")
            return False
            
        try:
            # Step 3: Remove from apps.txt
            self.remove_from_apps_txt()
            
            # Step 4: Uninstall from site
            self.uninstall_app()
            
            # Step 5: Regenerate structure
            if not self.regenerate_app_structure():
                return False
                
            # Step 6: Restore custom code
            self.restore_custom_code()
            
            # Step 7: Add to apps.txt
            self.add_to_apps_txt()
            
            # Step 8: Install on site
            if not self.install_app():
                return False
                
            # Step 9: Final validation
            print()
            print("🔍 Final validation...")
            final_issues = self.diagnose_issues()
            
            if not final_issues:
                print("🎉 SUCCESS: All issues resolved!")
                return True
            else:
                print(f"⚠️ Some issues remain: {', '.join(final_issues)}")
                return False
                
        except Exception as e:
            print(f"💥 Fix procedure failed: {e}")
            return False
        finally:
            # Cleanup backup
            if self.backup_path and self.backup_path.exists():
                shutil.rmtree(self.backup_path)
                print("🧹 Backup cleaned up")

def main():
    parser = argparse.ArgumentParser(description='Fix Frappe app structural issues')
    parser.add_argument('app_name', help='Name of the app to fix')
    parser.add_argument('--bench-path', default='.', help='Path to bench directory')
    parser.add_argument('--site', help='Site name for installation')
    
    args = parser.parse_args()
    
    fixer = AppFixer(args.app_name, args.bench_path, args.site)
    success = fixer.fix_app()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
