"""app-migrator-scan command (T1.8.2 — extracted from __init__.py)"""

import json
from datetime import datetime

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f
@click.command('app-migrator-scan')
@click.option('--site', required=True, help='Site name')
@click.option('--output', '-o', help='Output JSON file')
@pass_context
def app_migrator_scan(context, site, output):
    """Scan site for apps, doctypes, custom fields"""
    print(f"🔍 Scanning site: {site}")
    print("=" * 60)

    frappe.init(site=site)
    frappe.connect()

    result = {
        "site": site,
        "timestamp": datetime.now().isoformat(),
        "frappe_version": getattr(frappe, '__version__', 'unknown'),
        "apps": frappe.get_installed_apps(),
        "doctypes": [],
        "custom_fields": [],
        "summary": {}
    }

    # Get doctypes
    doctypes = frappe.get_all("DocType", fields=["name", "module", "custom", "istable"])
    result["doctypes"] = [dict(dt) for dt in doctypes]

    # Get custom fields
    custom_fields = frappe.get_all("Custom Field", fields=["name", "dt", "fieldname", "fieldtype"])
    result["custom_fields"] = [dict(cf) for cf in custom_fields]

    # Summary
    result["summary"] = {
        "apps": len(result["apps"]),
        "doctypes": len(result["doctypes"]),
        "custom_doctypes": len([d for d in doctypes if d.custom]),
        "child_tables": len([d for d in doctypes if d.istable]),
        "custom_fields": len(result["custom_fields"])
    }

    frappe.db.close()

    # Display
    print("\n📊 SCAN RESULTS:")
    print(f"   Frappe: {result['frappe_version']}")
    print(f"   Apps: {result['summary']['apps']}")
    for app in result["apps"]:
        print(f"      • {app}")
    print(f"   DocTypes: {result['summary']['doctypes']}")
    print(f"   Custom DocTypes: {result['summary']['custom_doctypes']}")
    print(f"   Child Tables: {result['summary']['child_tables']}")
    print(f"   Custom Fields: {result['summary']['custom_fields']}")

    if output:
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✅ Saved to: {output}")
