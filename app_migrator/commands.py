"""
App Migrator CLI Commands v8.1.0
Main entry point for all app_migrator bench commands

Commands:
- migrate-app health: Health check
- migrate-app scan-site: Scan site for apps, doctypes, custom fields
- migrate-app detect-conflicts: Find conflicts between apps
- migrate-app generate-plan: Generate migration plan
- migrate-app execute-plan: Execute migration with dry-run support
- migrate-app fix-app: Fix common app structural issues
"""

import click
from frappe.commands import pass_context, get_site

# Import command implementations
from app_migrator.commands.migration_commands import (
    scan_site,
    detect_conflicts,
    generate_plan,
    execute_plan
)
from app_migrator.commands.fix_app import fix_app


@click.group('migrate-app')
def migrate_app():
    """App Migrator commands for Frappe v16 migration"""
    pass


@migrate_app.command('health')
@pass_context
def health_command(context):
    """Check App Migrator health and version"""
    site = get_site(context)
    print("=" * 50)
    print("🔧 App Migrator Health Check")
    print("=" * 50)
    print(f"   Version: 8.1.0")
    print(f"   Site: {site}")
    print(f"   Status: ✅ OPERATIONAL")
    print()
    print("📋 Available Commands:")
    print("   • scan-site        - Scan site inventory")
    print("   • detect-conflicts - Find app conflicts")
    print("   • generate-plan    - Create migration plan")
    print("   • execute-plan     - Run migration (dry-run/apply)")
    print("   • fix-app          - Fix app structure issues")
    print("=" * 50)


# Register all commands
migrate_app.add_command(scan_site)
migrate_app.add_command(detect_conflicts)
migrate_app.add_command(generate_plan)
migrate_app.add_command(execute_plan)
migrate_app.add_command(fix_app)


# Export the command group for Frappe to discover
commands = [migrate_app]
