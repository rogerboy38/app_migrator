"""Check: select-option-drift — a stored value the field's options no longer allow.

These tests reproduce the defect the 2026-11-05 audits found: changing the
options of a Select field can make already-submitted documents un-editable,
because Frappe validates the stored value against the *current* options on
every non-cancel save. One audited case would have made **42 submitted Stock
Entries un-editable**.

The comparison core is bench-free: these tests run with no Frappe and no
``bench`` CLI, which is the point of placing it in
``app_migrator/_integrity/select_option_drift.py`` (outside ``commands/`` and
outside the auto-discovered ``checks/`` registry).
"""
from __future__ import annotations

import re
from app_migrator._integrity.select_option_drift import (
    CHECK_ID,
    build_findings,
    compare_select_options,
    scan_select_options,
)
from pathlib import Path

STOCK_ENTRY = "Stock Entry"


def _record(**overrides):
    """One (DocType, field) record as the site layer produces it."""
    record = {
        "doctype": STOCK_ENTRY,
        "fieldname": "purpose",
        "fieldtype": "Select",
        "options": ["Material Transfer", "Manufacturing"],
        "stored_values": [],
        "doctype_count": 0,
        "app": "amb_w_tds",
    }
    record.update(overrides)
    return record


def _ids(findings):
    """The finding ids, in order."""
    return [f.id for f in findings]


# --------------------------------------------------------------------------
# The comparison itself
# --------------------------------------------------------------------------
def test_stored_value_outside_the_options_is_high_when_the_doctype_has_rows():
    """A drifted value on a doctype with rows is what breaks a save: high."""
    result = compare_select_options([
        _record(stored_values=["Material Transfer", "Recount"], doctype_count=42),
    ])
    assert len(result["drift"]) == 1, result
    entry = result["drift"][0]
    assert entry["severity"] == "high", entry["severity"]
    # Only the offending value is reported, not the legal ones.
    assert entry["stored_values"] == ["Recount"], entry["stored_values"]
    assert entry["doctype"] == STOCK_ENTRY
    assert entry["fieldname"] == "purpose"
    assert entry["options"] == ["Material Transfer", "Manufacturing"]
    assert entry["doctype_count"] == 42
    assert entry["app"] == "amb_w_tds"
    assert result["_stats"]["drift_count"] == 1
    assert result["_stats"]["high_count"] == 1


def test_stored_value_outside_the_options_is_medium_when_the_doctype_is_empty():
    """Nothing to break yet, but the drift is latent: medium."""
    result = compare_select_options([
        _record(stored_values=["Recount"], doctype_count=0),
    ])
    assert len(result["drift"]) == 1, result
    assert result["drift"][0]["severity"] == "medium", result["drift"][0]["severity"]
    assert result["_stats"]["medium_count"] == 1
    assert result["_stats"]["high_count"] == 0


def test_stored_value_inside_the_options_is_not_reported():
    """The common case must stay clean — a noisy check is a check nobody runs."""
    result = compare_select_options([
        _record(stored_values=["Material Transfer", "Manufacturing"], doctype_count=42),
    ])
    assert result["drift"] == []
    assert result["_stats"]["drift_count"] == 0


def test_empty_options_list_is_skipped():
    """A Select with no options constrains nothing — every value is legal."""
    result = compare_select_options([
        _record(options=[], stored_values=["Recount"], doctype_count=42),
    ])
    assert result["drift"] == []
    assert result["_stats"]["fields_unconstrained"] == 1
    assert result["_stats"]["fields_scanned"] == 1


def test_whitespace_trimmed_match_is_not_reported():
    """Frappe stores what it was given; surrounding spaces are not a drift."""
    result = compare_select_options([
        _record(options=[" Material Transfer "], stored_values=["Material Transfer"],
                doctype_count=42),
    ])
    assert result["drift"] == []


def test_comparison_is_case_sensitive():
    """Frappe's own validation is case-sensitive, so 'ready' is not 'Ready'."""
    result = compare_select_options([
        _record(options=["Ready"], stored_values=["ready"], doctype_count=1),
    ])
    assert len(result["drift"]) == 1, result
    assert result["drift"][0]["stored_values"] == ["ready"]


def test_blank_stored_values_are_not_drift():
    """An unset Select is not 'outside the options'."""
    result = compare_select_options([
        _record(stored_values=["", "   ", None], doctype_count=3),
    ])
    assert result["drift"] == []
    assert result["_stats"]["blank_values_skipped"] == 3


# --------------------------------------------------------------------------
# The findings
# --------------------------------------------------------------------------
def test_finding_ids_are_stable():
    """Stable ids are the diff key an agent uses; they must not drift."""
    records = [_record(stored_values=["Recount"], doctype_count=42)]
    first = _ids(build_findings(compare_select_options(records)["drift"]))
    second = _ids(build_findings(compare_select_options(records)["drift"]))
    assert first == second
    assert first == ["integrity-select-option-drift-stock-entry-purpose"]


def test_finding_ids_slugify_the_doctype_and_keep_the_fieldname():
    """The doctype is slugified; the fieldname stays the literal column name."""
    records = [_record(doctype="Sales Invoice", fieldname="po_type",
                       stored_values=["Recount"], doctype_count=1)]
    findings = build_findings(compare_select_options(records)["drift"])
    assert _ids(findings) == ["integrity-select-option-drift-sales-invoice-po_type"]


