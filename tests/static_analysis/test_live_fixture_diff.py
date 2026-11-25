"""Tests for the pure helpers of scripts/live_fixture_diff.py.

The script is loaded by path and its frappe import is optional, so the
comparison logic can be checked offline - the site-dependent parts need a
bench.  This is what stops the live half from being "written but never run".
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "live_fixture_diff.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("live_fixture_diff_under_test", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["live_fixture_diff_under_test"] = module
    spec.loader.exec_module(module)
    return module


lfd = _load()


def test_normalise_compares_across_json_types():
    assert lfd.normalise(1) == "1"
    assert lfd.normalise("1") == "1"
    assert lfd.normalise(1.0) == "1.0"
    assert lfd.normalise(None) == ""
    assert lfd.normalise("  x ") == "x"
    assert lfd.normalise(True) == "1"
    assert lfd.normalise(False) == "0"


def test_normalise_compares_lists_by_content():
    assert lfd.normalise(["a", "b"]) == lfd.normalise(["a", "b"])
    assert lfd.normalise(["a", "b"]) != lfd.normalise(["b", "a"])


def test_read_records_handles_the_three_shapes(tmp_path):
    (tmp_path / "a_list.json").write_text(
        json.dumps([{"doctype": "Role", "name": "r1"}]), encoding="utf-8"
    )
    (tmp_path / "b_by_doctype.json").write_text(
        json.dumps({"Role": [{"doctype": "Role", "name": "r2"}]}), encoding="utf-8"
    )
    (tmp_path / "c_single_record.json").write_text(
        json.dumps({"doctype": "Print Format", "name": "pf", "html": "<p>x</p>"}),
        encoding="utf-8",
    )

    found = lfd.read_records(str(tmp_path))
    names = sorted(rec["name"] for _f, rec in found)
    assert names == ["pf", "r1", "r2"]


def test_read_records_skips_unreadable_files(tmp_path, capsys):
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    (tmp_path / "ok.json").write_text(
        json.dumps([{"doctype": "Role", "name": "r"}]), encoding="utf-8"
    )
    found = lfd.read_records(str(tmp_path))
    assert len(found) == 1
    assert "unreadable" in capsys.readouterr().out


def test_controller_refusals_finds_a_throw_in_submit():
    source = (
        "class Doc:\n"
        "    def submit(self):\n"
        "        frappe.throw('not allowed')\n"
    )
    hits = lfd.controller_refusals(source, "submit")
    assert len(hits) == 1
    assert "not allowed" in hits[0]


def test_controller_refusals_ignores_other_methods():
    source = (
        "class Doc:\n"
        "    def validate(self):\n"
        "        frappe.throw('nope')\n"
        "    def submit(self):\n"
        "        self.save()\n"
    )
    assert lfd.controller_refusals(source, "submit") == []
    assert len(lfd.controller_refusals(source, "validate")) == 1


def test_controller_refusals_handles_no_source():
    assert lfd.controller_refusals(None, "submit") == []
    assert lfd.controller_refusals("not python((", "submit") == []


def test_scrub_matches_frappe():
    assert lfd.scrub("COA AMB2") == "coa_amb2"
    assert lfd.scrub("Sales Invoice") == "sales_invoice"


def test_skip_fields_exclude_identity_and_bookkeeping():
    for field in ("doctype", "name", "modified", "owner", "idx"):
        assert field in lfd.SKIP_FIELDS


def test_metadata_flags_are_not_value_fields():
    assert "is_system_generated" in lfd.METADATA_FLAGS
    assert "is_system_generated" not in lfd.SKIP_FIELDS


def test_right_to_method_maps_delete_to_on_trash():
    assert lfd.RIGHT_TO_METHOD["delete"] == "on_trash"
    assert lfd.RIGHT_TO_METHOD["submit"] == "submit"


def test_importing_the_script_does_not_run_the_report_even_with_a_frappe_stub():
    """Importing must never run the report - not even with a frappe present.

    This is a regression test for a real CI failure.  The bench-free suite
    installs a permissive `frappe` stand-in whose `get_installed_apps()`
    returns a stub object rather than a list, so a script that ran its
    report on import died during pytest collection with

        TypeError: 'stub_get_installed_apps' object is not iterable

    The report runs on `__main__` only, which is what the bench console and
    `python3 live_fixture_diff.py` both are.
    """
    import _frappe_stub

    _frappe_stub.install()

    spec = importlib.util.spec_from_file_location(
        "live_fixture_diff_imported_with_stub", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["live_fixture_diff_imported_with_stub"] = module
    # The import itself is the assertion: it must not raise, which is what
    # happens if the report runs and tries to read a site.
    spec.loader.exec_module(module)

    assert module.frappe is not None, "the frappe stand-in should be importable here"
