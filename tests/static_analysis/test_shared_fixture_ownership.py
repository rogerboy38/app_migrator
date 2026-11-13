"""Check: shared-fixture-ownership — the reference implementation's tests.

These tests reproduce the two defects the 2026-11-05 audits actually found:

- ``rnd_warehouse_management`` ships **63 of 64** Custom Fields and **all 21**
  Property Setters identically to ``amb_w_spc`` (audit F6).
- ``amb_w_tds`` ships ``Item-substrate`` (also ``amb_w_spc``) and
  ``Item-custom_is_sub_batch`` (also ``rnd_warehouse_management``) (audit F5).

The checks are bench-free: these tests run with no Frappe and no ``bench``
CLI, which is the point of placing them outside ``app_migrator/commands/``.
"""
from __future__ import annotations

from conftest import FakeApp, finding_ids, run_check

CHECK_ID = "shared-fixture-ownership"


def _cf(dt: str, fieldname: str, **extra):
    record = {"dt": dt, "fieldname": fieldname, "fieldtype": "Data"}
    record.update(extra)
    return record


def _ps(doc_type: str, field_name: str, prop: str, value: str):
    return {
        "doc_type": doc_type,
        "field_name": field_name,
        "property": prop,
        "value": value,
    }


def test_identical_custom_field_is_reported_as_medium(apps_root, inventory):
    """Two apps shipping the same Custom Field is a latent trap: medium."""
    root = apps_root([
        FakeApp(
            name="app_a",
            custom_fields=[_cf("Item", "substrate", modified="2026-01-01 00:00:00")],
        ),
        FakeApp(
            name="app_b",
            custom_fields=[_cf("Item", "substrate", modified="2026-11-01 00:00:00")],
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "medium", finding.severity
    assert "app_a" in finding.evidence["owning_apps"]
    assert "app_b" in finding.evidence["owning_apps"]
    assert finding.evidence["identical"] is True
    # The id must be stable so two runs can be diffed.
    assert finding.id == "integrity-shared-fixture-ownership-custom-fields-Item-substrate"


def test_divergent_custom_field_is_escalated_to_high(apps_root, inventory):
    """Once the copies differ, migrate order decides the surviving definition."""
    root = apps_root([
        FakeApp(name="app_a", custom_fields=[_cf("Item", "substrate", options="A\nB")]),
        FakeApp(name="app_b", custom_fields=[_cf("Item", "substrate", options="A\nC")]),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    assert result.findings[0].severity == "high"
    assert result.findings[0].evidence["identical"] is False


def test_timestamp_differences_alone_are_not_divergence(apps_root, inventory):
    """Fixture exports carry different timestamps; that is not a real divergence."""
    root = apps_root([
        FakeApp(name="app_a", custom_fields=[_cf("Item", "substrate", modified="2026-01-01")]),
        FakeApp(name="app_b", custom_fields=[_cf("Item", "substrate", modified="2026-12-31")]),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings[0].evidence["identical"] is True


def test_property_setter_shared_by_two_apps_is_reported(apps_root, inventory):
    """Property Setters are the other half of the fixture-ownership problem."""
    root = apps_root([
        FakeApp(name="app_a", property_setters=[_ps("Item", "substrate", "reqd", "0")]),
        FakeApp(name="app_b", property_setters=[_ps("Item", "substrate", "reqd", "0")]),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    assert result.findings[0].severity == "medium"
    assert "property-setters" in result.findings[0].id


def test_unique_records_are_not_reported(apps_root, inventory):
    """The common case must stay clean — a noisy check is a check nobody runs."""
    root = apps_root([
        FakeApp(name="app_a", custom_fields=[_cf("Item", "only_a")]),
        FakeApp(name="app_b", custom_fields=[_cf("Item", "only_b")]),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == []
    assert result.stats["custom_fields_shared"] == 0


def test_single_app_ships_nothing_shared(apps_root, inventory):
    """One app alone cannot have an ownership conflict."""
    root = apps_root([
        FakeApp(name="app_a", custom_fields=[_cf("Item", "substrate")]),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == []


def test_three_owners_are_all_listed(apps_root, inventory):
    """Every owning app must be named — 'two apps' is what the audits found, but
    the check must not cap at two."""
    root = apps_root([
        FakeApp(name="app_a", custom_fields=[_cf("Item", "substrate")]),
        FakeApp(name="app_b", custom_fields=[_cf("Item", "substrate")]),
        FakeApp(name="app_c", custom_fields=[_cf("Item", "substrate")]),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    assert result.findings[0].evidence["owning_apps"] == ["app_a", "app_b", "app_c"]


def test_finding_is_stable_across_runs(apps_root, inventory):
    """Stable ids are the diff key an agent uses; they must not drift."""
    root = apps_root([
        FakeApp(name="app_a", custom_fields=[_cf("Item", "substrate")]),
        FakeApp(name="app_b", custom_fields=[_cf("Item", "substrate")]),
    ])
    first = finding_ids(run_check(CHECK_ID, inventory(root)))
    second = finding_ids(run_check(CHECK_ID, inventory(root)))
    assert first == second
