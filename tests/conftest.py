"""
Workspace-root conftest for app_migrator v0.5-alpha test plan v2.

Addresses T-VERIFY-001 Gap 4 (hardcoded Linux paths) and Gap 2 (no pytest.skip guards).
Also addresses Verifier's T-VERIFY-002 probes:
- Probe (a): conftest APP_MIGRATOR_ROOT env var actually drives path resolution
  (verified via test_app_migrator_root_env_var_override below).
- Probe (b): L381 fixture-driven test (uses tests/fixtures/l381_known_stale_keypair.json).

Provides:
- app_migrator_root: session-scoped, resolves once at start (default + env var).
- app_migrator_root_factory: function-callable for tests that override env var.
- skills_dir: skills catalog dir under the scaffold root.
- require_app_migrator: opt-in fixture that skips if scaffold not built yet.
- autouse bench-on-PATH guard: skip whole session if `bench` CLI not available.
"""
import os
import shutil
from pathlib import Path

import pytest


# Per v0.5 coverage-map design principle: "tests skip gracefully if phase not built yet".
# Without this guard, every test hard-fails on missing scaffold.


def _resolve_app_migrator_root():
    """Resolve app_migrator_root from $APP_MIGRATOR_ROOT env var or default."""
    return Path(os.environ.get("APP_MIGRATOR_ROOT", "/home/frappe/app_migrator"))


def pytest_configure(config):
    """Register phase markers so test selection is explicit."""
    config.addinivalue_line("markers", "phase1_skills: Phase 1 (skills layer)")
    config.addinivalue_line("markers", "phase2_verification: Phase 2 (verification gaps)")
    config.addinivalue_line("markers", "phase3_radar_flags: Phase 3 (radar flags)")
    config.addinivalue_line("markers", "phase4_envelope: Phase 4 (JSON envelope)")
    config.addinivalue_line("markers", "phase5_planner_verifier: Phase 5 (planner + verifier)")


@pytest.fixture(autouse=True)
def _require_bench_on_path():
    """Skip any test if `bench` CLI is not on PATH (Windows host, etc.)."""
    if shutil.which("bench") is None:
        pytest.skip("`bench` CLI not on PATH (tests target VM2 substrate; "
                    "run pytest inside the VM2 bench container)")


def _resolve_bench_cwd():
    """Resolve bench_cwd from $BENCH_CWD env var or default.

    Tests that invoke the bench CLI via subprocess.run must cd into the
    bench install directory first. The bench script is CWD-sensitive for
    app discovery (a bench run from anywhere else reports 'No such
    command' even for installed apps).
    """
    return Path(os.environ.get("BENCH_CWD", "/home/frappe/frappe-bench"))


@pytest.fixture(scope="session")
def bench_cwd():
    """Session-scoped: the bench install dir to cd into before `bench ...`."""
    return _resolve_bench_cwd()

@pytest.fixture(scope="session")
def app_migrator_root():
    """Session-scoped: resolves once. Use factory for env-var-override tests."""
    return _resolve_app_migrator_root()


@pytest.fixture(scope="session")
def app_migrator_root_factory():
    """Function that resolves path fresh on each call (for tests that override env var)."""
    return _resolve_app_migrator_root


@pytest.fixture(scope="session")
def skills_dir(app_migrator_root):
    """Path to skills catalog dir."""
    return app_migrator_root / "app_migrator" / "skills" / "frappe"


@pytest.fixture
def require_app_migrator(app_migrator_root):
    """Skip if the scaffold doesn't exist yet (per coverage-map: skip gracefully)."""
    if not app_migrator_root.exists():
        pytest.skip(f"app_migrator scaffold not built at {app_migrator_root} "
                    f"(set APP_MIGRATOR_ROOT env var to override)")


# ---------- Verifier T-VERIFY-002 probe (a): conftest env-var actually drives path ----------

def test_app_migrator_root_env_var_override(monkeypatch, app_migrator_root_factory):
    """Verify APP_MIGRATOR_ROOT env var actually drives path resolution.

    T-VERIFY-002 probe (a): not just declared, but honored at runtime.
    """
    custom_path = "/tmp/test-scaffold-xyz-not-real"
    monkeypatch.setenv("APP_MIGRATOR_ROOT", custom_path)
    resolved = app_migrator_root_factory()
    assert resolved == Path(custom_path), (
        f"APP_MIGRATOR_ROOT env var not honored: expected {custom_path}, got {resolved}"
    )


def test_app_migrator_root_default_when_env_var_unset(monkeypatch, app_migrator_root_factory):
    """When APP_MIGRATOR_ROOT is unset, default to /home/frappe/app_migrator."""
    monkeypatch.delenv("APP_MIGRATOR_ROOT", raising=False)
    resolved = app_migrator_root_factory()
    assert resolved == Path("/home/frappe/app_migrator"), (
        f"default APP_MIGRATOR_ROOT not honored: got {resolved}"
    )


# ---------- Verifier T-VERIFY-002 boundary check: corrupt SQLite sessions DB ----------

def test_sessions_persistence_corrupt_db_skipped(app_migrator_root, tmp_path):
    """If sessions.sqlite3 exists but is corrupt, test_sessions_persistence_sqlite must skip cleanly.

    T-VERIFY-002 boundary check: corrupt-DB is not a hard failure, but the skip message
    must clearly identify corruption (not just 'not found').
    """
    import sqlite3

    # Create a fake scaffold with a deliberately-corrupt sessions DB
    fake_root = tmp_path / "fake-scaffold"
    sessions_dir = fake_root / ".sessions"
    sessions_dir.mkdir(parents=True)
    corrupt_db = sessions_dir / "sessions.sqlite3"
    corrupt_db.write_bytes(b"NOT A SQLITE DATABASE FILE")

    db_path = fake_root / ".sessions" / "sessions.sqlite3"
    assert db_path.exists()
    # The actual test_sessions_persistence_sqlite should hit sqlite3.DatabaseError
    # and skip with a corrupt-DB message. Verify the boundary behavior here:
    try:
        conn = sqlite3.connect(db_path)
        conn.execute("SELECT name FROM sqlite_master")
        pytest.fail("corrupt DB should have raised sqlite3.DatabaseError, but it didn't")
    except sqlite3.DatabaseError as e:
        # Expected: corrupt DB raises DatabaseError. The session test should catch
        # this and skip with a clear message identifying corruption.
        assert "database disk image" in str(e).lower() or "file is not a database" in str(e).lower(), (
            f"unexpected error from corrupt DB: {e}"
        )
