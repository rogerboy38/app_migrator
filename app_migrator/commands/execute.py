"""app-migrator-execute command (T1.8.2 — extracted from __init__.py)"""

import json

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    pass_context = lambda f: f

from ._shared import ProgressTracker


@click.command('app-migrator-execute')
@click.option('--site', required=True, help='Site name')
@click.option('--plan', 'plan_file', required=True, help='Migration plan file')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_execute(context, site, plan_file, dry_run):
    """Execute a migration plan"""
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"🚀 Executing migration [{mode}]")
    print("=" * 60)

    with open(plan_file) as f:
        plan = json.load(f)

    if not dry_run:
        if not click.confirm("⚠️ This will modify your database. Continue?"):
            print("❌ Cancelled")
            return

    frappe.init(site=site)
    frappe.connect()

    tracker = ProgressTracker("Migration", len(plan["doctypes"]))

    for dt in plan["doctypes"]:
        tracker.update(f"Processing {dt['name']}")
        if not dry_run:
            frappe.db.sql("""
                UPDATE `tabDocType` SET module = %s WHERE name = %s
            """, (dt["target_app"], dt["name"]))

    if not dry_run:
        frappe.db.commit()

    frappe.db.close()
    tracker.complete()

    if dry_run:
        print("\n✅ Dry-run complete. Run with --apply to execute.")
    else:
        print(f"\n✅ Migration complete! Run 'bench --site {site} migrate'")
