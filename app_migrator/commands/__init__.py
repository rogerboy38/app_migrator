import click
from frappe.commands import pass_context

@click.command('migrate-app')
@click.argument('action')
@pass_context
def migrate_app(context, action):
    """Migrate apps using App Migrator"""
    if action == 'help':
        click.echo("App Migrator v6.0.0")
        click.echo("Available commands: help, version")
    elif action == 'version':
        click.echo("App Migrator v6.0.0")
    else:
        click.echo(f"Command: {action}")

# ⚠️ CRITICAL: This line makes Frappe discover the command
commands = [migrate_app]
