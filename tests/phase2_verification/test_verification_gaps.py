"""
Phase 2 tests v2: Verification gaps (T3 Priority 2).

Validates that 4 verification lessons (L381, L398, L413, L419) are embodied in code.

v2 changes (per T-VERIFY-001 Verifier review):
- Gap 1: L381 drift test is NO LONGER CIRCULAR. The fake returns two hash inputs;
  the function under test must DERIVE drift_detected from comparing them.
- Added NEGATIVE CASES for L381, L398, L413 (function must NOT flag when input is clean).
- Each test has pytest.importorskip or require_app_migrator guard for portability.
"""
import subprocess

import pytest


@pytest.fixture
def require_app_migrator():
    """Skip if app_migrator module not importable."""
    pytest.importorskip("app_migrator", reason="app_migrator module not yet built")


# ---------- L381: encryption-key drift on site restore ----------
# v2.1: Load known-stale key sample from fixture file (per Verifier T-VERIFY-002 probe b).
# The fixture provides external data (not a return-the-truth mock in disguise).
# The fake_get_database_info reads from the fixture and returns the two hashes.
# The function under test must COMPARE them and DERIVE drift_detected.

import json as _json
from pathlib import Path as _Path

FIXTURES_DIR = _Path(__file__).parent.parent / "fixtures"
L381_FIXTURE_PATH = FIXTURES_DIR / "l381_known_stale_keypair.json"


def _load_l381_fixture():
    """Load the known-stale key sample. Skip if fixture missing."""
    if not L381_FIXTURE_PATH.exists():
        pytest.skip(f"L381 fixture not yet created at {L381_FIXTURE_PATH}")
    return _json.loads(L381_FIXTURE_PATH.read_text())


def test_l381_drift_detected_when_hashes_differ(monkeypatch, require_app_migrator):
    """L381: detect_encryption_key_drift must derive drift from comparing two hashes.

    v2.1 fix (per Verifier T-VERIFY-002 probe b): input comes from an EXTERNAL fixture
    file, not an in-test return-the-truth mock. The fake_get_database_info reads the
    fixture and returns its two hashes. The function under test must COMPARE them
    and output drift_detected (NOT echo any pre-computed value, which the fixture
    does not contain).
    """
    from app_migrator.verification import encryption_intel

    fixture = _load_l381_fixture()

    def fake_get_database_info(site):
        # Return ONLY the two hashes from the fixture; no drift_detected field
        return {
            "site_config": fixture["site_config"],
            "site_local_db": fixture["site_local_db"],
        }

    monkeypatch.setattr(encryption_intel, "get_database_info", fake_get_database_info)

    result = encryption_intel.detect_encryption_key_drift(site=fixture["site_name"])
    assert result["drift_detected"] is True, (
        f"Different hashes from fixture {fixture['site_config']['encryption_key_hash']} "
        f"vs {fixture['site_local_db']['encryption_key_hash']} should derive "
        f"drift_detected=True; got {result}"
    )


def test_l381_no_drift_when_hashes_match(monkeypatch, require_app_migrator):
    """L381 negative case: matching hashes must yield drift_detected=False."""
    from app_migrator.verification import encryption_intel

    # Build a same-hash fixture inline (no need for a separate file)
    fake_db_info = {
        "site_config": {"encryption_key_hash": "SAME_HASH_INLINE"},
        "site_local_db": {"encryption_key_hash": "SAME_HASH_INLINE"},
    }

    def fake_get_database_info(site):
        return fake_db_info

    monkeypatch.setattr(encryption_intel, "get_database_info", fake_get_database_info)

    result = encryption_intel.detect_encryption_key_drift(site="test.localhost")
    assert result["drift_detected"] is False, (
        f"Identical hashes should derive drift_detected=False; got {result}"
    )


# ---------- L398: blanket inspection_required_before_delivery rejected ----------

