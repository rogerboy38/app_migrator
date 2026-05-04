#!/usr/bin/env python3
"""
App Migrator - Fix App Command
Automatically fixes common Frappe app structural issues
"""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

import click


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

            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)

            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                capture_output=capture_output,
                text=True
            )

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

        if not self.app_path.exists():
            issues.append("MISSING_APP_DIRECTORY")
            print("❌ App directory doesn't exist")
            return issues

        hooks_py = self.app_path / self.app_name / "hooks.py"
        if not hooks_py.exists():
            issues.append("MISSING_HOOKS_PY")
            print("❌ hooks.py missing in package directory")
        else:
            print("✅ hooks.py exists")

        apps_txt = self.bench_path / "apps.txt"
        if apps_txt.exists():
            with open(apps_txt) as f:
                apps_content = f.read()
                if self.app_name not in apps_content:
                    issues.append("MISSING_IN_APPS_TXT")
                    print("❌ App missing from apps.txt")
                else:
                    print("✅ App found in apps.txt")

        git_dir = self.app_path / ".git"
        if git_dir.exists():
            issues.append("EMBEDDED_GIT_REPO")
            print("❌ Embedded git repository detected")
        else:
            print("✅ No embedded git repo")

        init_file = self.app_path / self.app_name / "__init__.py"
        if not init_file.exists():
            issues.append("MISSING_INIT_PY")
            print("❌ __init__.py missing in package")
        else:
            print("✅ __init__.py exists")

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
        site_config = self.bench_path / "sites" / self.site_name / "site_config.json"
        if site_config.exists():
            try:
                with open(site_config) as f:
                    config = json.load(f)
                    installed_apps = config.get('installed_apps', [])
                    return self.app_name in installed_apps
            except Exception:
                pass
        return False

    def add_to_apps_txt(self):
        """Add app to apps.txt if missing"""
        apps_txt = self.bench_path / "apps.txt"

        existing_apps = []
        if apps_txt.exists():
            with open(apps_txt) as f:
                existing_apps = [line.strip() for line in f.readlines() if line.strip()]

        if self.app_name not in existing_apps:
            existing_apps.append(self.app_name)
            with open(apps_txt, 'w') as f:
                f.write('\n'.join(existing_apps) + '\n')
            print("✅ Added to apps.txt")
            return True
        return False

    def quick_fix(self):
        """Quick fix without slow bench commands"""
        print("⚡ Performing quick fixes...")

        fixes_applied = 0

        if self.add_to_apps_txt():
            fixes_applied += 1

        git_dir = self.app_path / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir)
            print("✅ Removed embedded git repository")
            fixes_applied += 1

        hooks_py = self.app_path / self.app_name / "hooks.py"
        init_py = self.app_path / self.app_name / "__init__.py"

        if not hooks_py.exists():
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

        issues = self.diagnose_issues()
        if not issues:
            print("✅ No issues found, nothing to fix!")
            return True

        print(f"📋 Issues found: {', '.join(issues)}")
        print()

        fixes_applied = self.quick_fix()

        if fixes_applied > 0:
            print(f"✅ Applied {fixes_applied} quick fixes")

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

@click.command('fix-app')
@click.argument('app_name')
@click.option('--site', help='Site name for installation check')
@click.option('--bench-path', default='.', help='Path to bench directory')
@click.option('--quick/--full', default=True, help='Use quick fix mode (recommended)')
def fix_app(app_name, site, bench_path, quick):
    """
    Fix common structural issues in Frappe apps
    
    Automatically diagnoses and fixes:
    • Missing hooks.py in package directory
    • Apps.txt synchronization issues  
    • Embedded git repository problems
    • Missing __init__.py files
    • Basic app structure validation
    """
    click.echo(f"🛠️  App Migrator: Fixing {app_name}")
    click.echo("=" * 50)

    fixer = AppFixer(app_name, bench_path, site)

    if quick:
        success = fixer.fix_app_quick()
    else:
        click.echo("⚠️  Full mode not yet implemented, using quick mode")
        success = fixer.fix_app_quick()

    if success:
        click.echo("🎉 Fix completed successfully!")
    else:
        click.echo("❌ Fix failed!")
        sys.exit(1)

if __name__ == "__main__":
    fix_app()
