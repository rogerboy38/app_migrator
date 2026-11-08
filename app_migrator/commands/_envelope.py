"""v0.5-alpha W1: JSON envelope builder for app-migrator commands.

Per v0.5 spec Phase 0 envelope design (T-VERIFY-002 ratified):
- schema_version=1.0.0
- status in {ok/warn/blocked/error} with rc mapping {0/10/20/40}
  (rc=30 was removed in Q4 fold-in; canonical 4-status enum only)
- REQUIRED_ENVELOPE_KEYS = {schema_version, command, site, status, summary,
  findings, risks, suggested_next_commands, evidence, meta}
- meta has bench_version, app_migrator_commit, timestamp, duration_ms, host
- findings carry stable id (for diffing across runs)
- suggested_next_commands carry approval_required (for destructive steps)
"""
from __future__ import annotations

import datetime
import json
import socket
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional

SCHEMA_VERSION = "1.0.0"

# Canonical 4-status enum per Q4 fold-in. rc=30 was a leftover and is removed.
EXIT_CODE_MAPPING = {"ok": 0, "warn": 10, "blocked": 20, "error": 40}

# Bench app dir for git commit lookup.
_APP_DIR = "/home/frappe/frappe-bench/apps/app_migrator"


def _bench_version() -> str:
    """Return bench CLI version string (or 'unknown')."""
    try:
        out = subprocess.run(
            ["bench", "--version"], capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _app_migrator_commit() -> str:
    """Return short git SHA for the app_migrator bench app (or 'unknown')."""
    try:
        out = subprocess.run(
            ["git", "-C", _APP_DIR, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _current_site() -> str:
    """Return current bench site name (or 'unknown').

    Reads /home/frappe/frappe-bench/sites/currentsite.txt — the canonical
    source-of-truth maintained by `bench use <site>`. Replaces the prior
    `bench find site` call which hangs indefinitely on this substrate
    (W1 close-out receipt note: bench CLI subprocess hangs ~60s+ on this
    bench install).

    Preserves the 5s subprocess.run timeout pattern as a defensive guard
    against slow FS reads under load (L417 doctrine: do not eliminate
    defensive patterns; only swap the lookup mechanism).
    """
    currentsite_file = "/home/frappe/frappe-bench/sites/currentsite.txt"
    try:
        out = subprocess.run(
            ["cat", currentsite_file],
            capture_output=True, text=True, timeout=5,
        )
        site = out.stdout.strip() if out.stdout else ""
        return site or "unknown"
    except Exception:
        return "unknown"


def make_envelope(
    command: str,
    status: str = "ok",
    summary: str = "",
    findings: Optional[List[Dict[str, Any]]] = None,
    risks: Optional[List[Dict[str, Any]]] = None,
    suggested_next_commands: Optional[List[Dict[str, Any]]] = None,
    evidence: Optional[List[Dict[str, Any]]] = None,
    site: Optional[str] = None,
    start_time: Optional[float] = None,
) -> Dict[str, Any]:
    """Build a v0.5-alpha W1 envelope payload dict.

    Caller is responsible for passing stable-id'd findings and approval-flagged
    suggested_next_commands; this builder does NOT auto-fill those.
    """
    if start_time is None:
        start_time = time.time()
    duration_ms = int((time.time() - start_time) * 1000)
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "site": site if site else _current_site(),
        "status": status,
        "summary": summary,
        "findings": findings if findings is not None else [],
        "risks": risks if risks is not None else [],
        "suggested_next_commands": (
            suggested_next_commands if suggested_next_commands is not None else []
        ),
        "evidence": evidence if evidence is not None else [],
        "meta": {
            "bench_version": _bench_version(),
            "app_migrator_commit": _app_migrator_commit(),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "duration_ms": duration_ms,
            "host": socket.gethostname(),
        },
    }


def emit_envelope(envelope: Dict[str, Any]) -> None:
    """Print envelope as JSON to stdout, exit with status-mapped rc.

    Never returns: sys.exit(rc) terminates the process. The mapped rc comes
    from EXIT_CODE_MAPPING (ok=0, warn=10, blocked=20, error=40).
    """
    rc = EXIT_CODE_MAPPING.get(envelope.get("status", "ok"), 0)
    sys.stdout.write(json.dumps(envelope, indent=2, sort_keys=True) + "\n")
    sys.stdout.flush()
    sys.exit(rc)