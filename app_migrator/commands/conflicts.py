"""app-migrator-conflicts command (T1.8.2 — extracted from __init__.py)"""

import json
import os
import time
from collections import defaultdict
from datetime import datetime

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f

from ._envelope import emit_envelope, make_envelope


@click.command('app-migrator-conflicts')
@click.option('--json', 'as_json', is_flag=True, help='Emit v0.5 envelope JSON (wraps the real conflict result)')
@click.option('--site', required=True, help='Site name')
@click.option('--apps', help='Comma-separated apps to analyze')
@click.option('--all-apps', 'all_apps', is_flag=True, default=False, help='Scan ALL apps in apps folder (not just installed)')
@click.option('--output', '-o', help='Output JSON file')
@pass_context
def app_migrator_conflicts(context, as_json, site, apps, all_apps, output):
    """Detect conflicts between apps (use --all-apps to include uninstalled apps)"""
    start = time.time()
    if not as_json:
        print(f"🔍 Detecting conflicts in: {site}")
        print("=" * 60)

    try:
        frappe.init(site=site)
        frappe.connect()
    except Exception as e:
        if as_json:
            emit_envelope(make_envelope(
                command="conflicts",
                status="error",
                summary=f"conflicts failed: {type(e).__name__}",
                findings=[{"id": "conflicts-error", "title": "Conflict scan failed",
                           "severity": "high", "description": str(e)}],
                site=site, start_time=start,
            ))
        raise

    doctype_to_apps = defaultdict(list)

    # Determine apps path
    # frappe.get_app_path('frappe') returns e.g. /home/frappe/frappe-bench/apps/frappe/frappe
    # We need /home/frappe/frappe-bench/apps
    apps_path = os.path.dirname(os.path.dirname(frappe.get_app_path('frappe')))

    if all_apps:
        # Scan ALL apps in apps folder by reading doctype JSON files
        if not as_json:
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

        if not as_json:
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

    total = len(result["conflicts"]["duplicate_doctypes"]) + len(result["conflicts"]["orphan_doctypes"])

    if as_json:
        dups = result["conflicts"]["duplicate_doctypes"]
        orphs = result["conflicts"]["orphan_doctypes"]
        if output:
            with open(output, 'w') as f:
                json.dump(result, f, indent=2)
        findings = []
        if dups:
            names = ", ".join(d["doctype"] for d in dups[:10])
            findings.append({"id": "conflicts-duplicate-doctypes",
                             "title": "Duplicate DocTypes across apps", "severity": "high",
                             "description": f"{len(dups)} duplicate(s): {names}" + (" ..." if len(dups) > 10 else "")})
        if orphs:
            names = ", ".join(o["doctype"] for o in orphs[:10])
            findings.append({"id": "conflicts-orphan-doctypes",
                             "title": "Orphan DocTypes (no module)", "severity": "warn",
                             "description": f"{len(orphs)} orphan(s): {names}" + (" ..." if len(orphs) > 10 else "")})
        emit_envelope(make_envelope(
            command="conflicts",
            status="ok" if total == 0 else "warn",
            summary=(f"conflict scan: {len(result['apps_analyzed'])} apps, {total} issue(s) "
                     f"({len(dups)} duplicate, {len(orphs)} orphan)"),
            findings=findings,
            evidence=[{"type": "conflict_counts", "data": {
                "apps_analyzed": len(result["apps_analyzed"]),
                "duplicate_doctypes": len(dups),
                "orphan_doctypes": len(orphs),
                "scan_mode": result["scan_mode"]}}],
            site=site, start_time=start,
        ))

    # Display
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
