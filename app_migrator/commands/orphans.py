"""orphans command (T1.8.3 — extracted from __init__.py)

v0.5-alpha W1 (Coder 2026-06-24): added --json envelope support per Phase 4 contract.
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
from ._envelope import emit_envelope, make_envelope


# ──────────────────────────────────────────────────────────────────────────
# Filesystem scan filters (added 2026-05-08 after sysmayal misattribution)
# ──────────────────────────────────────────────────────────────────────────
# The scanner walks apps/<each-app>/ to enumerate DocType definitions on
# disk. Without filtering it picks up sibling backup directories, archive
# trees, test fixtures, and synthetic specimens — producing inflated FS
# counts and misattributing real DocTypes to non-production paths
# (observed: COA AMB2 → app_migrator.pre-v10.1.x-backup on sysmayal).
#
# Two layers:
#   1. APP-LEVEL  — sites/apps.txt is authoritative. Only listed apps are
#                   walked. Sibling dirs are skipped regardless of name.
#   2. PATH-LEVEL — inside each accepted app, prune directory components
#                   that are never source-of-truth (tests, fixtures,
#                   _archive, build, .venv, __pycache__, .git, …).

# Used only as a fallback when sites/apps.txt is unavailable.
NON_APP_NAME_PATTERNS = (
    "backup", "archive", ".bak", "_bak",
    "snapshot", ".old", "_old", ".pre-",
)

SKIP_WALK_COMPONENTS = frozenset({
    "__pycache__", ".git", ".github", ".hg", ".svn",
    "node_modules", ".venv", "venv", "env",
    "tests", "test", "fixtures", "fixture",
    "_archive", "archive",
    "docs", "doc", "build", "dist",
    ".pytest_cache", ".ruff_cache", ".mypy_cache", ".tox",
})

SKIP_WALK_NAME_PATTERNS = ("backup", "archive", "_bak", ".bak", "snapshot")


def _load_apps_txt(apps_path):
    """Set of apps from <bench>/sites/apps.txt, or None if unavailable.

    apps.txt is authoritative for "what counts as a real app on this bench."
    Returning None makes _should_skip_app_dir() fall back to looser pattern
    matching — the caller should warn in that case."""
    apps_txt = os.path.join(os.path.dirname(apps_path), "sites", "apps.txt")
    if not os.path.exists(apps_txt):
        return None
    with open(apps_txt) as f:
        return {ln.strip() for ln in f if ln.strip()}


def _should_skip_app_dir(app_name, apps_txt_set):
    """Decide whether a top-level dir under apps/ is a real app.

    Returns (skip: bool, reason: str). Layer 1 of the filter."""
    if app_name.startswith(".") or app_name.startswith("_"):
        return True, "hidden/private prefix"
    if apps_txt_set is not None:
        if app_name not in apps_txt_set:
            return True, "not listed in sites/apps.txt"
        # apps.txt is authoritative — if listed, accept even if the name
        # happens to contain a blocklist substring.
        return False, ""
    # No apps.txt available — fall back to pattern-based rejection.
    lower = app_name.lower()
    for pat in NON_APP_NAME_PATTERNS:
        if pat in lower:
            return True, f"name matches non-app pattern {pat!r} (apps.txt unavailable)"
    return False, ""


def _should_prune_walk(name):
    """Whether to drop this directory component from os.walk recursion.

    Layer 2 of the filter — applied to dirs[:] inside each accepted app."""
    if name.startswith(".") or name.startswith("_"):
        return True
    if name in SKIP_WALK_COMPONENTS:
        return True
    lower = name.lower()
    for pat in SKIP_WALK_NAME_PATTERNS:
        if pat in lower:
            return True
    return False


@click.command('app-migrator-orphans')
@click.option('--json', 'as_json', is_flag=True, help='Emit v0.5 envelope JSON')
@click.option('--site', default=None, help='Site name (uses current site if not specified)')
@click.option('--fix', 'fix_mode', is_flag=True, help='Auto-fix by matching to filesystem apps')
@click.option('--delete', 'delete_mode', is_flag=True, help='Delete orphaned DocTypes (DANGEROUS)')
@click.option('--reassign', default=None, help='Reassign all orphans to specified app/module')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_orphans(context, as_json, site, fix_mode, delete_mode, reassign, dry_run):
    """
    Intelligent orphaned DocType detection and resolution.

    v0.5-alpha W1 (Coder 2026-06-24): --json envelope stub when set.
    """
    start = time.time()

    # v0.5 W3 fix #2: --json wraps the REAL detection result (not a stub). It is
    # read-only (detection); the destructive --fix/--delete/--reassign paths run
    # only in the non-JSON text mode.
    if not site:
        site = get_current_site()
        if not site:
            if as_json:
                emit_envelope(make_envelope(
                    command="orphans",
                    status="error",
                    summary="orphans failed: no site (pass --site or set current site)",
                    findings=[{
                        "id": "orphans-no-site",
                        "title": "No site specified",
                        "severity": "high",
                        "description": "orphan detection requires a site; pass --site or run 'bench use <site>'.",
                    }],
                    start_time=start,
                ))
            print("❌ No site specified and no current site set. Use --site or 'bench use <site>'")
            return

    if not as_json:
        mode = "DRY-RUN" if dry_run else "APPLY"
        print(f"🔍 ORPHAN DETECTION [{mode}]")
        print(f"   Site: {site}")
        print("=" * 60)

    try:
        frappe.init(site=site)
        frappe.connect()
    except Exception as e:
        if as_json:
            emit_envelope(make_envelope(
                command="orphans",
                status="error",
                summary=f"orphans failed: {type(e).__name__}",
                findings=[{
                    "id": "orphans-error",
                    "title": "Orphan detection failed",
                    "severity": "high",
                    "description": str(e),
                }],
                site=site,
                start_time=start,
            ))
        raise

    # Get installed apps and their modules
    installed_apps = frappe.get_installed_apps()

    # Build module-to-app mapping from Module Def
    module_to_app = {}
    module_defs = frappe.get_all("Module Def", fields=["name", "app_name"])
    for md in module_defs:
        if md.app_name:
            module_to_app[md.name] = md.app_name

    # Scan filesystem for DocType definitions, skipping non-production paths.
    # See module-level NON_APP_NAME_PATTERNS / SKIP_WALK_COMPONENTS comments.
    apps_path = os.path.dirname(os.path.dirname(frappe.get_app_path('frappe')))
    apps_txt_set = _load_apps_txt(apps_path)
    filesystem_doctypes = {}        # dt_name -> {app, module, path, py_path, has_controller}
    skipped_app_dirs = []           # [(name, reason)]
    fs_collisions = []              # [(dt_name, kept_app, also_in_app)]

    # sorted() makes collision tie-breaking deterministic — first hit wins.
    for app_name in sorted(os.listdir(apps_path)):
        app_dir = os.path.join(apps_path, app_name)
        if not os.path.isdir(app_dir):
            continue
        skip, reason = _should_skip_app_dir(app_name, apps_txt_set)
        if skip:
            skipped_app_dirs.append((app_name, reason))
            continue

        for root, dirs, files in os.walk(app_dir):
            # In-place prune so os.walk does not descend into excluded subtrees.
            dirs[:] = [d for d in dirs if not _should_prune_walk(d)]
            if '/doctype/' not in root and '\\doctype\\' not in root:
                continue
            for f in files:
                if not f.endswith('.json') or f.startswith('_'):
                    continue
                json_path = os.path.join(root, f)
                try:
                    with open(json_path) as jf:
                        data = json.load(jf)
                except Exception:
                    continue
                if not isinstance(data, dict) or data.get('doctype') != 'DocType':
                    continue
                dt_name = data.get('name')
                if not dt_name:
                    continue
                dt_folder = os.path.dirname(json_path)
                dt_folder_name = os.path.basename(dt_folder)
                py_file = os.path.join(dt_folder, f"{dt_folder_name}.py")
                record = {
                    'app': app_name,
                    'module': data.get('module'),
                    'path': json_path,
                    'py_path': py_file,
                    'has_controller': os.path.exists(py_file),
                }
                existing = filesystem_doctypes.get(dt_name)
                if existing is not None:
                    if existing['app'] != app_name:
                        fs_collisions.append((dt_name, existing['app'], app_name))
                    continue  # keep first hit; never overwrite
                filesystem_doctypes[dt_name] = record

    if apps_txt_set is None and not as_json:
        print("   ⚠ sites/apps.txt missing — using pattern-based app filtering only")

    # Get all DocTypes from database
    all_doctypes = frappe.get_all("DocType",
        fields=["name", "module", "app", "custom"],
        filters={"custom": 0}  # Focus on standard DocTypes
    )

    # Categorize orphans
    orphans = {
        'no_app_field': [],       # app field is NULL
        'no_json': [],            # No JSON file in any app
        'wrong_app': [],          # app field doesn't match filesystem
        'no_controller': [],      # JSON exists but no .py controller file
    }

    for dt in all_doctypes:
        dt_name = dt.name
        dt_module = dt.module
        dt_app = dt.app

        fs_info = filesystem_doctypes.get(dt_name)

        # Check 1: No app field
        if not dt_app:
            if fs_info:
                orphans['no_app_field'].append({
                    'name': dt_name,
                    'module': dt_module,
                    'suggested_app': fs_info['app'],
                    'suggested_module': fs_info['module']
                })
            else:
                orphans['no_json'].append({
                    'name': dt_name,
                    'module': dt_module,
                    'app': dt_app
                })
            continue

        # Check 2: No JSON in filesystem
        if not fs_info:
            # Only flag if not in installed apps (could be core Frappe/ERPNext)
            if dt_app not in installed_apps:
                orphans['no_json'].append({
                    'name': dt_name,
                    'module': dt_module,
                    'app': dt_app
                })
            continue

        # Check 3: App mismatch
        if dt_app != fs_info['app']:
            orphans['wrong_app'].append({
                'name': dt_name,
                'current_app': dt_app,
                'correct_app': fs_info['app'],
                'module': dt_module
            })

        # Check 4: Missing controller file (THE KEY CHECK!)
        if not fs_info.get('has_controller'):
            orphans['no_controller'].append({
                'name': dt_name,
                'app': fs_info['app'],
                'module': fs_info['module'],
                'py_path': fs_info['py_path']
            })

    # Summary
    total_orphans = sum(len(v) for v in orphans.values())

    # v0.5 W3 fix #2: under --json, emit the real detection result as an envelope
    # (read-only) and stop before the text display / destructive apply paths.
    if as_json:
        frappe.db.close()
        findings = []
        for key, label, sev in [
            ("no_app_field", "DocTypes with NULL app field (fixable)", "warn"),
            ("wrong_app", "DocTypes with wrong app field", "warn"),
            ("no_controller", "DocTypes missing .py controller (will be deleted by migrate)", "high"),
            ("no_json", "DocTypes with no JSON definition", "info"),
        ]:
            items = orphans[key]
            if items:
                names = ", ".join(o['name'] for o in items[:10])
                findings.append({
                    "id": f"orphans-{key.replace('_', '-')}",
                    "title": label,
                    "severity": sev,
                    "description": f"{len(items)} DocType(s): {names}" + (" ..." if len(items) > 10 else ""),
                })
        suggested = []
        if total_orphans > 0:
            suggested = [
                {"command": f"bench app-migrator orphans --site {site} --fix --apply",
                 "approval_required": True,
                 "description": "Auto-fix NULL/wrong app fields + create missing controllers (destructive)."},
                {"command": f"bench app-migrator orphans --site {site} --reassign <app> --apply",
                 "approval_required": True,
                 "description": "Reassign orphans to an app (destructive)."},
                {"command": f"bench app-migrator orphans --site {site} --delete --apply",
                 "approval_required": True,
                 "description": "Delete no-JSON orphans (IRREVERSIBLE)."},
            ]
        emit_envelope(make_envelope(
            command="orphans",
            status="ok" if total_orphans == 0 else "warn",
            summary=(
                f"orphan detection: {total_orphans} orphan(s) across {len(all_doctypes)} "
                f"DocTypes ({len(filesystem_doctypes)} on filesystem)"
            ),
            findings=findings,
            evidence=[{"type": "orphan_counts", "data": {k: len(v) for k, v in orphans.items()}}],
            suggested_next_commands=suggested,
            site=site,
            start_time=start,
        ))

    print("\n📊 ORPHAN ANALYSIS:")
    print(f"   Total DocTypes scanned: {len(all_doctypes)}")
    print(f"   Filesystem DocTypes found: {len(filesystem_doctypes)}")
    print(f"   Total orphans: {total_orphans}")
    print()
    print(f"   📌 No 'app' field (fixable): {len(orphans['no_app_field'])}")
    print(f"   📌 Wrong 'app' field: {len(orphans['wrong_app'])}")
    print(f"   🔴 Missing .py controller (WILL ORPHAN!): {len(orphans['no_controller'])}")
    print(f"   ⚠️  No JSON definition: {len(orphans['no_json'])}")

    # Scan-filter visibility — surface what was excluded so unexpected counts
    # are explainable without re-reading the source.
    if skipped_app_dirs or fs_collisions:
        print("\n🔎 SCAN FILTERS:")
        if skipped_app_dirs:
            print(f"   Skipped app-level dirs: {len(skipped_app_dirs)}")
            for name, reason in skipped_app_dirs[:10]:
                print(f"     • apps/{name}/ — {reason}")
            if len(skipped_app_dirs) > 10:
                print(f"     ... and {len(skipped_app_dirs) - 10} more")
        if fs_collisions:
            print(f"   ⚠ FS collisions (same DocType in multiple apps): {len(fs_collisions)}")
            for dt, kept, also in fs_collisions[:10]:
                print(f"     • {dt}: kept apps/{kept}/, also in apps/{also}/")
            if len(fs_collisions) > 10:
                print(f"     ... and {len(fs_collisions) - 10} more")

    # Show details
    if orphans['no_app_field']:
        print("\n🔧 DOCTYPES WITH NULL APP FIELD:")
        for o in orphans['no_app_field'][:10]:
            print(f"   • {o['name']:<40} → suggested: {o['suggested_app']}")
        if len(orphans['no_app_field']) > 10:
            print(f"   ... and {len(orphans['no_app_field']) - 10} more")

    if orphans['wrong_app']:
        print("\n⚠️ DOCTYPES WITH WRONG APP FIELD:")
        for o in orphans['wrong_app'][:10]:
            print(f"   • {o['name']:<40} current: {o['current_app']}, should be: {o['correct_app']}")
        if len(orphans['wrong_app']) > 10:
            print(f"   ... and {len(orphans['wrong_app']) - 10} more")

    if orphans['no_controller']:
        print("\n🔴 DOCTYPES WITH MISSING .PY CONTROLLER (will be deleted by migrate!):")
        for o in orphans['no_controller'][:15]:
            print(f"   • {o['name']:<40} app: {o['app']}, missing: {os.path.basename(o['py_path'])}")
        if len(orphans['no_controller']) > 15:
            print(f"   ... and {len(orphans['no_controller']) - 15} more")

    if orphans['no_json']:
        print("\n❓ DOCTYPES WITH NO JSON (may be deletable):")
        for o in orphans['no_json'][:10]:
            print(f"   • {o['name']:<40} module: {o['module']}, app: {o['app']}")
        if len(orphans['no_json']) > 10:
            print(f"   ... and {len(orphans['no_json']) - 10} more")

    # Apply fixes
    if not dry_run:
        fixed_count = 0
        deleted_count = 0

        if fix_mode:
            print("\n🔧 APPLYING AUTO-FIX...")

            # Fix NULL app field
            for o in orphans['no_app_field']:
                try:
                    frappe.db.set_value("DocType", o['name'], {
                        'app': o['suggested_app'],
                        'module': o['suggested_module']
                    }, update_modified=False)
                    print(f"   ✅ {o['name']} → app: {o['suggested_app']}")
                    fixed_count += 1
                except Exception as e:
                    print(f"   ❌ {o['name']}: {e}")

            # Fix wrong app field
            for o in orphans['wrong_app']:
                try:
                    frappe.db.set_value("DocType", o['name'], 'app', o['correct_app'], update_modified=False)
                    print(f"   ✅ {o['name']} → app: {o['correct_app']}")
                    fixed_count += 1
                except Exception as e:
                    print(f"   ❌ {o['name']}: {e}")

            frappe.db.commit()

            # Create missing controller files (THE KEY FIX!)
            controllers_created = 0
            if orphans['no_controller']:
                print("\n🔧 CREATING MISSING CONTROLLER FILES...")
                for o in orphans['no_controller']:
                    py_path = o['py_path']
                    dt_name = o['name']

                    # Convert doctype name to class name (Title Case -> PascalCase)
                    # e.g., "TDS Settings" -> "TdsSettings"
                    class_name = ''.join(word.capitalize() for word in dt_name.replace('-', ' ').split())

                    controller_content = f'''import frappe
from frappe.model.document import Document


class {class_name}(Document):
    pass
'''
                    try:
                        with open(py_path, 'w') as f:
                            f.write(controller_content)
                        print(f"   ✅ Created: {py_path}")
                        controllers_created += 1
                    except Exception as e:
                        print(f"   ❌ {dt_name}: {e}")

                print(f"\n✅ Created {controllers_created} controller files")

            print(f"\n✅ Fixed {fixed_count} DocTypes, created {controllers_created} controllers")

        elif reassign:
            print(f"\n🔧 REASSIGNING TO: {reassign}...")
            reassign_module = reassign.replace("_", " ").title()

            all_fixable = orphans['no_app_field'] + orphans['wrong_app']
            for o in all_fixable:
                try:
                    frappe.db.set_value("DocType", o['name'], {
                        'app': reassign,
                        'module': reassign_module
                    }, update_modified=False)
                    print(f"   ✅ {o['name']} → {reassign}")
                    fixed_count += 1
                except Exception as e:
                    print(f"   ❌ {o['name']}: {e}")

            frappe.db.commit()
            print(f"\n✅ Reassigned {fixed_count} DocTypes to {reassign}")

        elif delete_mode:
            if not click.confirm(f"⚠️ DELETE {len(orphans['no_json'])} orphaned DocTypes? This is IRREVERSIBLE!"):
                print("❌ Cancelled")
            else:
                print("\n🗑️ DELETING ORPHANS...")
                for o in orphans['no_json']:
                    try:
                        frappe.delete_doc("DocType", o['name'], force=True)
                        print(f"   🗑️ Deleted: {o['name']}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"   ❌ {o['name']}: {e}")

                frappe.db.commit()
                print(f"\n✅ Deleted {deleted_count} orphaned DocTypes")

        print(f"\n📋 Now run: bench --site {site} migrate")

    else:
        if total_orphans > 0:
            print("\n📋 RESOLUTION OPTIONS:")
            print(f"   bench app-migrator orphans --site {site} --fix --apply")
            print(f"   bench app-migrator orphans --site {site} --reassign <app_name> --apply")
            print(f"   bench app-migrator orphans --site {site} --delete --apply")
        else:
            print("\n✅ No orphaned DocTypes found!")

    frappe.db.close()