def test_l398_blanket_enable_is_flagged(monkeypatch, require_app_migrator):
    """L398: blanket inspection_required_before_delivery=1 must be flagged.

    Input: 2 doctypes both with the field = 1.
    Function must flag BOTH as blanket-enabled.
    """
    from app_migrator.verification import data_quality

    blanket_enabled = [
        {"name": "Sales Invoice", "inspection_required_before_delivery": 1},
        {"name": "Delivery Note", "inspection_required_before_delivery": 1},
    ]
    result = data_quality.verify_data_integrity(app="test_app", doctypes=blanket_enabled)
    flagged = [
        d for d in result.get("flagged", [])
        if "inspection_required_before_delivery" in d.get("reason", "")
    ]
    assert len(flagged) >= len(blanket_enabled), (
        f"L398: all {len(blanket_enabled)} blanket-enabled doctypes should be flagged; "
        f"got {len(flagged)}: {flagged}"
    )


def test_l398_selective_enable_not_flagged_as_blanket(monkeypatch, require_app_migrator):
    """L398 negative case: selective enable (some = 1, some = 0) is allowed and not blanket-flagged."""
    from app_migrator.verification import data_quality

    selective = [
        {"name": "Sales Invoice", "inspection_required_before_delivery": 1},
        {"name": "Item", "inspection_required_before_delivery": 0},
    ]
    result = data_quality.verify_data_integrity(app="test_app", doctypes=selective)
    blanket_flagged = [
        d for d in result.get("flagged", [])
        if any(kw in d.get("reason", "").upper() for kw in ["BLANKET", "ALL DOCTYPES", "MASS"])
    ]
    assert len(blanket_flagged) == 0, (
        f"L398 negative: selective enable incorrectly flagged as blanket: {blanket_flagged}"
    )


# ---------- L413: multi-host branch guard ----------

def test_l413_branch_mismatch_flagged(monkeypatch, require_app_migrator):
    """L413: bench on wrong branch must be flagged with branch_warning."""
    from app_migrator.commands import multi_bench

    def fake_run(cmd, *args, **kwargs):
        if any("rev-parse" in str(c) for c in cmd):
            return subprocess.CompletedProcess(cmd, 0, stdout=b"main\n", stderr=b"")
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    benches = multi_bench.detect_available_benches_simple(expected_branch="release/v10.2.0")
    flagged = [b for b in benches if b.get("branch_warning")]
    on_main = [b for b in flagged if b.get("current_branch") == "main"]
    assert len(on_main) >= 1, (
        f"L413: bench on 'main' should be flagged when 'release/v10.2.0' expected; "
        f"got benches={benches}"
    )


def test_l413_branch_match_not_flagged(monkeypatch, require_app_migrator):
    """L413 negative case: bench on expected branch must NOT be flagged."""
    from app_migrator.commands import multi_bench

    def fake_run(cmd, *args, **kwargs):
        if any("rev-parse" in str(c) for c in cmd):
            return subprocess.CompletedProcess(cmd, 0, stdout=b"release/v10.2.0\n", stderr=b"")
        return subprocess.CompletedProcess(cmd, 0, stdout=b"", stderr=b"")

    monkeypatch.setattr(subprocess, "run", fake_run)
    benches = multi_bench.detect_available_benches_simple(expected_branch="release/v10.2.0")
    flagged = [b for b in benches if b.get("branch_warning")]
    assert len(flagged) == 0, (
        f"L413 negative: matching branch should NOT be flagged; got {flagged}"
    )


# ---------- L419: flt-coercion pattern in pattern_database ----------

def test_l419_flt_coercion_pattern_registered(require_app_migrator):
    """L419: pattern_database must include a flt/unit-coercion pattern.

    Substring check on title+description is appropriate here because the question
    is "does the database contain a pattern ABOUT unit-coercion?" not "does
    the function transform input correctly?".
    """
    from app_migrator.intelligence.engine import MigrationIntelligence

    intel = MigrationIntelligence()
    patterns = intel.pattern_database
    matches = [
        p for p in patterns
        if any(kw in (p.get("title", "") + " " + p.get("description", "")).lower()
               for kw in ["flt", "unit", "coerc", "value-parse"])
    ]
    assert len(matches) >= 1, (
        f"L419: pattern_database missing flt-coercion pattern; "
        f"pattern titles: {[p.get('title') for p in patterns]}"
    )
