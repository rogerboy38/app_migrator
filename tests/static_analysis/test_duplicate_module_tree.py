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

# ---------------------------------------------------------------------------
# The audited layout
# ---------------------------------------------------------------------------
# ``amb_w_tds`` is doubly nested: the app's *module root* — the directory that
# holds the app's real content — is ``<package>/<app_name>/``, one level below
# the Python package. The two copies of ``api`` sit on either side of it:
#
#   apps/amb_w_tds/amb_w_tds/api/               <- copy 1 (package level)
#   apps/amb_w_tds/amb_w_tds/amb_w_tds/api/     <- copy 2 (module-root level)
#
# Copy 2 has no ``__init__.py``: it is a namespace package, which imports fine
# without one, so a package-marker-only scan skips it entirely.

#: Copy 1 — at the package level, with ``__init__.py``.
PACKAGE_LEVEL_API = {
    "api/__init__.py": "",
    "api/batch_api.py": "PACKAGE VERSION\n",
    "api/bom_tree_fix.py": "PACKAGE VERSION\n",
}

#: The module root holds the app's real content (here ``doctype/``).
MODULE_ROOT_CONTENT = {
    "amb_w_tds/doctype/item/item.py": "ITEM\n",
}

#: Copy 2 — at the module-root level, no ``__init__.py``, ``batch_api.py``
#: already diverged from copy 1.
NESTED_API_DIVERGED = {
    "amb_w_tds/api/batch_api.py": "NESTED VERSION\n",
    "amb_w_tds/api/bom_tree_fix.py": "PACKAGE VERSION\n",
}

