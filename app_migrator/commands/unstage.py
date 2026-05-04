"""unstage command (T1.8.3 — extracted from __init__.py)"""

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


@click.command('app-migrator-unstage')
@click.option('--site', default=None, help='Site name (uses current site if not specified)')
@click.option('--host', required=True, help='Host/staging module name')
@click.option('--target', required=True, help='Target module name')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_unstage(context, site, host, target, dry_run):
    """Unstage doctypes from host module to target module (reassign module)"""
    if not site:
        site = get_current_site()
        if not site:
            print("❌ No site specified and no current site set. Use --site or 'bench use <site>'")
            return
    mode = "DRY-RUN" if dry_run else "APPLY"
    host_module_title = host.replace("_", " ").title()
    target_module_title = target.replace("_", " ").title()

    print(f"📥 UNSTAGING DOCTYPES [{mode}]")
    print(f"   From module: {host_module_title}")
    print(f"   To module: {target_module_title}")
    print("=" * 60)

    frappe.init(site=site)
    frappe.connect()

    # Get doctypes in the host module
    host_doctypes = frappe.get_all("DocType",
        filters={"module": host_module_title},
        fields=["name", "module"])

    print(f"\n📦 DOCTYPES TO REASSIGN ({len(host_doctypes)}):")

    for dt in host_doctypes:
        print(f"   • {dt.name}")

    if not dry_run:
        print(f"\n🔧 REASSIGNING TO MODULE '{target_module_title}'...")
        success_count = 0
        for dt in host_doctypes:
            try:
                # Restore module, set custom=0, and set app field (CRITICAL for orphan prevention)
                frappe.db.set_value("DocType", dt.name, {
                    "module": target_module_title,
                    "custom": 0,  # Restore to normal doctype
                    "app": target  # CRITICAL: prevents orphan deletion
                }, update_modified=False)
                print(f"   ✅ {dt.name} → module: {target_module_title} (custom=0)")
                success_count += 1
            except Exception as e:
                print(f"   ❌ {dt.name}: {e}")

        frappe.db.commit()
        print(f"\n✅ Reassigned {success_count}/{len(host_doctypes)} doctypes to '{target_module_title}'")

        # Auto-create missing controller files for the target app
        print("\n🔧 Ensuring controller files exist for target app...")
        created = ensure_controller_files(target, target, dry_run=False)
        if created:
            print(f"   Created {len(created)} controller file(s)")
        else:
            print("   All controller files already exist")

        print(f"\n📋 Now run: bench --site {site} migrate")
    else:
        print("\n📋 Run with --apply to reassign")

    frappe.db.close()

