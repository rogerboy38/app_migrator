"""
Phase 3 tests v3: Radar flags (T3 Priority 3, L394).

v2 changes (per T-VERIFY-001 Verifier review):
- Gap 2: Added module-level pytest.importorskip guard so all tests skip gracefully
  if app_migrator.intelligence.engine not yet built.

v3 changes (W2 (e) — full pattern_database re-export):
- pattern_database grown from 3 -> 10 (re-export from intelligence_engine.py).
- Parametrized coverage: each re-exported pattern id is asserted present, carries
  a valid severity, and exposes a working detect(content) callable.
"""
import pytest

# Per coverage-map: skip the whole phase gracefully if module not yet built.
pytest.importorskip(
    "app_migrator.intelligence.engine",
    reason="app_migrator.intelligence.engine not yet built (Phase 3 WIP)",
)

from app_migrator.intelligence.engine import MigrationIntelligence, severity_for_risk

VALID_SEVERITIES = {"info", "warn", "high", "critical"}

# Every pattern id the W2(e) re-export must expose, paired with a content sample
# that its detect() callable is expected to flag True.
EXPECTED_PATTERNS = {
    "flt_coercion_failure": "value = flt(row.qty)",
    "l394_fixture_drift": "fixtures regenerate drift after db cleanup",
    "l394_symbol_collision": "raise ImportError('duplicate symbol')",
    "apps_txt_instability": "bench migrate rewrote apps.txt",
    "version_conflicts": "__version__ = '1.2.3'",
    "payment_gateway_dependency": "import stripe  # payment gateway",
    "hardcoded_secrets": "STRIPE_KEY = 'sk_live_abc123def456'",
    "webhook_dependency": "webhook_url = 'https://x/hook'",
    "encryption_compatibility": "from cryptography.fernet import Fernet",
    "frappe_cloud_dependency": "key = os.environ['FRAPPE_CLOUD_API_KEY']",
}


@pytest.fixture(scope="module")
def patterns():
    return MigrationIntelligence().pattern_database


def test_l394_fixture_drift_pattern_in_database(patterns):
    """L394: pattern_database should include a 'fleet-canonical-fixture drift' pattern."""
    titles = [p.get("title", "").lower() for p in patterns]
    descriptions = [p.get("description", "").lower() for p in patterns]
    assert any(
        "fixture" in t and "drift" in t for t in titles
    ) or any(
        "fixture" in d and "drift" in d for d in descriptions
    ), f"L394 fixture-drift radar flag not in pattern_database; titles: {titles}"


def test_l394_symbol_collision_pattern_in_database(patterns):
    """L394: pattern_database should include a 'cross-app symbol collision' pattern."""
    titles = [p.get("title", "").lower() for p in patterns]
    descriptions = [p.get("description", "").lower() for p in patterns]
    assert any(
        "symbol" in t and "collision" in t for t in titles
    ) or any(
        "symbol" in d and "collision" in d for d in descriptions
    ), f"L394 symbol-collision radar flag not in pattern_database; titles: {titles}"


def test_l394_radar_flags_have_severity_levels(patterns):
    """Each radar flag must declare a severity level (per L380 4-layer pattern)."""
    radar = [
        p for p in patterns
        if "drift" in p.get("title", "").lower() or "collision" in p.get("title", "").lower()
    ]
    assert len(radar) >= 2, (
        f"expected at least 2 radar patterns (fixture-drift + symbol-collision); "
        f"found {len(radar)}; titles: {[p.get('title') for p in patterns]}"
    )
    for p in radar:
        assert "severity" in p, f"radar pattern {p.get('title')} missing severity"
        assert p["severity"] in VALID_SEVERITIES, (
            f"radar pattern {p.get('title')} has invalid severity: {p['severity']}"
        )


# ---- W2 (e): full re-export coverage ----

def test_pattern_database_has_at_least_nine_patterns(patterns):
    """W2(e) goal: re-export brings pattern_database from 3 to >= 9 patterns."""
    assert len(patterns) >= 9, (
        f"expected >= 9 patterns after W2(e) re-export; found {len(patterns)}"
    )


def test_all_patterns_have_required_keys(patterns):
    """Every pattern carries the envelope-shaped keys the radar layer consumes."""
    for p in patterns:
        for key in ("id", "title", "description", "severity"):
            assert key in p and p[key], f"pattern {p.get('id')} missing/empty {key}"
        assert p["severity"] in VALID_SEVERITIES, (
            f"pattern {p['id']} has invalid severity: {p['severity']}"
        )


def test_pattern_ids_are_unique(patterns):
    ids = [p["id"] for p in patterns]
    assert len(ids) == len(set(ids)), f"duplicate pattern ids: {ids}"


@pytest.mark.parametrize("pattern_id", sorted(EXPECTED_PATTERNS.keys()))
def test_expected_pattern_present(patterns, pattern_id):
    """Each re-exported pattern id must be present in the database."""
    ids = {p["id"] for p in patterns}
    assert pattern_id in ids, f"expected pattern '{pattern_id}' missing; have {sorted(ids)}"


@pytest.mark.parametrize("pattern_id,sample", sorted(EXPECTED_PATTERNS.items()))
def test_pattern_detect_matches_positive_sample(patterns, pattern_id, sample):
    """Each pattern's detect(content) callable flags its positive sample True."""
    by_id = {p["id"]: p for p in patterns}
    p = by_id[pattern_id]
    detect = p.get("detect")
    assert callable(detect), f"pattern {pattern_id} has no detect() callable"
    assert detect(sample) is True, (
        f"pattern {pattern_id} detect() failed to match positive sample: {sample!r}"
    )
    # Detector should not fire on clearly-unrelated empty content.
    assert detect("") is False, f"pattern {pattern_id} detect() fired on empty content"


def test_severity_for_risk_mapping():
    """L380 risk->severity mapping boundaries."""
    assert severity_for_risk(0.95) == "critical"
    assert severity_for_risk(0.90) == "critical"
    assert severity_for_risk(0.8) == "high"
    assert severity_for_risk(0.70) == "high"
    assert severity_for_risk(0.55) == "warn"
    assert severity_for_risk(0.40) == "warn"
    assert severity_for_risk(0.39) == "info"
