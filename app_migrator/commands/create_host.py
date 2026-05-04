"""create-host command (T1.8.3 — extracted from __init__.py)"""

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

from ._shared import find_bench_root

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


@click.command('app-migrator-create-host')
@click.argument('host_app_name')
@pass_context
def app_migrator_create_host(context, host_app_name):
    """Create a staging/host app for ping-pong migration"""
    print(f"🏗️ CREATE HOST APP: {host_app_name}")
    print("=" * 60)

    apps_dir = os.path.join(find_bench_root(), "apps")
    host_path = os.path.join(apps_dir, host_app_name)

    if os.path.exists(host_path):
        print(f"✅ App already exists: {host_path}")
        print("\n📋 NEXT STEPS:")
        print(f"   1. Install: bench --site <site> install-app {host_app_name}")
        print(f"   2. Stage: bench app-migrator-stage --site <site> --source <app> --host {host_app_name}")
        return

    # Use frappe API directly to create app non-interactively
    print(f"\n🔄 Creating app: {host_app_name}...")

    try:
        import frappe
        from frappe.utils.boilerplate import _create_app_boilerplate

        hooks = frappe._dict(
            app_name=host_app_name,
            app_title=host_app_name.replace("_", " ").title(),
            app_description="Staging app for ping-pong migration",
            app_publisher="App Migrator",
            app_email="migrator@localhost",
            app_license="mit",
            create_github_workflow=False,
            branch_name="develop"
        )

        _create_app_boilerplate(apps_dir, hooks, no_git=True)

        print(f"✅ App created: {host_path}")
        print("\n📋 NEXT STEPS:")
        print(f"   1. Install: bench --site <site> install-app {host_app_name}")
        print(f"   2. Stage: bench app-migrator-stage --site <site> --source <app> --host {host_app_name}")

    except ImportError:
        # Fallback if direct import fails
        print("\n⚠️ Direct creation failed. Run manually:")
        print(f"   cd ~/frappe-bench && bench new-app {host_app_name}")
        print("\n   Answer prompts:")
        print(f"     App Title: {host_app_name.replace('_', ' ').title()}")
        print("     App Description: Staging app for migration")
        print("     App Publisher: Your Name")
        print("     App Email: your@email.com")
        print("     App License: mit")

