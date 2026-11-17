"""Tests for the static fixture audit (app_migrator._integrity.fixture_audit).

The module is loaded by path rather than imported through the package,
because `app_migrator._integrity.__init__` pulls in context.py, which uses
PEP 758 syntax (except A, B:) that only Python 3.14 can parse.  The
project floor is 3.14; this test still runs on 3.11 so it can be checked
offline.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "app_migrator"
    / "_integrity"
    / "fixture_audit.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("fixture_audit_under_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["fixture_audit_under_test"] = module
    spec.loader.exec_module(module)
    return module


fa = _load()


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _make_app(apps_root: Path, name: str) -> Path:
    app = apps_root / name
    app.mkdir(parents=True, exist_ok=True)
    (app / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    return app


def test_app_names_needs_an_app_marker(tmp_path):
    apps = tmp_path / "apps"
    apps.mkdir()
    _make_app(apps, "real_app")
    (apps / "not_an_app").mkdir()
    (apps / "not_an_app" / "assets").mkdir()

    assert fa.app_names(apps) == ["real_app"]


def test_app_level_fixture_records_are_always_rewritten(tmp_path):
    apps = tmp_path / "apps"
    app = _make_app(apps, "demo")
    _write(
        app / "demo" / "fixtures" / "property_setter.json",
        [{"doctype": "Property Setter", "name": "ps-1", "value": "1"}],
    )

    report = fa.audit_apps_root(apps)
    ids = {f["id"] for f in report["findings"]}
    assert "FX-REIMPORTED-APP-FIXTURE" in ids

    rewritten = list(fa.iter_never_modified(report))
    assert rewritten == [("demo", str(app / "demo" / "fixtures" / "property_setter.json"), "ps-1")]


def test_modified_does_not_protect_an_app_level_fixture(tmp_path):
    """force=True bypasses the timestamp skip, so a `modified` key changes nothing."""
    apps = tmp_path / "apps"
    app = _make_app(apps, "demo")
    _write(
        app / "demo" / "fixtures" / "notification.json",
        [{"doctype": "Notification", "name": "n1", "modified": "2020-01-01 00:00:00"}],
    )

    report = fa.audit_apps_root(apps)
    assert len(list(fa.iter_never_modified(report))) == 1


def test_doc_file_without_modified_is_rewritten(tmp_path):
    apps = tmp_path / "apps"
    app = _make_app(apps, "demo")
    _write(
        app / "demo" / "print_format" / "my_pf" / "my_pf.json",
        {"doctype": "Print Format", "name": "My PF", "html": "<p>x</p>"},
    )

    report = fa.audit_apps_root(apps)
    ids = {f["id"] for f in report["findings"]}
    assert "FX-NO-MODIFIED-DOCFILE" in ids
    assert len(list(fa.iter_never_modified(report))) == 1


def test_doc_file_with_modified_is_left_alone(tmp_path):
    apps = tmp_path / "apps"
    app = _make_app(apps, "demo")
    _write(
        app / "demo" / "print_format" / "my_pf" / "my_pf.json",
        {
            "doctype": "Print Format",
            "name": "My PF",
            "html": "<p>x</p>",
            "modified": "2020-01-01 00:00:00",
        },
    )

    report = fa.audit_apps_root(apps)
    assert "FX-NO-MODIFIED-DOCFILE" not in {f["id"] for f in report["findings"]}
    assert list(fa.iter_never_modified(report)) == []


def test_empty_body_is_reported(tmp_path):
    apps = tmp_path / "apps"
    app = _make_app(apps, "demo")
    _write(
        app / "demo" / "fixtures" / "print_format.json",
        [{"doctype": "Print Format", "name": "pf", "html": ""}],
    )

    report = fa.audit_apps_root(apps)
    empty = [f for f in report["findings"] if f["id"] == "FX-EMPTY-BODY"]
    assert len(empty) == 1
    assert empty[0]["field"] == "html"


def test_custom_docperm_is_reported_as_a_whole_set_replace(tmp_path):
    apps = tmp_path / "apps"
    app = _make_app(apps, "demo")
    _write(
        app / "demo" / "custom" / "custom_docperm.json",
        [{"doctype": "Custom DocPerm", "parent": "Item", "role": "x"}],
    )

    report = fa.audit_apps_root(apps)
    ids = {f["id"] for f in report["findings"]}
    assert "FX-DOCPERM-WHOLE-SET-REPLACED" in ids


def test_multiple_fixture_folders_are_flagged(tmp_path):
    apps = tmp_path / "apps"
    app = _make_app(apps, "demo")
    _write(app / "demo" / "fixtures" / "role.json", [{"doctype": "Role", "name": "r"}])
    _write(
        app / "demo" / "sub_module" / "fixtures" / "role.json",
        [{"doctype": "Role", "name": "r2"}],
    )

    report = fa.audit_apps_root(apps)
    assert "FX-MULTIPLE-FIXTURE-FOLDERS" in {f["id"] for f in report["findings"]}


def test_scrub_matches_frappe():
    assert fa._scrub("Sales Invoice") == "sales_invoice"
    assert fa._scrub("Print Format") == "print_format"
    assert fa._scrub("COA AMB2") == "coa_amb2"


def test_discover_apps_root_finds_the_apps_dir(tmp_path):
    bench = tmp_path / "frappe-bench"
    (bench / "apps").mkdir(parents=True)
    _make_app(bench / "apps", "demo")
    assert fa.discover_apps_root(bench) == (bench / "apps").resolve()
    assert fa.discover_apps_root(tmp_path / "nowhere") is None


def test_a_single_record_dict_reads_as_one_record(tmp_path):
    """A doc-file is ONE record as a dict; reading its values reads nothing."""
    path = tmp_path / "one.json"
    path.write_text(
        json.dumps({"doctype": "Print Format", "name": "My PF", "html": "<p>x</p>"}),
        encoding="utf-8",
    )
    records = fa._read_json(path)
    assert len(records) == 1
    assert records[0]["name"] == "My PF"
