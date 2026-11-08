"""W3 finding #3 — generate-plan <-> execute plan-schema round-trip contract.

The canonical pipeline is `generate-plan --output p.json` then
`execute --dry-run --plan p.json`. Before this fix `execute` assumed a flat
`plan['doctypes']` list and raised `KeyError: 'doctypes'` on the phased schema
that `generate-plan` actually emits.

These tests exercise the `_extract_doctypes` shim in-process (no `bench`
subprocess, so they never hang on this substrate — the full CLI round-trip is
covered by T-VERIFY-005 in a fresh venv).
"""
from app_migrator.commands.execute import _extract_doctypes


def test_phased_schema_does_not_keyerror():
    """The generate-plan 'intelligent phased' schema must extract without KeyError."""
    plan = {
        "version": "10.0.0-rc1-intelligent",
        "source_apps": ["payments"],
        "target_app": "erpnext",
        "phases": [
            {"name": "Phase 1 - Foundation", "doctypes": ["Payment Gateway"], "count": 1},
            {"name": "Phase 2 - Dependent", "doctypes": [], "count": 0},
            {"name": "Phase 3 - Complex", "doctypes": [], "count": 0},
        ],
    }
    out = _extract_doctypes(plan)
    assert out == [{"name": "Payment Gateway", "target_app": "erpnext"}]


def test_legacy_flat_schema_still_works():
    """The legacy flat schema must keep working (backward compat)."""
    plan = {"doctypes": [
        {"name": "Payment Gateway", "target_app": "erpnext"},
        {"name": "Payment Log", "target_app": "erpnext"},
    ]}
    out = _extract_doctypes(plan)
    assert out == [
        {"name": "Payment Gateway", "target_app": "erpnext"},
        {"name": "Payment Log", "target_app": "erpnext"},
    ]


def test_flat_schema_string_entries_inherit_target():
    """Flat schema with bare string entries inherits plan-level target_app."""
    plan = {"target_app": "erpnext", "doctypes": ["Payment Gateway"]}
    assert _extract_doctypes(plan) == [{"name": "Payment Gateway", "target_app": "erpnext"}]


def test_empty_plan_returns_empty_not_keyerror():
    """A plan with neither 'doctypes' nor 'phases' returns [] rather than raising."""
    assert _extract_doctypes({}) == []
    assert _extract_doctypes({"phases": []}) == []


def test_every_extracted_doctype_has_execute_required_keys():
    """execute reads dt['name'] and dt['target_app']; both must always be present."""
    plan = {
        "target_app": "erpnext",
        "phases": [{"name": "P1", "doctypes": ["A", "B"], "count": 2}],
    }
    for dt in _extract_doctypes(plan):
        assert "name" in dt and "target_app" in dt
