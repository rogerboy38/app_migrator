"""Session management commands (T1.8.3 — extracted from __init__.py).

Holds both session-start and session-status — combined per Phase 1 plan
since they're a logical pair.
"""

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f
from ._shared import MigrationSession


@click.command('app-migrator-session-start')
@click.argument('name')
@pass_context
def app_migrator_session_start(context, name):
    """Start a new migration session"""
    session = MigrationSession(name)
    session_id = session.save()
    print(f"✅ Session started: {name}")
    print(f"📁 Session ID: {session_id}")
    print(f"\n   Check status: bench app-migrator-session-status {session_id}")


@click.command('app-migrator-session-status')
@click.argument('session_id')
@pass_context
def app_migrator_session_status(context, session_id):
    """Check migration session status"""
    data = MigrationSession.load(session_id)
    if not data:
        print(f"❌ Session not found: {session_id}")
        return

    print("📊 SESSION STATUS")
    print("=" * 40)
    print(f"   Name: {data['metadata']['name']}")
    print(f"   ID: {data['metadata']['session_id']}")
    print(f"   Status: {data['metadata']['status'].upper()}")
    print(f"   Started: {data['metadata']['start_time']}")
    print(f"   Completed Apps: {len(data['progress']['completed_apps'])}")
    print(f"   Failed Apps: {len(data['progress']['failed_apps'])}")
