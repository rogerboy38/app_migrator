"""app-migrator-scan command (T1.8.2 — extracted from __init__.py)

v0.5-alpha W1 (Coder 2026-06-24): added --json envelope support per Phase 4 contract.
When --json is set, --site becomes optional; without --json, --site is required.
"""

import json
import sys
import time
from datetime import datetime

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f

from ._envelope import emit_envelope, make_envelope


@click.command('app-migrator-scan')
@click.option('--json', 'as_json', is_flag=True, help='Emit v0.5 envelope JSON (wraps the real scan result)')
@click.option('--site', default=None, help='Site name (required)')
@click.option('--output', '-o', help='Output JSON file (full scan result)')
@pass_context
def app_migrator_scan(context, as_json, site, output):
    """Scan site for apps, doctypes, custom fields.

    v0.5 W3 fix #2: --json now wraps the REAL scan result (not a stub). Requires
    --site. When --output is also given, the full result is written to the file.
    """
    start = time.time()

    # --site is required for a real scan. Under --json, surface that as a valid
    # error envelope (not a raw exit) so the envelope contract always holds.
    if not site:
        if as_json:
            emit_envelope(make_envelope(
                command="scan",
                status="error",
                summary="scan failed: no site (pass --site)",
                findings=[{
                    "id": "scan-no-site",
                    "title": "No site specified",
                    "severity": "high",
                    "description": "scan requires --site to read apps/doctypes/custom fields.",
                }],
                start_time=start,
            ))
        click.echo("Error: --site is required", err=True)
        sys.exit(2)

    # Single code path: always run the real scan. Under --json, DB/scan failures
    # become an error envelope instead of an unhandled traceback.
    try:
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

        doctypes = frappe.get_all("DocType", fields=["name", "module", "custom", "istable"])
        result["doctypes"] = [dict(dt) for dt in doctypes]

        custom_fields = frappe.get_all("Custom Field", fields=["name", "dt", "fieldname", "fieldtype"])
        result["custom_fields"] = [dict(cf) for cf in custom_fields]

        result["summary"] = {
            "apps": len(result["apps"]),
            "doctypes": len(result["doctypes"]),
            "custom_doctypes": len([d for d in doctypes if d.custom]),
            "child_tables": len([d for d in doctypes if d.istable]),
            "custom_fields": len(result["custom_fields"])
        }

        frappe.db.close()
    except Exception as e:
        if as_json:
            emit_envelope(make_envelope(
                command="scan",
                status="error",
                summary=f"scan failed: {type(e).__name__}",
                findings=[{
                    "id": "scan-error",
                    "title": "Scan failed",
                    "severity": "high",
                    "description": str(e),
                }],
                site=site,
                start_time=start,
            ))
        raise

    # Full result goes to --output regardless of mode.
    if output:
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)

    if as_json:
        s = result["summary"]
        emit_envelope(make_envelope(
            command="scan",
            status="ok",
            summary=(
                f"scan completed: {s['apps']} apps, {s['doctypes']} doctypes "
                f"({s['custom_doctypes']} custom, {s['child_tables']} child tables), "
                f"{s['custom_fields']} custom fields"
            ),
            findings=[{
                "id": "scan-summary",
                "title": "Scan summary",
                "severity": "info",
                "description": (
                    f"{s['apps']} apps / {s['doctypes']} doctypes / "
                    f"{s['custom_doctypes']} custom / {s['child_tables']} child tables / "
                    f"{s['custom_fields']} custom fields"
                ),
            }],
            evidence=[{"type": "scan_summary", "data": s}],
            suggested_next_commands=[{
                "command": "bench app-migrator diagnose <app> --json",
                "approval_required": False,
                "description": "Diagnose the scanned app.",
            }],
            site=site,
            start_time=start,
        ))

    # Non-JSON text display.
    print(f"🔍 Scanning site: {site}")
    print("=" * 60)
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
        print(f"\n✅ Saved to: {output}")
