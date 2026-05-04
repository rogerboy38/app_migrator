"""app-migrator-plan command (T1.8.2 — extracted from __init__.py)"""

import json
from datetime import datetime

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    pass_context = lambda f: f


@click.command('app-migrator-plan')
@click.option('--site', required=True, help='Site name')
@click.option('--source-apps', required=True, help='Source apps (comma-separated)')
@click.option('--target-app', required=True, help='Target consolidated app')
@click.option('--output', '-o', required=True, help='Output plan file')
@pass_context
def app_migrator_plan(context, site, source_apps, target_app, output):
    """Generate a migration plan"""
    print(f"📋 Generating migration plan")
    print(f"   Source: {source_apps}")
    print(f"   Target: {target_app}")
    print("=" * 60)

    frappe.init(site=site)
    frappe.connect()

    apps_list = [a.strip() for a in source_apps.split(',')]

    plan = {
        "version": "10.0.0-rc1",
        "created": datetime.now().isoformat(),
        "source_apps": apps_list,
        "target_app": target_app,
        "doctypes": [],
        "custom_fields": [],
        "data_migration": []
    }

    for app in apps_list:
        doctypes = frappe.get_all("DocType",
            filters={"module": app},
            fields=["name", "module", "istable"])

        for dt in doctypes:
            try:
                count = frappe.db.count(dt.name)
            except Exception:
                count = 0

            plan["doctypes"].append({
                "name": dt.name,
                "source_app": app,
                "target_app": target_app,
                "is_child": dt.istable,
                "record_count": count
            })

            if count > 0:
                plan["data_migration"].append({
                    "doctype": dt.name,
                    "records": count,
                    "action": "migrate"
                })

    frappe.db.close()

    with open(output, 'w') as f:
        json.dump(plan, f, indent=2)

    print(f"\n✅ Plan saved: {output}")
    print(f"   DocTypes: {len(plan['doctypes'])}")
    print(f"   Data migrations: {len(plan['data_migration'])}")
    print(f"\n📋 Next: bench app-migrator-execute --site {site} --plan {output} --dry-run")
