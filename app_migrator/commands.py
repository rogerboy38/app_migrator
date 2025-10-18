import click
from frappe.commands import pass_context, get_site

@click.group('migrate-app')
def migrate_app():
    """App Migrator commands"""
    pass

@migrate_app.command('health')
@pass_context
def health_command(context):
    """Check App Migrator health"""
    site = get_site(context)
    print(f"✅ App Migrator Health Check - Site: {site}")
    print("   - Version: 6.1.0")
    print("   - Status: COMMAND GROUP WORKING!")

# Export the command group
commands = [migrate_app]
