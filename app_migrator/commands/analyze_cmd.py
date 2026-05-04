"""analyze command (T1.8.4 — extracted from __init__.py).

File named analyze_cmd.py to avoid collision with the analyze/
subdirectory (which holds analyze/apps.py and similar).
"""

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


@click.command('app-migrator-analyze')
@click.argument('app_name')
@pass_context
def app_migrator_analyze(context, app_name):
    """Analyze app structure (modern pyproject.toml vs traditional)"""
    print(f"🔍 ANALYZING APP: {app_name}")
    print("=" * 60)

    app_path = os.path.expanduser(f"~/frappe-bench/apps/{app_name}")

    if not os.path.exists(app_path):
        print(f"❌ App not found: {app_path}")
        return

    result = {
        "app_name": app_name,
        "path": app_path,
        "structure": "unknown",
        "has_pyproject": False,
        "has_hooks": False,
        "has_modules_txt": False,
        "nested_package": False,
        "modules": [],
        "dependencies": [],
        "issues": []
    }

    # Check for modern structure (pyproject.toml)
    pyproject_path = os.path.join(app_path, "pyproject.toml")
    result["has_pyproject"] = os.path.exists(pyproject_path)

    # Check for nested package structure
    nested_path = os.path.join(app_path, app_name)
    if os.path.isdir(nested_path):
        result["nested_package"] = True
        hooks_path = os.path.join(nested_path, "hooks.py")
        modules_txt_path = os.path.join(nested_path, "modules.txt")
    else:
        hooks_path = os.path.join(app_path, "hooks.py")
        modules_txt_path = os.path.join(app_path, "modules.txt")

    result["has_hooks"] = os.path.exists(hooks_path)
    result["has_modules_txt"] = os.path.exists(modules_txt_path)

    # Determine structure type
    if result["has_pyproject"] and result["nested_package"]:
        result["structure"] = "modern"
    elif result["has_hooks"]:
        result["structure"] = "traditional"
    else:
        result["structure"] = "incomplete"
        result["issues"].append("Missing hooks.py")

    # Read modules.txt if exists
    if result["has_modules_txt"]:
        with open(modules_txt_path) as f:
            result["modules"] = [line.strip() for line in f if line.strip()]

    # Detect Python modules in nested package
    if result["nested_package"]:
        for item in os.listdir(nested_path):
            item_path = os.path.join(nested_path, item)
            if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "__init__.py")):
                if item not in ['templates', 'public', 'patches', 'config', '__pycache__']:
                    if item not in result["modules"]:
                        result["modules"].append(item)

    # Read dependencies from pyproject.toml
    if result["has_pyproject"]:
        try:
            with open(pyproject_path) as f:
                content = f.read()
                # Simple extraction of dependencies
                if 'dependencies' in content:
                    import re
                    deps = re.findall(r'"([a-zA-Z0-9_-]+)"', content)
                    result["dependencies"] = [d for d in deps if d not in ['python', 'frappe', app_name]][:10]
        except Exception:
            pass

    # Check for issues
    if not result["has_hooks"]:
        result["issues"].append("Missing hooks.py")
    if not result["has_modules_txt"] and result["modules"]:
        result["issues"].append("Missing modules.txt (has modules)")

    # Display results
    print("\n📋 STRUCTURE ANALYSIS:")
    print(f"   Type: {result['structure'].upper()}")
    print(f"   Nested Package: {'Yes' if result['nested_package'] else 'No'}")
    print(f"   pyproject.toml: {'✅' if result['has_pyproject'] else '❌'}")
    print(f"   hooks.py: {'✅' if result['has_hooks'] else '❌'}")
    print(f"   modules.txt: {'✅' if result['has_modules_txt'] else '❌'}")

    if result["modules"]:
        print(f"\n📦 MODULES ({len(result['modules'])}):")
        for mod in result["modules"][:15]:
            print(f"   • {mod}")
        if len(result["modules"]) > 15:
            print(f"   ... and {len(result['modules']) - 15} more")

    if result["dependencies"]:
        print(f"\n📚 DEPENDENCIES ({len(result['dependencies'])}):")
        for dep in result["dependencies"]:
            print(f"   • {dep}")

    if result["issues"]:
        print("\n⚠️ ISSUES:")
        for issue in result["issues"]:
            print(f"   • {issue}")

    # Health score
    score = 0
    if result["has_hooks"]:
        score += 30
    if result["has_modules_txt"]:
        score += 20
    if result["has_pyproject"]:
        score += 20
    if result["modules"]:
        score += 20
    if not result["issues"]:
        score += 10

    print(f"\n💯 HEALTH SCORE: {score}%")

