"""Check: duplicate-module-tree — the tests.

These tests reproduce the defect the 2026-11-05 audit actually found:
``amb_w_tds`` ships ``amb_w_tds/api/`` **and** ``amb_w_tds/amb_w_tds/api/``.
Three files were byte-identical; two (``batch_api.py`` and ``bom_tree_fix.py``)
had already diverged — 115 and 88 differing lines — even though both were last
touched in the same commit.

The check is bench-free: these tests run with no Frappe and no ``bench``
CLI, which is the point of placing them outside ``app_migrator/commands/``.
"""
from __future__ import annotations

from conftest import FakeApp, finding_ids, run_check

CHECK_ID = "duplicate-module-tree"

# The second copy lives at the app root, so it is written with a ``..``
# segment relative to the app package. ``python_files`` is the only knob the
# shared ``FakeApp`` builder offers, and it is enough to place a tree
# outside the package.
ROOT_COPY = {
    "../api/__init__.py": "",
    "../api/batch_api.py": "PACKAGE VERSION\n",
    "../api/bom_tree_fix.py": "PACKAGE VERSION\n",
}

PACKAGE_COPY = {
    "api/__init__.py": "",
    "api/batch_api.py": "PACKAGE VERSION\n",
    "api/bom_tree_fix.py": "PACKAGE VERSION\n",
}

DIVERGED_PACKAGE_COPY = {
    "api/__init__.py": "",
    "api/batch_api.py": "PACKAGE VERSION\n",
    "api/bom_tree_fix.py": "PACKAGE VERSION\n",
}

DIVERGED_ROOT_COPY = {
    "../api/__init__.py": "",
    "../api/batch_api.py": "ROOT VERSION\n",
    "../api/bom_tree_fix.py": "PACKAGE VERSION\n",
}


def test_diverged_copies_are_high(apps_root, inventory):
    """Already-diverged copies are a live defect, not a latent trap."""
    files = dict(DIVERGED_PACKAGE_COPY)
    files.update(DIVERGED_ROOT_COPY)
    root = apps_root([FakeApp(name="amb_w_tds", python_files=files)])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high", finding.severity
    assert finding.app == "amb_w_tds"
    evidence = finding.evidence
    assert evidence["app"] == "amb_w_tds"
    assert evidence["module"] == "api"
    assert evidence["identical"] is False
    assert evidence["file_count"] == 3
    assert evidence["identical_files"] == 2
    diverged = {entry["file"]: entry["sha256"] for entry in evidence["diverged_files"]}
    assert set(diverged) == {"batch_api.py"}
    assert len(set(diverged["batch_api.py"].values())) == 2


def test_identical_copies_are_medium(apps_root, inventory):
    """Byte-identical copies are a drift risk, not a live bug."""
    files = dict(PACKAGE_COPY)
    files.update(ROOT_COPY)
    root = apps_root([FakeApp(name="amb_w_tds", python_files=files)])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "medium", finding.severity
    evidence = finding.evidence
    assert evidence["identical"] is True
    assert evidence["diverged_files"] == []
    assert evidence["identical_files"] == evidence["file_count"] == 3
    assert evidence["paths"] == ["amb_w_tds/amb_w_tds/api", "amb_w_tds/api"]


def test_single_copy_is_not_reported(apps_root, inventory):
    """The common case must stay clean — a noisy check is a check nobody runs."""
    root = apps_root([FakeApp(name="amb_w_tds", python_files=PACKAGE_COPY)])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)
    assert result.stats["duplicate_modules"] == 0


def test_same_module_in_two_apps_is_not_a_duplicate(apps_root, inventory):
    """Two apps may both ship an ``api`` package — that is not a duplicate."""
    root = apps_root([
        FakeApp(name="app_a", python_files={"api/__init__.py": "", "api/x.py": "X\n"}),
        FakeApp(name="app_b", python_files={"api/__init__.py": "", "api/x.py": "X\n"}),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)
    assert result.stats["duplicate_modules"] == 0


def test_file_missing_from_one_copy_is_a_divergence(apps_root, inventory):
    """A file that exists in only one copy has already diverged."""
    root = apps_root([
        FakeApp(
            name="amb_w_tds",
            python_files={
                "api/__init__.py": "",
                "api/batch_api.py": "PACKAGE VERSION\n",
                "../api/__init__.py": "",
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high"
    assert finding.evidence["identical"] is False
    diverged = {entry["file"]: entry["sha256"] for entry in finding.evidence["diverged_files"]}
    assert set(diverged) == {"batch_api.py"}
    assert None in diverged["batch_api.py"].values()


def test_nested_module_suffix_is_reported(apps_root, inventory):
    """A duplicated nested package is the same defect, one level deeper."""
    root = apps_root([
        FakeApp(
            name="amb_w_tds",
            python_files={
                "doctype/item/__init__.py": "",
                "doctype/item/item.py": "ITEM\n",
                "../doctype/item/__init__.py": "",
                "../doctype/item/item.py": "ITEM\n",
            },
        ),
    ])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.evidence["module"] == "doctype/item"
    assert finding.id == "integrity-duplicate-module-tree-amb-w-tds-doctype-item"


def test_finding_id_is_stable_across_runs(apps_root, inventory):
    """Stable ids are the diff key an agent uses; they must not drift."""
    files = dict(DIVERGED_PACKAGE_COPY)
    files.update(DIVERGED_ROOT_COPY)
    root = apps_root([FakeApp(name="amb_w_tds", python_files=files)])
    first = finding_ids(run_check(CHECK_ID, inventory(root)))
    second = finding_ids(run_check(CHECK_ID, inventory(root)))
    assert first == second
    assert first == ["integrity-duplicate-module-tree-amb-w-tds-api"]


def test_stats_report_what_was_scanned(apps_root, inventory):
    """Every check reports its counters, mirroring the reference check."""
    files = dict(PACKAGE_COPY)
    files.update(ROOT_COPY)
    root = apps_root([FakeApp(name="amb_w_tds", python_files=files)])
    result = run_check(CHECK_ID, inventory(root))
    assert result.stats["apps_scanned"] == 1
    assert result.stats["duplicate_modules"] == 1
    assert result.stats["identical_modules"] == 1
    assert result.stats["diverged_modules"] == 0
    assert result.stats["module_dirs_scanned"] >= 2
