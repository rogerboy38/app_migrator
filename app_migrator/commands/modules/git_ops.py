# app_migrator/commands/modules/git_ops.py
import click
import subprocess
import os

@click.command("git-pull")
@click.option("--app", help="Specific app to pull")
@click.option("--all", "pull_all", is_flag=True, help="Pull all apps")
def git_pull(app, pull_all):
    """Pull latest changes for apps."""
    if app:
        click.echo(f"Pulling {app}...")
        # Implementation for single app
    elif pull_all:
        click.echo("Pulling all apps...")
        # Implementation for all apps

@click.command("git-push")
@click.option("--message", "-m", required=True, help="Commit message")
@click.option("--app", help="Specific app to push")
def git_push(message, app):
    """Push changes to Git repository."""
    click.echo(f"Pushing {app or 'all apps'} with message: {message}")

@click.command("git-info")
@click.option("--app", help="App name")
def git_info(app):
    """Show Git information for apps."""
    # Implementation