def test_findings_are_ordered_worst_first():
    """A high finding must come before a medium one, whatever the input order."""
    drift = compare_select_options([
        _record(fieldname="empty_field", stored_values=["Recount"], doctype_count=0),
        _record(fieldname="busy_field", stored_values=["Recount"], doctype_count=42),
    ])["drift"]
    findings = build_findings(drift)
    assert [f.severity for f in findings] == ["high", "medium"]
    assert findings[0].evidence["doctype_count"] == 42
    assert findings[0].evidence["stored_values"] == ["Recount"]


def test_finding_limit_truncates_the_finding_list():
    """The envelope carries a bounded list; the true count stays in the stats."""
    records = [
        _record(fieldname=f"field_{index}", stored_values=["Recount"], doctype_count=5)
        for index in range(5)
    ]
    drift = compare_select_options(records)["drift"]
    assert len(drift) == 5
    findings = build_findings(drift, limit=2)
    assert len(findings) == 2
    assert _ids(findings) == [
        "integrity-select-option-drift-stock-entry-field_0",
        "integrity-select-option-drift-stock-entry-field_1",
    ]
    assert compare_select_options(records)["_stats"]["drift_count"] == 5


# --------------------------------------------------------------------------
# The scan (collector injected, no database in this layer)
# --------------------------------------------------------------------------
class _FakeCollector:
    """Answers the collector protocol from dicts instead of a live site."""

    def __init__(self, doctypes=(), fields=None, stored=None, options=None, counts=None):
        self._doctypes = list(doctypes)
        self._fields = fields or {}
        self._stored = stored or {}
        self._options = options or {}
        self._counts = counts or {}

    def doctypes(self):
        return list(self._doctypes)

    def fields(self, doctype):
        return list(self._fields.get(doctype, []))

    def stored_values(self, doctype, fieldname):
        return list(self._stored.get((doctype, fieldname), []))

    def options(self, doctype, fieldname):
        return list(self._options.get((doctype, fieldname), []))

    def row_count(self, doctype):
        return int(self._counts.get(doctype, 0))


class _FakeInventory:
    """Just enough of the inventory to attribute a doctype to an app."""

    def __init__(self, shipped=None):
        self._shipped = shipped or {}

    def all_shipped_doctypes(self):
        return dict(self._shipped)


def _collector():
    return _FakeCollector(
        doctypes=[STOCK_ENTRY],
        fields={STOCK_ENTRY: [
            {"fieldname": "purpose", "fieldtype": "Select"},
            {"fieldname": "remarks", "fieldtype": "Data"},
        ]},
        stored={(STOCK_ENTRY, "purpose"): ["Material Transfer", "Recount"]},
        options={(STOCK_ENTRY, "purpose"): ["Material Transfer"]},
        counts={STOCK_ENTRY: 42},
    )


def test_scan_reads_the_site_only_through_the_injected_collector():
    """The scan must not touch the database itself."""
    inventory = _FakeInventory({STOCK_ENTRY: {"amb_w_tds"}})
    records = scan_select_options(inventory, _collector())
    assert len(records) == 1, records
    record = records[0]
    assert record["doctype"] == STOCK_ENTRY
    assert record["fieldname"] == "purpose"
    assert record["fieldtype"] == "Select"
    assert record["options"] == ["Material Transfer"]
    assert record["stored_values"] == ["Material Transfer", "Recount"]
    assert record["doctype_count"] == 42
    assert record["app"] == "amb_w_tds"


def test_scan_ignores_fields_that_are_not_constrained():
    """A Data field has no options, so it can never drift."""
    records = scan_select_options(_FakeInventory(), _collector())
    assert [r["fieldname"] for r in records] == ["purpose"]


def test_scan_honours_the_doctype_and_field_filters():
    inventory = _FakeInventory({STOCK_ENTRY: {"amb_w_tds"}})
    assert scan_select_options(inventory, _collector(), doctype_filter="Item") == []
    assert scan_select_options(inventory, _collector(), field_filter="remarks") == []
    assert len(scan_select_options(inventory, _collector(), field_filter="purpose")) == 1


def test_scanned_records_drive_the_comparison():
    """The scan output is the comparison input — the two layers compose."""
    records = scan_select_options(_FakeInventory({STOCK_ENTRY: {"amb_w_tds"}}), _collector())
    result = compare_select_options(records)
    assert len(result["drift"]) == 1, result
    assert result["drift"][0]["severity"] == "high"
    assert result["drift"][0]["stored_values"] == ["Recount"]
    assert result["_stats"]["doctypes_scanned"] == 1
    assert result["_stats"]["fields_scanned"] == 1


# --------------------------------------------------------------------------
# The hard constraint: the core is importable with no Frappe installed
# --------------------------------------------------------------------------
def test_the_core_never_imports_frappe():
    """The package must stay importable without a bench."""
    import app_migrator._integrity.select_option_drift as module

    source = Path(module.__file__).read_text(encoding="utf-8")
    assert not re.search(r"^\s*import\s+frappe\b", source, re.M)
    assert not re.search(r"^\s*from\s+frappe\b", source, re.M)


def test_the_core_lives_outside_the_auto_discovered_check_registry():
    """A check under ``checks/`` is registered automatically — this one is not."""
    from app_migrator._integrity.checks import CHECKS

    assert CHECK_ID not in [spec.check_id for spec in CHECKS]
