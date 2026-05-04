"""resolve-duplicates command (T1.8.3 — extracted from __init__.py)"""

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
    ProgressTracker,
    MigrationSession,
    get_current_site,
    detect_available_benches,
    get_bench_apps,
)


@click.command('app-migrator-resolve-duplicates')
@click.option('--keep', required=True, help='App to KEEP doctypes in (authoritative)')
@click.option('--remove-from', required=True, help='App to REMOVE duplicate doctypes from')
@click.option('--add-dependency/--no-dependency', default=True, help='Add dependency in hooks.py')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
def app_migrator_resolve_duplicates(keep, remove_from, add_dependency, dry_run):
    """
    Resolve duplicate doctypes between two apps.
    
    Compares doctypes, keeps authoritative version in --keep app,
    removes duplicates from --remove-from app, and optionally adds dependency.
    
    Example:
        bench app-migrator resolve-duplicates --keep amb_w_tds --remove-from rnd_nutrition --apply
    """
    import shutil
    
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"🔧 RESOLVE DUPLICATES [{mode}]")
    print(f"   Keep in: {keep}")
    print(f"   Remove from: {remove_from}")
    print("=" * 60)
    
    # Find apps path
    apps_path = os.path.join(find_bench_root(), "apps")
    keep_app_path = os.path.join(apps_path, keep)
    remove_app_path = os.path.join(apps_path, remove_from)
    
    if not os.path.exists(keep_app_path):
        print(f"❌ App not found: {keep_app_path}")
        return
    if not os.path.exists(remove_app_path):
        print(f"❌ App not found: {remove_app_path}")
        return
    
    # Find all doctypes in both apps
    def get_doctypes(app_path, app_name):
        doctypes = {}
        for root, dirs, files in os.walk(app_path):
            if '/doctype/' in root or '\\doctype\\' in root:
                for f in files:
                    if f.endswith('.json') and not f.startswith('_'):
                        json_path = os.path.join(root, f)
                        try:
                            with open(json_path) as jf:
                                data = json.load(jf)
                                if data.get('doctype') == 'DocType':
                                    dt_name = data.get('name')
                                    if dt_name:
                                        doctypes[dt_name] = {
                                            'path': os.path.dirname(json_path),
                                            'app': data.get('app'),
                                            'custom': data.get('custom', 0),
                                            'fields': len(data.get('fields', []))
                                        }
                        except:
                            pass
        return doctypes
    
    keep_doctypes = get_doctypes(keep_app_path, keep)
    remove_doctypes = get_doctypes(remove_app_path, remove_from)
    
    # Find duplicates
    duplicates = set(keep_doctypes.keys()) & set(remove_doctypes.keys())
    
    if not duplicates:
        print(f"✅ No duplicate doctypes found between {keep} and {remove_from}")
        return
    
    print(f"\n📋 DUPLICATE DOCTYPES ({len(duplicates)}):")
    print(f"{'DocType':<35} {'Keep App':<20} {'Remove App':<20}")
    print("-" * 75)
    
    for dt in sorted(duplicates):
        keep_info = keep_doctypes[dt]
        remove_info = remove_doctypes[dt]
        keep_status = f"app={keep_info['app']}, {keep_info['fields']}f"
        remove_status = f"app={remove_info['app']}, {remove_info['fields']}f"
        print(f"{dt:<35} {keep_status:<20} {remove_status:<20}")
    
    # Unique doctypes in remove_from (will be preserved)
    unique_in_remove = set(remove_doctypes.keys()) - duplicates
    if unique_in_remove:
        print(f"\n✅ UNIQUE DOCTYPES IN {remove_from} (will be preserved): {len(unique_in_remove)}")
        for dt in sorted(unique_in_remove):
            print(f"   • {dt}")
    
    if not dry_run:
        print(f"\n🔧 REMOVING DUPLICATES FROM {remove_from}...")
        removed = 0
        for dt in duplicates:
            dt_path = remove_doctypes[dt]['path']
            try:
                shutil.rmtree(dt_path)
                print(f"   ✅ Removed: {dt}")
                removed += 1
            except Exception as e:
                print(f"   ❌ Failed to remove {dt}: {e}")
        
        # Add dependency in hooks.py
        if add_dependency:
            hooks_path = os.path.join(remove_app_path, remove_from, "hooks.py")
            if os.path.exists(hooks_path):
                with open(hooks_path, 'r') as f:
                    hooks_content = f.read()
                
                # Check if required_apps already exists
                if 'required_apps' in hooks_content:
                    # Check if keep app is already in required_apps
                    if keep not in hooks_content:
                        # Add to existing required_apps
                        import re
                        hooks_content = re.sub(
                            r'(required_apps\s*=\s*\[)',
                            f'\\1"{keep}", ',
                            hooks_content
                        )
                        with open(hooks_path, 'w') as f:
                            f.write(hooks_content)
                        print(f"   ✅ Added {keep} to required_apps in hooks.py")
                else:
                    # Add required_apps after app_name
                    hooks_content = hooks_content.replace(
                        f'app_name = "{remove_from}"',
                        f'app_name = "{remove_from}"\nrequired_apps = ["{keep}"]'
                    )
                    with open(hooks_path, 'w') as f:
                        f.write(hooks_content)
                    print(f"   ✅ Added required_apps = [\"{keep}\"] to hooks.py")
        
        print(f"\n✅ Removed {removed}/{len(duplicates)} duplicate doctypes")
        print(f"\n📋 NEXT STEPS:")
        print(f"   1. cd {remove_app_path}")
        print(f"   2. git add -A && git commit -m 'Remove duplicate doctypes, add {keep} dependency'")
        print(f"   3. git push")
    else:
        print(f"\n📋 Run with --apply to remove duplicates and add dependency")