#: Copy 2 — same, but nothing has diverged yet.
NESTED_API_IDENTICAL = {
    "amb_w_tds/api/batch_api.py": "PACKAGE VERSION\n",
    "amb_w_tds/api/bom_tree_fix.py": "PACKAGE VERSION\n",
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
    """Byte-identical copies are a drift risk, not a live bug: medium.

    The audited pair was exactly in this state for three of its five files.
    Nothing looks wrong today, but the next edit to one copy leaves the other
    stale — and the audit only found the drift because somebody looked.
    """
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
    assert result.stats["duplicate_modules"] == 1
    assert result.stats["identical_modules"] == 1
    assert result.stats["diverged_modules"] == 0


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


def test_file_missing_from_one_copy_is_high(apps_root, inventory):
    """A file that exists in only one copy is a difference between the copies.

    The copies have drifted apart: one of them ships a file the other does
    not. Which copy is imported decides whether that file exists at all, so
    the pair is ``high``.
    """
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
    assert finding.severity == "high", finding.severity
    evidence = finding.evidence
    assert evidence["identical"] is False
    diverged = {entry["file"]: entry["sha256"] for entry in evidence["diverged_files"]}
    assert set(diverged) == {"batch_api.py"}
    assert None in diverged["batch_api.py"].values()
    one_sided = {entry["file"]: entry for entry in evidence["one_sided_files"]}
    assert set(one_sided) == {"batch_api.py"}
    assert one_sided["batch_api.py"]["present_in"] == ["amb_w_tds/amb_w_tds/api"]
    assert one_sided["batch_api.py"]["missing_from"] == ["amb_w_tds/api"]


def test_nested_module_suffix_is_reported(apps_root, inventory):
    """A duplicated nested package is the same defect, one level deeper."""
    root = apps_root([
        FakeApp(
            name="amb_w_tds",
            python_files={
                "doctype/item/__init__.py": "",
                "doctype/item/item.py": "ITEM\n",
                "../doctype/item/__init__.py": "",
                "../doctype/item/item.py": "DIVERGED ITEM\n",
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
    assert result.stats["one_sided_modules"] == 0
    assert result.stats["module_dirs_scanned"] >= 2


# ---------------------------------------------------------------------------
# Golden tests on the real shape
# ---------------------------------------------------------------------------


def test_nested_module_copy_collides_with_package_copy(apps_root, inventory):
    """The audited pair: one module name at two depths inside one app.

    Copy 1 is ``<package>/api/`` (with ``__init__.py``), copy 2 is
    ``<package>/<app_name>/api/`` (no ``__init__.py`` — a namespace package).
    Both must resolve to the module suffix ``api``, so the pair is one
    duplicated module and not two unrelated directories.
    """
    files = dict(PACKAGE_LEVEL_API)
    files.update(MODULE_ROOT_CONTENT)
    files.update(NESTED_API_DIVERGED)
    root = apps_root([FakeApp(name="amb_w_tds", python_files=files)])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high", finding.severity
    assert finding.id == "integrity-duplicate-module-tree-amb-w-tds-api"
    evidence = finding.evidence
    assert evidence["module"] == "api"
    assert evidence["identical"] is False
    # The two copies must be distinguishable to a human.
    assert evidence["paths"] == [
        "amb_w_tds/amb_w_tds/amb_w_tds/api",
        "amb_w_tds/amb_w_tds/api",
    ]
    assert len(set(evidence["paths"])) == 2
    # ``batch_api.py`` is in both copies and disagrees -> content divergence.
    diverged = {entry["file"]: entry["sha256"] for entry in evidence["diverged_files"]}
    assert set(diverged) == {"batch_api.py", "__init__.py"}
    assert len(set(diverged["batch_api.py"].values())) == 2
    # ``__init__.py`` exists in the package copy only -> the copies differ.
    assert None in diverged["__init__.py"].values()
    one_sided = {entry["file"] for entry in evidence["one_sided_files"]}
    assert one_sided == {"__init__.py"}
    # ``bom_tree_fix.py`` is in both copies and agrees.
    assert evidence["identical_files"] == 1


def test_nested_module_copy_without_app_content_still_collides(apps_root, inventory):
    """A nested namespace directory is a module root even without ``doctype/``."""
    files = {
        "api/__init__.py": "",
        "api/batch_api.py": "PACKAGE VERSION\n",
        "amb_w_tds/api/batch_api.py": "NESTED VERSION\n",
    }
    root = apps_root([FakeApp(name="amb_w_tds", python_files=files)])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high", finding.severity
    assert finding.evidence["module"] == "api"


def test_nested_module_copy_with_identical_content_is_reported(apps_root, inventory):
    """The same pair with nothing diverged still differs: one file is one-sided.

    The nested copy has no ``__init__.py``, so that file exists in only one
    copy — a difference between the copies, and therefore a ``high`` finding
    whose ``diverged_files`` names the file that is missing on one side.
    """
    files = dict(PACKAGE_LEVEL_API)
    files.update(MODULE_ROOT_CONTENT)
    files.update(NESTED_API_IDENTICAL)
    root = apps_root([FakeApp(name="amb_w_tds", python_files=files)])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high", finding.severity
    evidence = finding.evidence
    diverged = {entry["file"]: entry["sha256"] for entry in evidence["diverged_files"]}
    assert set(diverged) == {"__init__.py"}
    assert None in diverged["__init__.py"].values()
    one_sided = {entry["file"] for entry in evidence["one_sided_files"]}
    assert one_sided == {"__init__.py"}


def test_byte_identical_module_copies_are_medium(apps_root, inventory):
    """Two module copies that agree byte for byte are a drift risk: medium."""
    files = {
        "api/__init__.py": "",
        "api/batch_api.py": "SAME\n",
        "amb_w_tds/api/__init__.py": "",
        "amb_w_tds/api/batch_api.py": "SAME\n",
    }
    root = apps_root([FakeApp(name="amb_w_tds", python_files=files)])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "medium", finding.severity
    assert finding.evidence["identical"] is True
    assert finding.evidence["diverged_files"] == []
    assert result.stats["duplicate_modules"] == 1
    assert result.stats["identical_modules"] == 1


def test_extra_file_in_one_copy_is_a_difference(apps_root, inventory):
    """A file that exists in only one copy is a difference between the copies.

    The content of the files the copies share is identical, so the only
    difference is the extra file — it is named in ``diverged_files`` with the
    sha256 of the copy that has it and ``None`` for the copy that has not.
    """
    files = dict(PACKAGE_LEVEL_API)
    files.update(MODULE_ROOT_CONTENT)
    files.update(NESTED_API_IDENTICAL)
    files["api/extra.py"] = "EXTRA\n"
    root = apps_root([FakeApp(name="amb_w_tds", python_files=files)])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "high", finding.severity
    evidence = finding.evidence
    diverged = {entry["file"]: entry["sha256"] for entry in evidence["diverged_files"]}
    assert "extra.py" in diverged
    assert None in diverged["extra.py"].values()
    one_sided = {entry["file"]: entry for entry in evidence["one_sided_files"]}
    assert "extra.py" in one_sided
    assert one_sided["extra.py"]["present_in"] == ["amb_w_tds/amb_w_tds/api"]
    assert one_sided["extra.py"]["missing_from"] == ["amb_w_tds/amb_w_tds/amb_w_tds/api"]


def test_repo_root_scripts_folder_is_not_a_module_duplicate(apps_root, inventory):
    """The repo-root ``scripts/`` folder is content, not a module.

    The repo-root ``scripts/`` folder holds developer handouts and shell
    scripts; the package ``scripts/`` folder holds its own code. Comparing
    them was a false positive — the folders are not importable modules, and
    only ``.py`` files are module code in the first place.
    """
    files = {
        "../scripts/__init__.py": "",
        "../scripts/README.md": "# developer handout\n",
        "../scripts/helper.py": "ROOT HELPER\n",
        "../scripts/run.sh": "#!/bin/sh\n",
        "scripts/__init__.py": "",
        "scripts/helper.py": "PACKAGE HELPER\n",
        "scripts/notes.md": "# notes\n",
    }
    root = apps_root([FakeApp(name="amb_w_tds", python_files=files)])
    result = run_check(CHECK_ID, inventory(root))
    assert result.findings == [], finding_ids(result)
    assert result.stats["duplicate_modules"] == 0


def test_non_python_files_in_module_copies_are_ignored(apps_root, inventory):
    """A ``.md`` handout next to the code is not a divergence.

    Only the module code is compared, so the two ``.md`` files do not count —
    the copies are identical as far as the module is concerned.
    """
    files = {
        "api/__init__.py": "",
        "api/batch_api.py": "SAME\n",
        "api/NOTES.md": "# package notes\n",
        "../api/__init__.py": "",
        "../api/batch_api.py": "SAME\n",
        "../api/README.md": "# root notes\n",
    }
    root = apps_root([FakeApp(name="amb_w_tds", python_files=files)])
    result = run_check(CHECK_ID, inventory(root))
    assert len(result.findings) == 1, finding_ids(result)
    finding = result.findings[0]
    assert finding.severity == "medium"
    assert finding.evidence["file_count"] == 2
    assert finding.evidence["identical"] is True
    assert finding.evidence["diverged_files"] == []
    assert result.stats["duplicate_modules"] == 1
    assert result.stats["identical_modules"] == 1
