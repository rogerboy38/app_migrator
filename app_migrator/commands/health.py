"""app-migrator-health command (T1.8.2 — extracted from __init__.py)"""

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    pass_context = lambda f: f

from . import __version__


@click.command('app-migrator-health')
@pass_context
def app_migrator_health(context):
    """Check App Migrator health and list commands"""
    print("=" * 60)
    print(f"🔧 App Migrator Enterprise v{__version__} - OPERATIONAL")
    print("=" * 60)
    print("\n📋 AVAILABLE COMMANDS:")
    print("  Site Analysis:")
    print("    app-migrator-scan --site <name>          Scan site inventory")
    print("    app-migrator-conflicts --site <name>     Detect conflicts")
    print("  Migration:")
    print("    app-migrator-plan --site <name>          Create migration plan")
    print("    app-migrator-execute --site <name>       Execute migration")
    print("  Enterprise:")
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
