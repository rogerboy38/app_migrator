"""fix-json-app command (T1.8.3 — extracted from __init__.py)"""

import json
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    pass_context = lambda f: f

from ._shared import (
    MigrationSession,
    ProgressTracker,
    detect_available_benches,
    get_bench_apps,
    get_current_site,
)


@click.command('app-migrator-fix-json-app')
@click.argument('app_name')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
def app_migrator_fix_json_app(app_name, dry_run):
    """
    Fix JSON app field issues to prevent orphan deletion on fresh installs.
    
    This command fixes TWO common issues:
    1. 'app': null - Replaces with correct app name
    2. Duplicate 'app' fields - Removes the first occurrence (keeps the one near 'module')
    
    Both issues cause DocTypes to be deleted as orphans during bench migrate.
    
    Example:
        bench app-migrator-fix-json-app amb_w_tds --apply
    """

    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"🔧 FIX JSON APP FIELD [{mode}]")
    print(f"   App: {app_name}")
    print("=" * 60)

    # Find app directory
    bench_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    apps_path = os.path.join(bench_path, "apps")
    app_path = os.path.join(apps_path, app_name)

    if not os.path.exists(app_path):
        print(f"❌ App not found: {app_path}")
        return

    # Find all DocType JSON files
    null_app_files = []
    duplicate_app_files = []
    already_correct = []
    errors = []

    for root, dirs, files in os.walk(app_path):
        if "/doctype/" in root:
            for f in files:
                if f.endswith(".json") and not f.startswith("_"):
                    json_path = os.path.join(root, f)
                    try:
                        with open(json_path) as fp:
                            content = fp.read()

                        # Check if this is a DocType JSON
                        if '"doctype": "DocType"' not in content:
                            continue

                        needs_fix = False

                        # Issue 1: Check for "app": null
                        if '"app": null' in content or '"app":null' in content:
                            null_app_files.append(json_path)
                            needs_fix = True
                            if not dry_run:
                                content = re.sub(
                                    r'"app":\s*null',
                                    f'"app": "{app_name}"',
                                    content
                                )

                        # Issue 2: Check for duplicate "app" fields
                        app_count = len(re.findall(r'"app":', content))
                        if app_count > 1:
                            duplicate_app_files.append(json_path)
                            needs_fix = True
                            if not dry_run:
                                # Remove the first occurrence (in first 30 lines)
                                lines = content.split('\n')
                                new_lines = []
                                removed = False
                                for i, line in enumerate(lines):
                                    if not removed and i < 30 and '"app":' in line:
                                        removed = True
                                        continue
                                    new_lines.append(line)
                                content = '\n'.join(new_lines)

                        if needs_fix and not dry_run:
                            with open(json_path, 'w') as fp:
                                fp.write(content)
                        elif not needs_fix:
                            already_correct.append(json_path)

                    except Exception as e:
                        errors.append((json_path, str(e)))

    print("\n📊 SCAN RESULTS:")
    print(f"   Files with 'app': null: {len(null_app_files)}")
    print(f"   Files with duplicate 'app': {len(duplicate_app_files)}")
    print(f"   Already correct: {len(already_correct)}")
    if errors:
        print(f"   Errors: {len(errors)}")

    total_issues = len(set(null_app_files + duplicate_app_files))

    if null_app_files:
        print(f"\n📝 {'Would fix' if dry_run else 'Fixed'} 'app': null → 'app': '{app_name}':")
        for f in null_app_files[:5]:
            print(f"   • {os.path.basename(os.path.dirname(f))}")
        if len(null_app_files) > 5:
            print(f"   ... and {len(null_app_files) - 5} more")

    if duplicate_app_files:
        print(f"\n📝 {'Would remove' if dry_run else 'Removed'} duplicate 'app' field:")
        for f in duplicate_app_files[:5]:
            print(f"   • {os.path.basename(os.path.dirname(f))}")
        if len(duplicate_app_files) > 5:
            print(f"   ... and {len(duplicate_app_files) - 5} more")

    if dry_run and total_issues > 0:
        print(f"\n📋 Run with --apply to fix {total_issues} file(s)")
        print(f"   Then commit: cd {app_path} && git add -A && git commit -m 'Fix app field in JSON' && git push")
    elif not dry_run and total_issues > 0:
        print(f"\n✅ Fixed {total_issues} file(s)")
        print("\n📋 Now commit the changes:")
        print(f"   cd {app_path}")
        print("   git add -A && git commit -m 'Fix app field in JSON' && git push")
    elif total_issues == 0:
        print("\n✅ All JSON files are correct - no issues found")


