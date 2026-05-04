"""fix-app-field command (T1.8.3 — extracted from __init__.py)"""

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


@click.command('app-migrator-fix-app-field')
@click.option('--site', required=True, help='Site name')
@click.option('--module', required=True, help='Module name (e.g., "Amb W Tds")')
@click.option('--app', required=True, help='App name (e.g., "amb_w_tds")')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_fix_app_field(context, site, module, app, dry_run):
    """
    Fix DocTypes with NULL app field to prevent orphan deletion.

    CRITICAL: When a DocType's 'app' field is NULL, bench migrate marks it
    as an orphan and DELETES it, even if the JSON file exists!

    This command finds all DocTypes in a module where app=NULL and sets
    the correct app name.

    Example:
        bench app-migrator-fix-app-field --site mysite --module "Amb W Tds" --app amb_w_tds --apply
    """
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"🔧 FIX APP FIELD [{mode}]")
    print(f"   Site: {site}")
    print(f"   Module: {module}")
    print(f"   Target App: {app}")
    print("=" * 60)

    frappe.init(site=site)
    frappe.connect()

    # Find DocTypes with NULL app field in this module
    doctypes_with_null_app = frappe.db.sql("""
        SELECT name, module, custom, app
        FROM `tabDocType`
        WHERE module = %s AND (app IS NULL OR app = '')
    """, (module,), as_dict=True)

    if not doctypes_with_null_app:
        print(f"\n✅ No DocTypes found with NULL app field in module '{module}'")
        frappe.db.close()
        return

    print(f"\n⚠️ DOCTYPES WITH NULL APP FIELD ({len(doctypes_with_null_app)}):")
    for dt in doctypes_with_null_app:
        print(f"   • {dt['name']} (custom={dt['custom']}, app={dt['app']})")

    if not dry_run:
        print("\n🔧 FIXING APP FIELD...")
        fixed_count = 0
        for dt in doctypes_with_null_app:
            try:
                frappe.db.set_value("DocType", dt['name'], "app", app, update_modified=False)
                print(f"   ✅ {dt['name']} → app: {app}")
                fixed_count += 1
            except Exception as e:
                print(f"   ❌ {dt['name']}: {e}")

        frappe.db.commit()
        print(f"\n✅ Fixed {fixed_count}/{len(doctypes_with_null_app)} DocTypes")
        print(f"\n📋 Now run: bench --site {site} migrate")
    else:
        print("\n📋 Run with --apply to fix the app field")

    frappe.db.close()


