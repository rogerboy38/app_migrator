"""Check: undeclared-app-dependency — the tests.

These tests reproduce the defect the 2026-11-05 audit of ``amb_w_tds`` found:
the app declares **no** ``required_apps`` at all, yet 13 Link / Table fields
point at four DocTypes that exist only in ``amb_w_spc``
(``Batch AMB`` x8, ``Parameter Group Substrate`` x2,
``SPC Batch Parameter`` x2, ``SPC Specification`` x1).

The checks are bench-free: these tests run with no Frappe and no ``bench``
CLI, which is the point of placing them outside ``app_migrator/commands/``.
"""
from __future__ import annotations

import json
import os
from typing import List, Tuple

from conftest import FakeApp, finding_ids, run_check

CHECK_ID = "undeclared-app-dependency"

# (fieldname, fieldtype, options)
Field = Tuple[str, str, str]


def _write_doctype(root: str, app: str, doctype: str, fields: List[Field]) -> None:
    """Write a DocType JSON that carries real fieldtypes.

    The shared ``FakeApp`` builder only emits ``Data`` fields; the check
    under test is about ``Link`` / ``Table`` fields, so the schema of the
    DocTypes that carry them is written here.
    """
    slug = doctype.lower().replace(" ", "_").replace("-", "_")
    dt_dir = os.path.join(root, app, app, "doctype", slug)
    os.makedirs(dt_dir, exist_ok=True)
    payload = {
        "name": doctype,
        "fields": [
            {"fieldname": fieldname, "fieldtype": fieldtype, "options": options}
            for fieldname, fieldtype, options in fields
        ],
    }
    with open(os.path.join(dt_dir, f"{slug}.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def _link(doctype: str, fieldname: str) -> Field:
    return (fieldname, "Link", doctype)


def _table(doctype: str, fieldname: str) -> Field:
    return (fieldname, "Table", doctype)


def test_link_to_another_apps_doctype_is_reported_as_medium(apps_root, inventory):
    """The audited case: no required_apps, yet links into another app."""
    root = apps_root([
        FakeApp(name="amb_w_spc", doctypes={"Batch AMB": ["name"]}),
        FakeApp(name="amb_w_tds"),
    ])
    _write_doctype(root, "amb_w_tds", "TDS Batch", [
        _link("Batch AMB", "batch_amb_ref"),
        _link("Batch AMB", "batch_amb_ref_2"),
    ])
    result = run_check(CHECK_ID, inventory(root))
    # One finding per (app, target) pair — not one per field.
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "medium", finding.severity
    assert finding.app == "amb_w_tds"
    assert finding.evidence["doctype"] == "Batch AMB"
    assert finding.evidence["owner_app"] == "amb_w_spc"
    assert finding.evidence["required_apps"] == []
    assert len(finding.evidence["targets"]) == 2
    assert finding.evidence["fieldname"] == "batch_amb_ref"
    assert finding.evidence["fieldtype"] == "Link"
    # The id must be stable so two runs can be diffed.
    assert finding.id == "integrity-undeclared-app-dependency-amb_w_tds-batch-amb"


def test_link_to_a_doctype_nobody_ships_is_high(apps_root, inventory):
    """A target no installed app ships can never resolve: high."""
    root = apps_root([
        FakeApp(name="amb_w_tds"),
    ])
    _write_doctype(root, "amb_w_tds", "TDS Batch", [
        _link("SPC Batch Parameter", "spc_batch_parameter"),
        _table("SPC Specification", "spec_rows"),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 2, finding_ids(result)
    severities = {f.evidence["doctype"]: f.severity for f in result.findings}
    assert severities == {
        "SPC Batch Parameter": "high",
        "SPC Specification": "high",
    }
    finding = result.findings[0]
    assert finding.evidence["owner_apps"] == []
    assert finding.evidence["targets"][0]["doctype"] == "TDS Batch"


def test_declared_dependency_is_not_reported(apps_root, inventory):
    """The clean case: the dependency is declared, so nothing to report."""
    root = apps_root([
        FakeApp(name="amb_w_spc", doctypes={"Batch AMB": ["name"]}),
        FakeApp(name="amb_w_tds", hooks='required_apps = ["amb_w_spc"]\n'),
    ])
    _write_doctype(root, "amb_w_tds", "TDS Batch", [
        _link("Batch AMB", "batch_amb_ref"),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)
    assert result.stats["undeclared_targets"] == 0


def test_doctype_shipped_by_the_app_itself_is_ignored(apps_root, inventory):
    """Linking to your own DocType is normal — it must stay quiet."""
    root = apps_root([
        FakeApp(name="amb_w_tds", doctypes={"TDS Batch": ["name"]}),
    ])
    _write_doctype(root, "amb_w_tds", "TDS Batch", [
        _link("TDS Batch", "parent_batch"),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)


def test_target_is_matched_case_insensitively(apps_root, inventory):
    """MariaDB's default collation is case-insensitive, so we match that way.

    ``Batch AMB`` and ``batch amb`` are the same DocType on a real site: the
    target resolves, so the finding is 'undeclared', not 'nobody ships it'.
    """
    root = apps_root([
        FakeApp(name="amb_w_spc", doctypes={"Batch AMB": ["name"]}),
        FakeApp(name="amb_w_tds"),
    ])
    _write_doctype(root, "amb_w_tds", "TDS Batch", [
        _link("batch amb", "batch_amb_ref"),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "medium", finding.severity
    assert finding.evidence["owner_app"] == "amb_w_spc"


def test_required_apps_built_at_runtime_is_not_judged(apps_root, inventory):
    """A ``required_apps`` computed at runtime cannot be judged statically."""
    root = apps_root([
        FakeApp(name="amb_w_spc", doctypes={"Batch AMB": ["name"]}),
        FakeApp(name="amb_w_tds", hooks="required_apps = compute_required_apps()\n"),
    ])
    _write_doctype(root, "amb_w_tds", "TDS Batch", [
        _link("Batch AMB", "batch_amb_ref"),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)
    assert result.stats["dynamic_required_apps"] == 1


def test_stats_report_what_was_scanned(apps_root, inventory):
    """The stats block says how much was looked at, not just what was found."""
    root = apps_root([
        FakeApp(name="amb_w_spc", doctypes={"Batch AMB": ["name"]}),
        FakeApp(name="amb_w_tds"),
    ])
    _write_doctype(root, "amb_w_tds", "TDS Batch", [
        _link("Batch AMB", "batch_amb_ref"),
        _link("Batch AMB", "batch_amb_ref_2"),
        _link("Nowhere DocType", "ghost_ref"),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.stats["apps_scanned"] == 2
    assert result.stats["link_fields_scanned"] == 3
    assert result.stats["unresolved_targets"] == 1
    assert result.stats["undeclared_targets"] == 1


def test_finding_ids_are_stable_across_runs(apps_root, inventory):
    """Stable ids are the diff key an agent uses; they must not drift."""
    root = apps_root([
        FakeApp(name="amb_w_spc", doctypes={"Batch AMB": ["name"]}),
        FakeApp(name="amb_w_tds"),
    ])
    _write_doctype(root, "amb_w_tds", "TDS Batch", [
        _link("Batch AMB", "batch_amb_ref"),
    ])
    first = finding_ids(run_check(CHECK_ID, inventory(root)))
    second = finding_ids(run_check(CHECK_ID, inventory(root)))
    assert first == second
    assert first == ["integrity-undeclared-app-dependency-amb_w_tds-batch-amb"]
