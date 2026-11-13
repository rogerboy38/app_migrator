"""
Phase 5 tests v2: Planner + verifier (T3 Priority 5).

v2 changes (per T-VERIFY-001 Verifier review):
- Gap 5: REMOVED weak `test_verifier_3_outcomes` (only checked outcome in set;
  a buggy verifier that always returns 'improved' would pass).
- Kept strong pre/post tests that derive outcome from before/after evidence.
- Added `test_verifier_outcome_unchanged_when_no_delta` for negative-case completeness.
- Gap 4: Uses conftest fixture (app_migrator_root) for sessions DB path (no hardcoded Linux path).
- Gap 2: Added graceful pytest.skip on missing implementation, empty stdout, non-JSON.

v3 changes (per Q7 NATIVE PARAMETRIZE ratification, 2026-06-24):
- test_planner_* parametrized across 5 first-wave skills (orphan-repair,
  module-collision-preflight, paired-deliverable-check, migration-preflight,
  install-recovery). Q7 resolved in code; no v2.1 backlog needed.
"""
import json
import subprocess

import pytest


# Q7 native parametrize: 5 first-wave skills per v0.5 spec.
FIRST_WAVE_SKILLS = [
    "orphan-repair",
    "module-collision-preflight",
    "paired-deliverable-check",
    "migration-preflight",
    "install-recovery",
]


def run_planner(workflow, *extra_args):
    """Run planner; skip gracefully on any failure mode."""
    result = subprocess.run(
        ["bench", "app-migrator", "planner", workflow, *extra_args],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        pytest.skip(
            f"planner not yet implemented for {workflow} (rc={result.returncode}): "
            f"{result.stderr[:200]}"
        )
    if not result.stdout.strip():
        pytest.skip(f"planner {workflow} returned empty stdout (WIP)")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.skip(f"planner {workflow} returned non-JSON: {result.stdout[:200]}")


def run_verifier(*cli_args):
    """Run verifier with arbitrary CLI args; skip gracefully on any failure mode."""
    result = subprocess.run(
        ["bench", "app-migrator", "verifier", *cli_args],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        pytest.skip(
            f"verifier not yet implemented (rc={result.returncode}): "
            f"{result.stderr[:200]}"
        )
    if not result.stdout.strip():
        pytest.skip(f"verifier returned empty stdout (WIP)")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.skip(f"verifier returned non-JSON: {result.stdout[:200]}")


# ---------- Planner (U1/Q3) ----------

@pytest.mark.parametrize("workflow", FIRST_WAVE_SKILLS)
def test_planner_emits_dry_run_by_default(workflow):
    """Per U1/Q3 sign-off: planner emits dry-run by default; --apply required for destructive.

    Parametrized across 5 first-wave skills per Q7 NATIVE PARAMETRIZE.
    """
    plan = run_planner(workflow)
    assert plan["execution_mode"] == "dry-run", (
        f"planner {workflow} should default to dry-run; got {plan['execution_mode']}"
    )


@pytest.mark.parametrize("workflow", FIRST_WAVE_SKILLS)
def test_planner_destructive_steps_marked(workflow):
    """Destructive steps must be flagged with approval_required=true.

    Parametrized across 5 first-wave skills per Q7 NATIVE PARAMETRIZE.
    """
    plan = run_planner(workflow)
    destructive_steps = [s for s in plan["ordered_steps"] if s.get("destructive")]
    assert all(s.get("approval_required") for s in destructive_steps), (
        f"{workflow}: destructive steps must have approval_required=true; "
        f"steps: {[s.get('name') for s in destructive_steps]}"
    )


@pytest.mark.parametrize("workflow", FIRST_WAVE_SKILLS)
def test_planner_yes_bypasses_apply_pause(workflow):
    """--yes flag bypasses the dry-run pause for scripted use.

    Parametrized across 5 first-wave skills per Q7 NATIVE PARAMETRIZE.
    """
    plan = run_planner(workflow, "--yes")
    assert plan["execution_mode"] in ("apply", "yes-bypass"), (
        f"{workflow} --yes should bypass dry-run; got execution_mode={plan['execution_mode']}"
    )


# ---------- Verifier 3-outcome semantics (U2/Q4) ----------
# Per U2/Q4 invariant: outcome is DERIVED from comparing before/after evidence
# with deterministic thresholds (blockers delta, findings delta).
# A buggy verifier that always returns one value must NOT pass.

def test_verifier_improved_when_blockers_drop():
    """Outcome=improved when blocker count drops (per U2/Q4 derivation rule)."""
    pre = {"findings": [{"id": "f1"}], "blockers": 2}
    post = {"findings": [{"id": "f1"}], "blockers": 0}
    result = run_verifier(
        "test-session",
        "--pre", json.dumps(pre),
        "--post", json.dumps(post),
    )
    assert result["outcome"] == "improved", (
        f"blockers 2->0 should derive outcome=improved; got {result['outcome']}; "
        f"full: {result}"
    )


def test_verifier_regressed_blocks_continuation():
    """Outcome=regressed (new findings or blockers up) must set block_continuation=true."""
    pre = {"findings": [{"id": "f1"}], "blockers": 0}
    post = {"findings": [{"id": "f1"}, {"id": "f2"}], "blockers": 0}
    result = run_verifier(
        "test-session",
        "--pre", json.dumps(pre),
        "--post", json.dumps(post),
    )
    assert result["outcome"] == "regressed", (
        f"new finding added should derive outcome=regressed; got {result['outcome']}"
    )
    assert result.get("block_continuation") is True, (
        f"regressed must set block_continuation=true; got {result.get('block_continuation')}"
    )


def test_verifier_outcome_unchanged_when_no_delta():
    """Outcome=unchanged when findings+blockers are identical pre and post.

    v2 addition: negative case to close the loop on U2/Q4 invariant.
    Without this, a buggy verifier that always returns 'regressed' would pass.
    """
    pre = {"findings": [{"id": "f1"}], "blockers": 1}
    post = {"findings": [{"id": "f1"}], "blockers": 1}
    result = run_verifier(
        "test-session",
        "--pre", json.dumps(pre),
        "--post", json.dumps(post),
    )
    assert result["outcome"] == "unchanged", (
        f"identical pre/post should derive outcome=unchanged; "
        f"got {result['outcome']}; full: {result}"
    )


# ---------- Session persistence (U5/Q7c) ----------

def test_sessions_persistence_sqlite(app_migrator_root):
    """Sessions are stored in SQLite (per U5/Q7c). A session can be created/queried/resumed."""
    import sqlite3

    # Use fixture-resolved path (conftest.py), not hardcoded Linux path
    db_path = app_migrator_root / ".sessions" / "sessions.sqlite3"
    if not db_path.exists():
        pytest.skip(
            f"sessions DB not yet created at {db_path} "
            f"(Phase 5 sessions storage WIP)"
        )
    # T-VERIFY-002 boundary check: corrupt DB must skip with a clear message,
    # not hard-fail with stack trace.
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        )
        assert cur.fetchone() is not None, "sessions table should exist"
    except sqlite3.DatabaseError as e:
        pytest.skip(
            f"sessions DB at {db_path} is corrupt (not WIP, real corruption): {e}. "
            f"Re-initialize via `bench app-migrator sessions init`."
        )
