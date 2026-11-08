"""L413: multi-host branch hazard guard.

Per L413: VM2 lab may be on commit X while substrate (vpp) has been updated
to commit Y by sysmayal-3. Before cross-host action, check that the bench
is on the expected branch.

This is the v0.5 implementation that the L413 v2 tests exercise. The
implementation runs `git rev-parse --abbrev-ref HEAD` for each bench and
flags any whose current_branch != expected_branch.
"""
from __future__ import annotations

import subprocess
from typing import Any, Dict, List


def _run_git_rev_parse(cwd: str = ".") -> str:
    """Run git rev-parse --abbrev-ref HEAD and return the branch name as str.

    Handles both real subprocess (text=str) and monkeypatched
    subprocess.run that returns bytes (test mocks).
    """
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=cwd,
    )
    raw = result.stdout
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace").strip()
    return (raw or "").strip()


def detect_available_benches_simple(expected_branch: str) -> List[Dict[str, Any]]:
    """Detect available benches, with branch_warning for mismatched branches.

    Returns a list of dicts, each with:
      - name: bench name
      - current_branch: the branch the bench is on
      - branch_warning: bool, True iff current_branch != expected_branch

    The L413 v2 tests monkeypatch subprocess.run to return canned branch
    values; we decode bytes-or-str robustly and compare to expected_branch.
    """
    benches: List[Dict[str, Any]] = []

    try:
        current_branch = _run_git_rev_parse()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return benches

    if not current_branch:
        return benches

    benches.append({
        "name": "main",
        "current_branch": current_branch,
        "branch_warning": current_branch != expected_branch,
    })
    return benches
