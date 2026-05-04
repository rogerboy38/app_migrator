"""app-migrator-conflicts command (T1.8.2 — extracted from __init__.py)"""

import json
import os
from collections import defaultdict
from datetime import datetime

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f
@click.command('app-migrator-conflicts')
@click.option('--site', required=True, help='Site name')
@click.option('--apps', help='Comma-separated apps to analyze')
@click.option('--all-apps', 'all_apps', is_flag=True, default=False, help='Scan ALL apps in apps folder (not just installed)')
@click.option('--output', '-o', help='Output JSON file')
@pass_context
def app_migrator_conflicts(context, site, apps, all_apps, output):
    """Detect conflicts between apps (use --all-apps to include uninstalled apps)"""
    print(f"🔍 Detecting conflicts in: {site}")
    print("=" * 60)

    frappe.init(site=site)
    frappe.connect()

    doctype_to_apps = defaultdict(list)

    # Determine apps path
    # frappe.get_app_path('frappe') returns e.g. /home/frappe/frappe-bench/apps/frappe/frappe
    # We need /home/frappe/frappe-bench/apps
    apps_path = os.path.dirname(os.path.dirname(frappe.get_app_path('frappe')))

    if all_apps:
        # Scan ALL apps in apps folder by reading doctype JSON files
        click.secho("📂 Scanning ALL apps in apps folder (including uninstalled)...", fg="cyan")
        apps_list = []

        for app_name in os.listdir(apps_path):
            app_dir = os.path.join(apps_path, app_name)
            if not os.path.isdir(app_dir) or app_name.startswith('.'):
                continue

            # Check if it's a valid Frappe app
            has_hooks = os.path.exists(os.path.join(app_dir, app_name, "hooks.py")) or \
                       os.path.exists(os.path.join(app_dir, "hooks.py"))
            has_pyproject = os.path.exists(os.path.join(app_dir, "pyproject.toml"))

            if not (has_hooks or has_pyproject):
                continue

            apps_list.append(app_name)

            # Find all doctype JSON files in this app
            for root, _dirs, files in os.walk(app_dir):
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
                                            if app_name not in doctype_to_apps[dt_name]:
                                                doctype_to_apps[dt_name].append(app_name)
                            except Exception:
                                pass

        print(f"   Found {len(apps_list)} apps: {', '.join(sorted(apps_list))}")
    else:
        # Original behavior - only installed apps via database
        apps_list = apps.split(',') if apps else frappe.get_installed_apps()

        for app in apps_list:
            doctypes = frappe.get_all("DocType", filters={"module": app}, fields=["name"])
            for dt in doctypes:
                doctype_to_apps[dt.name].append(app)

    result = {
        "site": site,
        "apps_analyzed": sorted(apps_list),
        "scan_mode": "all_apps" if all_apps else "installed_only",
        "timestamp": datetime.now().isoformat(),
        "conflicts": {
            "duplicate_doctypes": [],
            "orphan_doctypes": [],
            "field_conflicts": []
        }
    }

    # Duplicate doctypes (found in multiple apps)
    for dt, dt_apps in doctype_to_apps.items():
        if len(dt_apps) > 1:
            result["conflicts"]["duplicate_doctypes"].append({
                "doctype": dt, "apps": sorted(dt_apps)
            })

    # Orphan doctypes (only for installed apps mode)
    if not all_apps:
        orphans = frappe.get_all("DocType",
            filters={"module": ["in", ["", None]], "custom": 0},
            fields=["name"])
        result["conflicts"]["orphan_doctypes"] = [{"doctype": o.name} for o in orphans]

    frappe.db.close()

    # Display
    total = len(result["conflicts"]["duplicate_doctypes"]) + len(result["conflicts"]["orphan_doctypes"])
    print("\n📊 CONFLICT SUMMARY:")
    print(f"   Scan Mode: {'All Apps (filesystem)' if all_apps else 'Installed Apps (database)'}")
    print(f"   Apps Scanned: {len(apps_list)}")
    print(f"   Duplicate DocTypes: {len(result['conflicts']['duplicate_doctypes'])}")
    if not all_apps:
        print(f"   Orphan DocTypes: {len(result['conflicts']['orphan_doctypes'])}")
    print(f"   Total Issues: {total}")

    if result["conflicts"]["duplicate_doctypes"]:
        print("\n⚠️ DUPLICATE DOCTYPES (same name in multiple apps):")
        for dup in result["conflicts"]["duplicate_doctypes"]:
            print(f"   • {dup['doctype']} → {dup['apps']}")

    if output:
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✅ Saved to: {output}")
