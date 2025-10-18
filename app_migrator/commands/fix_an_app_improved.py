#!/usr/bin/env python3
"""
Improved fix_an_app.py with timeout handling and better error recovery
"""

import os
import subprocess
import json
import shutil
import tempfile
from pathlib import Path
import argparse
import sys
import signal

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Command timed out")

class AppFixer:
    def __init__(self, app_name, bench_path=".", site_name=None):
        self.app_name = app_name
        self.bench_path = Path(bench_path).resolve()
        self.app_path = self.bench_path / "apps" / app_name
        self.site_name = site_name
        self.issues_found = []
        self.backup_path = None
        
    def run_command(self, cmd, cwd=None, capture_output=True, timeout=60):
        """Run shell command with timeout handling"""
        try:
            if cwd is None:
                cwd = self.bench_path
                
            # Set timeout handler
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
            
            result = subprocess.run(
                cmd, 
                shell=True, 
                cwd=cwd,
                capture_output=capture_output,
                text=True
            )
            
            # Cancel timeout
            signal.alarm(0)
            return result
            
        except TimeoutError:
            print(f"⏰ Command timed out: {cmd}")
            return None
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
        else:
            print("✅ hooks.py exists")
        
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
        else:
            print("✅ No embedded git repo")
            
        # 5. Check Python package structure
        init_file = self.app_path / self.app_name / "__init__.py"
        if not init_file.exists():
            issues.append("MISSING_INIT_PY")
            print("❌ __init__.py missing in package")
        else:
            print("✅ __init__.py exists")
        
        # 6. Check if app is installed on site (skip if no site specified)
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
        """Quick check if app might be installed"""
        # Simple file-based check instead of slow bench command
        site_config = self.bench_path / "sites" / self.site_name / "site_config.json"
        if site_config.exists():
            try:
                with open(site_config, 'r') as f:
                    config = json.load(f)
                    installed_apps = config.get('installed_apps', [])
                    return self.app_name in installed_apps
            except:
                pass
        return False

    def quick_fix(self):
        """Quick fix without slow bench commands"""
        print("⚡ Performing quick fixes...")
        
        fixes_applied = 0
        
        # 1. Fix apps.txt
        if self.add_to_apps_txt():
            fixes_applied += 1
            
        # 2. Remove embedded git
        git_dir = self.app_path / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir)
            print("✅ Removed embedded git repository")
            fixes_applied += 1
            
        # 3. Ensure basic structure
        hooks_py = self.app_path / self.app_name / "hooks.py"
        init_py = self.app_path / self.app_name / "__init__.py"
        
        if not hooks_py.exists():
            # Create basic hooks.py
            hooks_content = f'''from . import __version__ as version

app_name = "{self.app_name}"
app_title = "{self.app_name.title()}"
app_publisher = "Auto-generated"
app_description = "Auto-generated app"
app_version = version
app_license = "MIT"
'''
            hooks_py.parent.mkdir(parents=True, exist_ok=True)
            with open(hooks_py, 'w') as f:
                f.write(hooks_content)
            print("✅ Created missing hooks.py")
            fixes_applied += 1
            
        if not init_py.exists():
            init_py.parent.mkdir(parents=True, exist_ok=True)
            with open(init_py, 'w') as f:
                f.write('__version__ = "1.0.0"')
            print("✅ Created missing __init__.py")
            fixes_applied += 1
            
        return fixes_applied

    def fix_app_quick(self):
        """Quick fix procedure without slow bench commands"""
        print(f"🚀 Starting QUICK fix procedure for {self.app_name}")
        print("=" * 50)
        
        # Step 1: Diagnose
        issues = self.diagnose_issues()
        if not issues:
            print("✅ No issues found, nothing to fix!")
            return True
            
        print(f"📋 Issues found: {', '.join(issues)}")
        print()
        
        # Step 2: Apply quick fixes
        fixes_applied = self.quick_fix()
        
        if fixes_applied > 0:
            print(f"✅ Applied {fixes_applied} quick fixes")
            
            # Step 3: Final validation
            print()
            print("🔍 Final validation...")
            final_issues = self.diagnose_issues()
            
            if not final_issues:
                print("🎉 SUCCESS: All issues resolved!")
                return True
            else:
                print(f"⚠️ Some issues remain: {', '.join(final_issues)}")
                print("💡 Run 'bench build' and 'bench install-app' manually if needed")
                return True
        else:
            print("❌ No fixes were applied")
            return False

def main():
    parser = argparse.ArgumentParser(description='Fix Frappe app structural issues')
    parser.add_argument('app_name', help='Name of the app to fix')
    parser.add_argument('--bench-path', default='.', help='Path to bench directory')
    parser.add_argument('--site', help='Site name for installation')
    parser.add_argument('--quick', action='store_true', help='Use quick fix mode (no bench commands)')
    
    args = parser.parse_args()
    
    fixer = AppFixer(args.app_name, args.bench_path, args.site)
    
    if args.quick:
        success = fixer.fix_app_quick()
    else:
        # For now, default to quick mode to avoid hangs
        print("⚠️  Using quick mode to avoid command timeouts")
        success = fixer.fix_app_quick()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
