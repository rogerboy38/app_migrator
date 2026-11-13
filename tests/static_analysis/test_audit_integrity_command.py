"""Check: the ``audit-integrity`` command layer — the tests.

The 2026-11-04 review found four defects in the command layer, all of them
about the same thing: **the command lied to the caller**.

- it suggested a command name that did not exist (``audit-app-integrity``),
- ``--limit`` was applied per check instead of to the envelope as a whole,
- the exit code was severity-blind, so a ``high`` finding and a ``medium``
  finding both produced the same code and a CI gate could not tell them
  apart,
- the apps root was hard-coded to ``/home/frappe/frappe-bench/apps``, so on
  any other bench the command scanned nothing and reported "no findings".

These tests are bench-free: they drive the click command directly with a
synthetic apps tree and never import Frappe for real.
"""
from __future__ import annotations

import json

import _frappe_stub
from conftest import FakeApp

_frappe_stub.install()

from click.testing import CliRunner
from app_migrator.commands.audit_integrity import (
    app_migrator_audit_integrity,
)


GUEST_WRITE_ENDPOINT = """
import frappe


@frappe.whitelist(allow_guest=True)
def receive_weight_event(**kwargs):
    doc = frappe.get_doc({"doctype": "Weight Event"})
    doc.insert(ignore_permissions=True)
    frappe.db.commit()
    return {"status": "success"}
"""


def _run(root, *args):
    """Run the command against ``root`` and return the click result."""
    return CliRunner().invoke(
        app_migrator_audit_integrity,
        ["--apps-root", str(root), "--json", *args],
    )


def _envelope(result):
    """Parse the JSON envelope the command printed."""
    assert result.exit_code in (0, 10, 20, 40), (
        f"unexpected exit code {result.exit_code}: {result.output}"
    )
    return json.loads(result.output)


def test_a_clean_tree_exits_zero(apps_root):
    root = apps_root([FakeApp(name="amb_w_tds")])
    result = _run(root, "--check", "endpoint-permission-gap")
    assert result.exit_code == 0, result.output
    envelope = _envelope(result)
    assert envelope["status"] == "ok", envelope["status"]


def test_a_medium_finding_exits_ten(apps_root):
    """A ``medium`` finding is a warning, not a block."""
    root = apps_root([
        FakeApp(name="amb_w_spc", doctypes={"Batch AMB": ["name"]}),
        FakeApp(name="amb_w_tds"),
    ])
    # amb_w_tds links into amb_w_spc without declaring the dependency.
    import json as _json
    import os

    dt_dir = os.path.join(str(root), "amb_w_tds", "amb_w_tds", "doctype", "tds_batch")
    os.makedirs(dt_dir, exist_ok=True)
    with open(os.path.join(dt_dir, "tds_batch.json"), "w", encoding="utf-8") as fh:
        _json.dump(
            {
                "name": "TDS Batch",
                "fields": [
                    {"fieldname": "batch_amb_ref", "fieldtype": "Link",
                     "options": "Batch AMB"}
                ],
            },
            fh,
        )
    result = _run(root, "--check", "undeclared-app-dependency")
    assert result.exit_code == 10, (result.exit_code, result.output)
    envelope = _envelope(result)
    assert envelope["status"] == "warn", envelope["status"]
    assert envelope["findings"], envelope


def test_a_high_finding_exits_twenty(apps_root):
    """A ``high`` finding blocks: the exit code says so."""
    root = apps_root([
        FakeApp(
            name="amb_w_spc",
            python_files={
                "system_integration/doctype/weight_event/weight_event.py":
                    GUEST_WRITE_ENDPOINT
            },
        ),
    ])
    result = _run(root, "--check", "endpoint-permission-gap")
    assert result.exit_code == 20, (result.exit_code, result.output)
    envelope = _envelope(result)
    assert envelope["status"] == "blocked", envelope["status"]


def test_the_limit_is_envelope_wide_not_per_check(apps_root):
    """``--limit 1`` carries at most one finding in the whole envelope.

    The old code applied the limit inside each check, so eight checks could
    return eight findings for a limit of one.
    """
    root = apps_root([
        FakeApp(
            name="amb_w_spc",
            python_files={
                "system_integration/doctype/weight_event/weight_event.py":
                    GUEST_WRITE_ENDPOINT
            },
        ),
    ])
    result = _run(root, "--limit", "1")
    assert result.exit_code == 20, (result.exit_code, result.output)
    envelope = _envelope(result)
    assert len(envelope["findings"]) == 1, envelope["findings"]
    # The true count is still reported, so a truncation never hides a number.
    evidence = {item["kind"]: item for item in envelope["evidence"]}
    assert evidence["scan_params"]["findings_truncated"] >= 0


def test_the_suggested_command_exists(apps_root):
    """The envelope must not suggest a command that does not exist."""
    root = apps_root([FakeApp(name="amb_w_tds")])
    result = _run(root)
    envelope = _envelope(result)
    for suggestion in envelope["suggested_next_commands"]:
        command = suggestion["command"]
        assert "audit-app-integrity" not in command, command
        assert "audit-integrity" in command, command


def _make_bench(base):
    """Build a bench layout: ``<base>/apps`` + ``sites/apps.txt`` + ``Procfile``."""
    bench = base / "frappe-bench"
    apps = bench / "apps"
    apps.mkdir(parents=True)
    (bench / "sites").mkdir()
    (bench / "sites" / "apps.txt").write_text("amb_w_tds\n", encoding="utf-8")
    (bench / "Procfile").write_text("web: bench serve\n", encoding="utf-8")
    return bench, apps


def test_the_apps_root_is_discovered_from_the_bench_env_var(tmp_path, monkeypatch):
    """``FRAPPE_BENCH`` must be honoured.

    The old default was the literal ``/home/frappe/frappe-bench/apps``, so
    on every bench that is not laid out exactly that way the command scanned
    a directory that does not exist and reported "no findings".
    """
    from app_migrator._integrity import context

    bench, apps = _make_bench(tmp_path)
    monkeypatch.setenv("FRAPPE_BENCH", str(bench))
    assert context.discover_apps_root() == str(apps)


def test_the_apps_root_is_discovered_by_walking_up_from_the_cwd(tmp_path, monkeypatch):
    """A bench in an ancestor directory is found without any configuration."""
    from app_migrator._integrity import context

    bench, apps = _make_bench(tmp_path)
    monkeypatch.delenv("FRAPPE_BENCH", raising=False)
    monkeypatch.delenv("BENCH_PATH", raising=False)
    monkeypatch.delenv("BENCH_APPS_ROOT", raising=False)
    monkeypatch.delenv("FRAPPE_APPS_ROOT", raising=False)
    monkeypatch.chdir(bench)
    assert context.discover_apps_root() == str(apps)


def test_an_explicit_apps_root_env_var_wins(tmp_path, monkeypatch):
    from app_migrator._integrity import context

    bench, _apps = _make_bench(tmp_path)
    other = tmp_path / "elsewhere"
    other.mkdir()
    monkeypatch.setenv("FRAPPE_BENCH", str(bench))
    monkeypatch.setenv("BENCH_APPS_ROOT", str(other))
    assert context.discover_apps_root() == str(other)
