"""orphans command (T1.8.3 — extracted from __init__.py)"""

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
    def pass_context(f):
        return f
from ._shared import (
    MigrationSession,
    ProgressTracker,
    detect_available_benches,
    get_bench_apps,
    get_current_site,
)


@click.command('app-migrator-orphans')
@click.option('--site', default=None, help='Site name (uses current site if not specified)')
@click.option('--fix', 'fix_mode', is_flag=True, help='Auto-fix by matching to filesystem apps')
@click.option('--delete', 'delete_mode', is_flag=True, help='Delete orphaned DocTypes (DANGEROUS)')
@click.option('--reassign', default=None, help='Reassign all orphans to specified app/module')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_orphans(context, site, fix_mode, delete_mode, reassign, dry_run):
    """
    Intelligent orphaned DocType detection and resolution.
    
    Detects DocTypes where:
    1. The 'module' doesn't match any installed app
    2. The 'app' field is NULL or doesn't match filesystem
    3. No JSON definition exists in any app
    
    Resolution options:
      --fix       Auto-match to correct app by scanning filesystem
      --delete    Remove orphaned DocTypes (use with caution!)
      --reassign  Move all orphans to a specific app/module
    
    Examples:
        bench app-migrator orphans --site mysite
        bench app-migrator orphans --site mysite --fix --apply
        bench app-migrator orphans --site mysite --reassign my_app --apply
    """
    if not site:
        site = get_current_site()
        if not site:
            print("❌ No site specified and no current site set. Use --site or 'bench use <site>'")
            return

    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"🔍 ORPHAN DETECTION [{mode}]")
    print(f"   Site: {site}")
    print("=" * 60)

    frappe.init(site=site)
    frappe.connect()

    # Get installed apps and their modules
    installed_apps = frappe.get_installed_apps()

    # Build module-to-app mapping from Module Def
    module_to_app = {}
    module_defs = frappe.get_all("Module Def", fields=["name", "app_name"])
    for md in module_defs:
        if md.app_name:
            module_to_app[md.name] = md.app_name

    # Scan filesystem for DocType definitions
    apps_path = os.path.dirname(os.path.dirname(frappe.get_app_path('frappe')))
    filesystem_doctypes = {}  # dt_name -> app_name

    for app_name in os.listdir(apps_path):
        app_dir = os.path.join(apps_path, app_name)
        if not os.path.isdir(app_dir) or app_name.startswith('.'):
            continue

        for root, dirs, files in os.walk(app_dir):
            if '/doctype/' in root or '\\doctype\\' in root:
                for f in files:
                    if f.endswith('.json') and not f.startswith('_'):
                        json_path = os.path.join(root, f)
                        try:
                            with open(json_path) as jf:
                                data = json.load(jf)
                                if data.get('doctype') == 'DocType':
                                    dt_name = data.get('name')
                                    dt_module = data.get('module')
                                    if dt_name:
                                        # Check if .py controller exists
                                        dt_folder = os.path.dirname(json_path)
                                        dt_folder_name = os.path.basename(dt_folder)
                                        py_file = os.path.join(dt_folder, f"{dt_folder_name}.py")
                                        has_controller = os.path.exists(py_file)

                                        filesystem_doctypes[dt_name] = {
                                            'app': app_name,
                                            'module': dt_module,
                                            'path': json_path,
                                            'py_path': py_file,
                                            'has_controller': has_controller
                                        }
                        except Exception:
                            pass

    # Get all DocTypes from database
    all_doctypes = frappe.get_all("DocType",
        fields=["name", "module", "app", "custom"],
        filters={"custom": 0}  # Focus on standard DocTypes
    )

    # Categorize orphans
    orphans = {
        'no_app_field': [],       # app field is NULL
        'no_json': [],            # No JSON file in any app
        'wrong_app': [],          # app field doesn't match filesystem
        'no_controller': [],      # JSON exists but no .py controller file
    }

    for dt in all_doctypes:
        dt_name = dt.name
        dt_module = dt.module
        dt_app = dt.app

        fs_info = filesystem_doctypes.get(dt_name)

        # Check 1: No app field
        if not dt_app:
            if fs_info:
                orphans['no_app_field'].append({
                    'name': dt_name,
                    'module': dt_module,
                    'suggested_app': fs_info['app'],
                    'suggested_module': fs_info['module']
                })
            else:
                orphans['no_json'].append({
                    'name': dt_name,
                    'module': dt_module,
                    'app': dt_app
                })
            continue

        # Check 2: No JSON in filesystem
        if not fs_info:
            # Only flag if not in installed apps (could be core Frappe/ERPNext)
            if dt_app not in installed_apps:
                orphans['no_json'].append({
                    'name': dt_name,
                    'module': dt_module,
                    'app': dt_app
                })
            continue

        # Check 3: App mismatch
        if dt_app != fs_info['app']:
            orphans['wrong_app'].append({
                'name': dt_name,
                'current_app': dt_app,
                'correct_app': fs_info['app'],
                'module': dt_module
            })

        # Check 4: Missing controller file (THE KEY CHECK!)
        if not fs_info.get('has_controller'):
            orphans['no_controller'].append({
                'name': dt_name,
                'app': fs_info['app'],
                'module': fs_info['module'],
                'py_path': fs_info['py_path']
            })

    # Summary
    total_orphans = sum(len(v) for v in orphans.values())

    print("\n📊 ORPHAN ANALYSIS:")
    print(f"   Total DocTypes scanned: {len(all_doctypes)}")
    print(f"   Filesystem DocTypes found: {len(filesystem_doctypes)}")
    print(f"   Total orphans: {total_orphans}")
    print()
    print(f"   📌 No 'app' field (fixable): {len(orphans['no_app_field'])}")
    print(f"   📌 Wrong 'app' field: {len(orphans['wrong_app'])}")
    print(f"   🔴 Missing .py controller (WILL ORPHAN!): {len(orphans['no_controller'])}")
    print(f"   ⚠️  No JSON definition: {len(orphans['no_json'])}")

    # Show details
    if orphans['no_app_field']:
        print("\n🔧 DOCTYPES WITH NULL APP FIELD:")
        for o in orphans['no_app_field'][:10]:
            print(f"   • {o['name']:<40} → suggested: {o['suggested_app']}")
        if len(orphans['no_app_field']) > 10:
            print(f"   ... and {len(orphans['no_app_field']) - 10} more")

    if orphans['wrong_app']:
        print("\n⚠️ DOCTYPES WITH WRONG APP FIELD:")
        for o in orphans['wrong_app'][:10]:
            print(f"   • {o['name']:<40} current: {o['current_app']}, should be: {o['correct_app']}")
        if len(orphans['wrong_app']) > 10:
            print(f"   ... and {len(orphans['wrong_app']) - 10} more")

    if orphans['no_controller']:
        print("\n🔴 DOCTYPES WITH MISSING .PY CONTROLLER (will be deleted by migrate!):")
        for o in orphans['no_controller'][:15]:
            print(f"   • {o['name']:<40} app: {o['app']}, missing: {os.path.basename(o['py_path'])}")
        if len(orphans['no_controller']) > 15:
            print(f"   ... and {len(orphans['no_controller']) - 15} more")

    if orphans['no_json']:
        print("\n❓ DOCTYPES WITH NO JSON (may be deletable):")
        for o in orphans['no_json'][:10]:
            print(f"   • {o['name']:<40} module: {o['module']}, app: {o['app']}")
        if len(orphans['no_json']) > 10:
            print(f"   ... and {len(orphans['no_json']) - 10} more")

    # Apply fixes
    if not dry_run:
        fixed_count = 0
        deleted_count = 0

        if fix_mode:
            print("\n🔧 APPLYING AUTO-FIX...")

            # Fix NULL app field
            for o in orphans['no_app_field']:
                try:
                    frappe.db.set_value("DocType", o['name'], {
                        'app': o['suggested_app'],
                        'module': o['suggested_module']
                    }, update_modified=False)
                    print(f"   ✅ {o['name']} → app: {o['suggested_app']}")
                    fixed_count += 1
                except Exception as e:
                    print(f"   ❌ {o['name']}: {e}")

            # Fix wrong app field
            for o in orphans['wrong_app']:
                try:
                    frappe.db.set_value("DocType", o['name'], 'app', o['correct_app'], update_modified=False)
                    print(f"   ✅ {o['name']} → app: {o['correct_app']}")
                    fixed_count += 1
                except Exception as e:
                    print(f"   ❌ {o['name']}: {e}")

            frappe.db.commit()

            # Create missing controller files (THE KEY FIX!)
            controllers_created = 0
            if orphans['no_controller']:
                print("\n🔧 CREATING MISSING CONTROLLER FILES...")
                for o in orphans['no_controller']:
                    py_path = o['py_path']
                    dt_name = o['name']

                    # Convert doctype name to class name (Title Case -> PascalCase)
                    # e.g., "TDS Settings" -> "TdsSettings"
                    class_name = ''.join(word.capitalize() for word in dt_name.replace('-', ' ').split())

                    controller_content = f'''import frappe
from frappe.model.document import Document


class {class_name}(Document):
    pass
'''
                    try:
                        with open(py_path, 'w') as f:
                            f.write(controller_content)
                        print(f"   ✅ Created: {py_path}")
                        controllers_created += 1
                    except Exception as e:
                        print(f"   ❌ {dt_name}: {e}")

                print(f"\n✅ Created {controllers_created} controller files")

            print(f"\n✅ Fixed {fixed_count} DocTypes, created {controllers_created} controllers")

        elif reassign:
            print(f"\n🔧 REASSIGNING TO: {reassign}...")
            reassign_module = reassign.replace("_", " ").title()

            all_fixable = orphans['no_app_field'] + orphans['wrong_app']
            for o in all_fixable:
                try:
                    frappe.db.set_value("DocType", o['name'], {
                        'app': reassign,
                        'module': reassign_module
                    }, update_modified=False)
                    print(f"   ✅ {o['name']} → {reassign}")
                    fixed_count += 1
                except Exception as e:
                    print(f"   ❌ {o['name']}: {e}")

            frappe.db.commit()
            print(f"\n✅ Reassigned {fixed_count} DocTypes to {reassign}")

        elif delete_mode:
            if not click.confirm(f"⚠️ DELETE {len(orphans['no_json'])} orphaned DocTypes? This is IRREVERSIBLE!"):
                print("❌ Cancelled")
            else:
                print("\n🗑️ DELETING ORPHANS...")
                for o in orphans['no_json']:
                    try:
                        frappe.delete_doc("DocType", o['name'], force=True)
                        print(f"   🗑️ Deleted: {o['name']}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"   ❌ {o['name']}: {e}")

                frappe.db.commit()
                print(f"\n✅ Deleted {deleted_count} orphaned DocTypes")

        print(f"\n📋 Now run: bench --site {site} migrate")

    else:
        if total_orphans > 0:
            print("\n📋 RESOLUTION OPTIONS:")
            print(f"   bench app-migrator orphans --site {site} --fix --apply")
            print(f"   bench app-migrator orphans --site {site} --reassign <app_name> --apply")
            print(f"   bench app-migrator orphans --site {site} --delete --apply")
        else:
            print("\n✅ No orphaned DocTypes found!")

    frappe.db.close()


