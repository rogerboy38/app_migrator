"""stage command (T1.8.3 — extracted from __init__.py)"""

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


@click.command('app-migrator-stage')
@click.option('--site', default=None, help='Site name (uses current site if not specified)')
@click.option('--source', required=True, help='Source app name')
@click.option('--host', required=True, help='Host/staging app name')
@click.option('--doctypes', default=None, help='Comma-separated doctype names (or all)')
@click.option('--prefix', default='STAGE_', help='Prefix for staged doctypes')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_stage(context, site, source, host, doctypes, prefix, dry_run):
    """Stage doctypes from source app to host app with prefix"""
    if not site:
        site = get_current_site()
        if not site:
            print("❌ No site specified and no current site set. Use --site or 'bench use <site>'")
            return
    mode = "DRY-RUN" if dry_run else "APPLY"
    source_module_title = source.replace("_", " ").title()
    print(f"📤 STAGING DOCTYPES [{mode}]")
    print(f"   Source: {source} (module: {source_module_title})")
    print(f"   Host: {host}")
    print(f"   Prefix: {prefix}")
    print("=" * 60)

    frappe.init(site=site)
    frappe.connect()

    # Get doctypes from source app - try DB first, then filesystem
    source_doctypes = []
    if doctypes:
        dt_list = [d.strip() for d in doctypes.split(',')]
        source_doctypes = frappe.get_all("DocType",
            filters={"name": ["in", dt_list]},
            fields=["name", "module"])
    else:
        # Try database first
        source_doctypes = frappe.get_all("DocType",
            filters={"module": source_module_title},
            fields=["name", "module"])

        # If no DB results, scan filesystem for all modules in the app
        if not source_doctypes:
            print(f"   ℹ️ No doctypes in DB for module '{source_module_title}', scanning filesystem...")
            app_path = os.path.expanduser(f"~/frappe-bench/apps/{source}/{source}")
            modules_file = os.path.join(app_path, "modules.txt")
            if os.path.exists(modules_file):
                with open(modules_file) as f:
                    modules = [m.strip() for m in f.readlines() if m.strip()]
                print(f"   📂 Found modules: {modules}")
                for module in modules:
                    module_folder = module.lower().replace(" ", "_")
                    doctype_path = os.path.join(app_path, module_folder, "doctype")
                    if os.path.exists(doctype_path):
                        for dt_folder in os.listdir(doctype_path):
                            dt_full_path = os.path.join(doctype_path, dt_folder)
                            if os.path.isdir(dt_full_path) and not dt_folder.startswith("_"):
                                # Convert folder name to DocType name (snake_case to Title Case)
                                dt_name = dt_folder.replace("_", " ").title()
                                source_doctypes.append({"name": dt_name, "module": module})

    host_module_title = host.replace("_", " ").title()
    print(f"\n📦 DOCTYPES TO REASSIGN TO MODULE '{host_module_title}' ({len(source_doctypes)}):")
    staged = []

    for dt in source_doctypes:
        dt_name = dt.get('name') if isinstance(dt, dict) else dt.name
        dt_module = dt.get('module') if isinstance(dt, dict) else dt.module
        print(f"   • {dt_name} (current: {dt_module})")
        staged.append({"old_name": dt_name, "old_module": dt_module})

    if not dry_run:
        print("\n🔧 STAGING (reassigning module via Frappe API)...")

        # Step 1: Ensure host module exists in Module Def
        host_module_title = host.replace("_", " ").title()
        if not frappe.db.exists("Module Def", host_module_title):
            try:
                module_doc = frappe.new_doc("Module Def")
                module_doc.module_name = host_module_title
                module_doc.app_name = host
                module_doc.insert(ignore_permissions=True)
                print(f"   ✅ Created Module Def: {host_module_title}")
            except Exception as e:
                print(f"   ⚠️ Module Def creation: {e}")

        # Step 2: Update modules.txt in host app
        host_apps_path = os.path.expanduser(f"~/frappe-bench/apps/{host}/{host}/modules.txt")
        if os.path.exists(host_apps_path):
            with open(host_apps_path) as f:
                modules = [m.strip() for m in f.readlines() if m.strip()]
            if host_module_title not in modules:
                modules.append(host_module_title)
                with open(host_apps_path, 'w') as f:
                    f.write('\n'.join(modules) + '\n')
                print(f"   ✅ Updated modules.txt with: {host_module_title}")
        else:
            # Create modules.txt if host app exists but file doesn't
            host_app_dir = os.path.expanduser(f"~/frappe-bench/apps/{host}/{host}")
            if os.path.exists(host_app_dir):
                with open(host_apps_path, 'w') as f:
                    f.write(f"{host_module_title}\n")
                print(f"   ✅ Created modules.txt with: {host_module_title}")
            else:
                print(f"   ⚠️ Host app not found at: {host_app_dir}")

        # Step 3: Copy doctype files from source to host app
        import json
        import shutil
        source_app_path = os.path.expanduser(f"~/frappe-bench/apps/{source}/{source}")
        host_app_path = os.path.expanduser(f"~/frappe-bench/apps/{host}/{host}")
        host_module_folder = host_module_title.lower().replace(" ", "_")
        host_doctype_path = os.path.join(host_app_path, host_module_folder, "doctype")
        os.makedirs(host_doctype_path, exist_ok=True)

        # Build a map of all doctype folders in source app (search all module dirs)
        doctype_folder_map = {}
        for entry in os.listdir(source_app_path):
            entry_path = os.path.join(source_app_path, entry)
            doctype_dir = os.path.join(entry_path, "doctype")
            if os.path.isdir(entry_path) and os.path.exists(doctype_dir):
                for dt_folder in os.listdir(doctype_dir):
                    dt_path = os.path.join(doctype_dir, dt_folder)
                    if os.path.isdir(dt_path) and not dt_folder.startswith("_"):
                        doctype_folder_map[dt_folder] = dt_path

        print("\n📁 COPYING DOCTYPE FILES TO HOST APP...")

        # Step 4: Reassign doctypes to host module AND mark as custom (prevents orphan deletion)
        success_count = 0
        for item in staged:
            dt_name = item["old_name"]
            dt_folder_name = dt_name.lower().replace(" ", "_")
            # Use the map to find actual path (handles module name mismatches)
            source_dt_path = doctype_folder_map.get(dt_folder_name)
            target_dt_path = os.path.join(host_doctype_path, dt_folder_name)

            try:
                # Copy doctype folder to host app
                if os.path.exists(source_dt_path):
                    if os.path.exists(target_dt_path):
                        shutil.rmtree(target_dt_path)
                    shutil.copytree(source_dt_path, target_dt_path)

                    # Update module in JSON file
                    json_file = os.path.join(target_dt_path, f"{dt_folder_name}.json")
                    if os.path.exists(json_file):
                        with open(json_file) as f:
                            dt_json = json.load(f)
                        dt_json["module"] = host_module_title
                        dt_json["custom"] = 1
                        with open(json_file, 'w') as f:
                            json.dump(dt_json, f, indent=1)
                    print(f"   📄 Copied: {dt_name} → {host}/{host_module_folder}/doctype/{dt_folder_name}/")

                # Update DB record
                if frappe.db.exists("DocType", dt_name):
                    frappe.db.set_value("DocType", dt_name, {
                        "module": host_module_title,
                        "custom": 1
                    }, update_modified=False)
                print(f"   ✅ {dt_name} → module: {host_module_title} (custom=1)")
                success_count += 1
            except Exception as e:
                print(f"   ❌ {dt_name}: {e}")

        frappe.db.commit()
        print(f"\n✅ Reassigned {success_count}/{len(staged)} doctypes to module '{host_module_title}'")
        print("\n📋 To move back to original or new app, run:")
        print(f"   bench app-migrator-unstage --site {site} --host {host} --target <target_app>")
    else:
        print("\n📋 Run with --apply to reassign doctypes to host module")

    frappe.db.close()

