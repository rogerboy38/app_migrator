"""ensure-controllers command (T1.8.3 — extracted from __init__.py)"""

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
    def pass_context(f):
        return f
from ._shared import (
    MigrationSession,
    ProgressTracker,
    detect_available_benches,
    get_bench_apps,
    get_current_site,
)


def ensure_controller_files(app_name, module_name=None, dry_run=True):
    """
    Create missing .py controller files for DocTypes in an app.
    
    When DocTypes are marked as custom=0 (standard), Frappe requires
    a .py controller file. This function creates basic controller files
    for any DocTypes that are missing them.
    
    Args:
        app_name: The app name (e.g., 'amb_w_tds')
        module_name: Optional module name (defaults to app_name)
        dry_run: If True, only report what would be created
    
    Returns:
        List of created/would-create file paths
    """

    apps_dir = os.path.join(find_bench_root(), "apps")
    app_path = os.path.join(apps_dir, app_name, app_name)

    if not os.path.isdir(app_path):
        print(f"❌ No app folder found: {app_path}")
        return []

    # Find ALL doctype directories in the app (search all module folders)
    doctype_paths = []
    for entry in os.listdir(app_path):
        entry_path = os.path.join(app_path, entry)
        doctype_dir = os.path.join(entry_path, "doctype")
        if os.path.isdir(entry_path) and os.path.exists(doctype_dir):
            doctype_paths.append(doctype_dir)

    if not doctype_paths:
        print(f"❌ No doctype folder found for app: {app_name}")
        return []

    print(f"📁 Found {len(doctype_paths)} doctype folder(s) in {app_name}")

    created_files = []

    for doctype_path in doctype_paths:
        for item in os.listdir(doctype_path):
            item_path = os.path.join(doctype_path, item)

            # Skip non-directories and __pycache__
            if not os.path.isdir(item_path) or item.startswith('__'):
                continue

            doctype_name = item
            py_file = os.path.join(item_path, f"{doctype_name}.py")
            json_file = os.path.join(item_path, f"{doctype_name}.json")

            # Only create .py if .json exists but .py doesn't
            if os.path.exists(json_file) and not os.path.exists(py_file):
                # Convert doctype_name to PascalCase class name
                # e.g., 'third_party_api' -> 'ThirdPartyApi'
                class_name = ''.join(word.capitalize() for word in doctype_name.split('_'))

                controller_content = f'''import frappe
from frappe.model.document import Document

class {class_name}(Document):
    pass
'''

                if dry_run:
                    print(f"   Would create: {py_file}")
                else:
                    with open(py_file, 'w') as f:
                        f.write(controller_content)
                    print(f"   ✅ Created: {py_file}")

                created_files.append(py_file)

    return created_files


@click.command('app-migrator-ensure-controllers')
@click.argument('app_name')
@click.option('--module', default=None, help='Module name (defaults to app name)')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_ensure_controllers(context, app_name, module, dry_run):
    """
    Create missing .py controller files for DocTypes in an app.
    
    This is needed when converting custom DocTypes (custom=1) to standard
    DocTypes (custom=0). Standard DocTypes require a .py controller file.
    
    Example:
        bench app-migrator-ensure-controllers amb_w_tds --apply
    """
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"🔧 ENSURE CONTROLLER FILES [{mode}]")
    print(f"   App: {app_name}")
    print(f"   Module: {module or app_name}")
    print("=" * 60)

    created = ensure_controller_files(app_name, module, dry_run)

    if created:
        print(f"\n📊 {'Would create' if dry_run else 'Created'} {len(created)} controller file(s)")
        if dry_run:
            print("\n📋 Run with --apply to create the files")
    else:
        print("\n✅ All DocTypes already have controller files")


