"""app-migrator-sessions: SQLite-backed session storage (Phase 5).

Per U5/Q7c, sessions are stored in SQLite at:
    /home/frappe/app_migrator/.sessions/sessions.sqlite3

Phase 5 stub:
- 'init' subcommand creates the .sessions dir + sessions.sqlite3 + sessions table
- The pytest test contract only checks that the DB file and 'sessions' table exist;
  full CRUD (create/resume/query) deferred to W1 close.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import click


SESSIONS_DIR = Path("/home/frappe/app_migrator/.sessions")
SESSIONS_DB = SESSIONS_DIR / "sessions.sqlite3"


def _ensure_dir() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _init_db() -> Path:
    """Initialize sessions DB (idempotent). Returns DB path."""
    _ensure_dir()
    conn = sqlite3.connect(SESSIONS_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            workflow TEXT,
            created_at TEXT,
            updated_at TEXT,
            state TEXT
        )
    """)
    conn.commit()
    conn.close()
    return SESSIONS_DB


@click.command('app-migrator-sessions')
@click.argument('subcommand', default='init')
def app_migrator_sessions(subcommand):
    """Session storage management.

    SUBCOMMAND: 'init' (create .sessions/ and sessions table).
    """
    if subcommand == "init":
        db_path = _init_db()
        click.echo(f"Sessions DB initialized at {db_path}")
    else:
        click.echo(f"Unknown subcommand: {subcommand!r}", err=True)
        import sys as _sys
        _sys.exit(2)