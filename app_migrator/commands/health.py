"""app-migrator-health command (T1.8.2 — extracted from __init__.py)

v0.5-alpha W1 (Coder 2026-06-24): added --json envelope support per Phase 4 contract.
"""

import time

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f

from . import __version__
from ._envelope import emit_envelope, make_envelope


@click.command('app-migrator-health')
@click.option('--json', 'as_json', is_flag=True, help='Emit v0.5 envelope JSON')
@pass_context
def app_migrator_health(context, as_json):
    """Check App Migrator health and list commands"""
    start = time.time()
    if as_json:
        envelope = make_envelope(
            command="health",
            status="ok",
            summary=f"app-migrator v{__version__} operational",
            findings=[
                {
                    "id": "health-ok",
                    "title": "app-migrator health check passed",
                    "severity": "info",
                    "description": f"App Migrator v{__version__} loaded; CLI group registered.",
                },
            ],
            site=None,
            start_time=start,
        )
        emit_envelope(envelope)
    print("=" * 60)
    print(f"🔧 App Migrator v{__version__} - OPERATIONAL")
    print("=" * 60)
    print("\n📋 AVAILABLE COMMANDS:")
    print("  Site Analysis:")
    print("    app-migrator-scan --site <name>          Scan site inventory")
    print("    app-migrator-conflicts --site <name>     Detect conflicts")
    print("  Migration:")
    print("    app-migrator-plan --site <name>          Create migration plan")
    print("    app-migrator-execute --site <name>       Execute migration")
    print("  Multi-Bench:")
    print("    app-migrator-benches                     List all benches")
    print("    app-migrator-apps --site <name>          Downloaded vs installed apps")
    print("    app-migrator-session-start <name>        Start session")
    print("    app-migrator-session-status <id>         Check session")
    print("  Diagnostics:")
    print("    app-migrator-analyze <app>               Analyze app structure")
    print("    app-migrator-fix-orphans --site <name>   Fix orphan doctypes")
    print("    app-migrator-fix-structure <app>         Fix nested folder structure")
    print("  Ping-Pong Staging:")
    print("    app-migrator-create-host <name>          Create staging app")
    print("    app-migrator-stage --site X --source A --host B    Stage doctypes")
    print("    app-migrator-unstage --site X --host B --target C  Unstage doctypes")
    print("=" * 60)
