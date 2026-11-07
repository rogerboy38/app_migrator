"""Check: the same Python module shipped at two paths inside one app.

Why this check exists
---------------------
Audited evidence (both audits, 2026-11-05):

- ``amb_w_tds`` ships ``amb_w_tds/api/`` **and** ``amb_w_tds/amb_w_tds/api/``.
- Three files in the two copies were byte-identical; two (``batch_api.py`` and
  ``bom_tree_fix.py``) had **already diverged** — 115 and 88 differing lines —
  even though both were last touched in the same commit.

Why it matters
--------------
Two copies of the same module are two different modules to Python: one is
imported as ``amb_w_tds.api.batch_api``, the other as
``amb_w_tds.amb_w_tds.api.batch_api``. A fix applied to one copy silently
leaves the other untouched, so the bug the fix was meant to remove comes back
on the next migrate — and the copy that is still shipped is whichever one some
other code happens to import.

What is reported
----------------
One finding per duplicated module path inside an app:

- ``high``   — the copies **differ**: a file exists in both with different
  bytes, or a file exists in only one of them. That is a live defect, because
  which copy is imported decides which behaviour ships.
- ``medium`` — the copies are byte-identical. Nothing looks wrong today, but the
  two trees are two different modules to Python, so the next edit to one of them
  turns it into one. In the audited pair, three of the five files were still
  byte-identical while two had already diverged.

The comparison is module code only (``.py`` files). Content folders such as
``scripts/``, ``docs/`` or ``fixtures/`` are not modules and are excluded from
the scan, so the developer handouts that live in the repo-root ``scripts/``
folder never show up as a "duplicated module".
"""
from __future__ import annotations

import hashlib
import os
import re
from typing import Any

from ..base import CheckResult, CheckSpec, Finding
from ..context import SKIP_DIRS, Inventory

CHECK_ID = "duplicate-module-tree"

#: Files that mark a directory as an importable Python package.
PACKAGE_MARKER = "__init__.py"

#: Directories that hold app content, not importable module code. They are
#: never treated as a copy of a module and never descended into.
NON_MODULE_DIRS = {
    "scripts", "docs", "test", "tests", "fixtures", "patches", "migrations",
    "templates", "public", "www", "locale", "config",
    "node_modules", "__pycache__", ".git",
}

#: Every directory name the scan never descends into.
SKIP = set(SKIP_DIRS) | NON_MODULE_DIRS


def _slug(text: str) -> str:
    """Kebab-case slug, used to build stable finding ids."""
    slug = re.sub(r"[^0-9a-zA-Z]+", "-", str(text)).strip("-").lower()
    return slug or "unknown"


def _is_inside(parent: str, child: str) -> bool:
    """True when ``child`` is ``parent`` itself or lives under it."""
    return child == parent or child.startswith(parent + os.sep)


def _holds_app_content(dirpath: str) -> bool:
    """True when ``dirpath`` holds the app's real content (``doctype/``/``fixtures/``)."""
    return (
        os.path.isdir(os.path.join(dirpath, "doctype"))
        or os.path.isdir(os.path.join(dirpath, "fixtures"))
    )


def _module_root(app: Any) -> str:
    """The directory that holds the app's real content — its *module root*.

    For the audited apps the module root is ``apps/<app>/<app>/<app>/``: the
    doubly-nested directory that holds ``doctype/`` and ``fixtures/``. The
    Python package is one level above it (``apps/<app>/<app>/``), which is why
    the two copies of ``api`` sit at different depths and still have to be
    recognised as the same module.

    The deepest candidate that actually holds app content wins; when no
    candidate holds content, the deepest one that merely exists is used, so a
    nested namespace-package directory still acts as a module root.
    """
    package = os.path.abspath(app.package)
    candidates = []
    nested = os.path.join(package, app.name)
    if os.path.isdir(nested):
        candidates.append(nested)
    if os.path.isdir(package):
        candidates.append(package)
    if not candidates:
        return package
    for candidate in candidates:
        if _holds_app_content(candidate):
            return candidate
    return candidates[0]


def _module_suffix(app: Any, dirpath: str, module_root: str) -> str:
    """Module path of ``dirpath``, normalised so that the two copies collide.

    * inside the module root -> path relative to the module root
      (``apps/<app>/<app>/<app>/api`` -> ``api``);
    * inside the Python package but outside the module root -> path relative
      to the package (``apps/<app>/<app>/api`` -> ``api``);
    * outside the package entirely -> path relative to the app root, which is
      how a second copy of the package at the app root is named.

    A leading ``<app_name>/`` segment is then stripped from the result, so
    ``package/api`` and ``package/<app>/api`` both resolve to ``api`` whichever
    of the two bases the path was taken from. With the audited layout both
    copies of ``api`` therefore resolve to the same suffix ``api``, which is
    what makes them collide.
    """
    package = os.path.abspath(app.package)
    target = os.path.abspath(dirpath)
    if _is_inside(module_root, target):
        rel = os.path.relpath(target, module_root)
    elif _is_inside(package, target):
        rel = os.path.relpath(target, package)
    else:
        rel = os.path.relpath(target, app.root)
    parts = rel.replace(os.sep, "/").split("/")
    if len(parts) > 1 and parts[0] == app.name:
        parts = parts[1:]
    rel = "/".join(parts)
    return "" if rel in ("", ".") else rel


def _is_module_dir(filenames: list[str]) -> bool:
    """True when a directory holds importable module code.

    A directory with at least one ``.py`` file is module code — including a
    namespace package, which imports fine without ``__init__.py``. A directory
    with only ``__init__.py`` is an empty package and is kept as well.
    """
    if PACKAGE_MARKER in filenames:
        return True
    return any(name.endswith(".py") for name in filenames)


def _module_dirs(app: Any) -> dict[str, list[str]]:
    """Map module suffix -> the ABSOLUTE path of every copy of that module.

    Absolute paths are returned so that comparison never has to re-join them
    onto a base that may not be the one they were found under. The
    human-facing, unambiguous form is produced separately by
    ``_display_path`` (apps-root-relative), because an app-root-relative form
    would collapse one copy to a bare ``api`` — exactly the ambiguity this
    check exists to remove.
    """
    module_root = _module_root(app)
    groups: dict[str, list[str]] = {}
    for dirpath, dirnames, filenames in os.walk(app.root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP)
        if not _is_module_dir(filenames):
            continue
        suffix = _module_suffix(app, dirpath, module_root)
        if not suffix:
            continue
        groups.setdefault(suffix, []).append(os.path.abspath(dirpath))
    return groups


def _display_path(app: Any, dirpath: str) -> str:
    """Path of a module copy relative to the bench ``apps/`` directory."""
    apps_root = os.path.dirname(os.path.abspath(app.root))
    return os.path.relpath(os.path.abspath(dirpath), apps_root).replace(os.sep, "/")


def _sha256(path: str) -> str | None:
    """SHA-256 of a file's bytes, or ``None`` when it cannot be read."""
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def _file_hashes(dirpath: str) -> dict[str, str | None]:
    """Map file path (relative to ``dirpath``) -> sha256 of its content.

    Only ``.py`` files count: a module copy is module code, and the handouts,
    shell scripts and JSON blobs that sit next to it are not part of the
    comparison.
    """
    hashes: dict[str, str | None] = {}
    for sub, dirnames, filenames in os.walk(dirpath):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP)
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            full = os.path.join(sub, filename)
            rel = os.path.relpath(full, dirpath).replace(os.sep, "/")
            hashes[rel] = _sha256(full)
    return hashes


def _compare_copies(copies_abs: list[str], display: dict[str, str]) -> dict[str, Any]:
    """Compare the files of two or more copies of the same module tree.

    ``copies_abs`` are absolute directories; ``display`` maps each absolute
    path to the apps-root-relative path used in the finding evidence.

    Every difference between the copies is a difference, so it lands in
    ``diverged_files`` — the file's sha256 in each copy, ``None`` for a copy
    that does not have the file at all:

    - ``diverged_files`` — the content differs between the copies, or the file
      exists in only some of them. Either way the two copies are no longer the
      same module.
    - ``one_sided_files`` — the subset that exists in only some copies, kept
      apart because a missing file is drift rather than a disagreement about
      content.
    """
    per_copy: dict[str, dict[str, str | None]] = {}
    for abs_path in copies_abs:
        per_copy[abs_path] = _file_hashes(abs_path)
    all_files = sorted({name for files in per_copy.values() for name in files})
    diverged: list[dict[str, Any]] = []
    one_sided: list[dict[str, Any]] = []
    identical_files = 0
    for name in all_files:
        present = [abs_path for abs_path in copies_abs if name in per_copy[abs_path]]
        digests = {display[abs_path]: per_copy[abs_path].get(name) for abs_path in copies_abs}
        if len(present) != len(copies_abs):
            one_sided.append({
                "file": name,
                "present_in": sorted(display[abs_path] for abs_path in present),
                "missing_from": sorted(
                    display[abs_path] for abs_path in copies_abs if abs_path not in present
                ),
            })
            diverged.append({"file": name, "sha256": digests})
            continue
        values = set(digests.values())
        if len(values) == 1 and None not in values:
            identical_files += 1
        else:
            diverged.append({"file": name, "sha256": digests})
    return {
        "file_count": len(all_files),
        "identical_files": identical_files,
        "identical": not diverged,
        "diverged_files": diverged,
        "one_sided_files": one_sided,
    }


def scan_duplicate_trees(inventory: Inventory) -> dict[str, Any]:
    """Scan every app for module trees that exist at more than one path.

    Returns a dict with a ``duplicates`` map of finding id -> comparison
    facts, plus scan counters under ``_stats``.
    """
    duplicates: dict[str, Any] = {}
    stats: dict[str, Any] = {
        "apps_scanned": len(inventory.apps),
        "module_dirs_scanned": 0,
        "duplicate_modules": 0,
        "diverged_modules": 0,
        "one_sided_modules": 0,
        "identical_modules": 0,
    }
    for app in inventory.apps:
        groups = _module_dirs(app)
        stats["module_dirs_scanned"] += sum(len(paths) for paths in groups.values())
        for suffix in sorted(groups):
            copies_abs = sorted(groups[suffix])
            if len(copies_abs) < 2:
                continue
            display = {abs_path: _display_path(app, abs_path) for abs_path in copies_abs}
            copies = sorted(display.values())
            comparison = _compare_copies(copies_abs, display)
            finding_id = f"integrity-{CHECK_ID}-{_slug(app.name)}-{_slug(suffix)}"
            duplicates[finding_id] = {
                "app": app.name,
                "module": suffix,
                "paths": copies,
                "file_count": comparison["file_count"],
                "identical": comparison["identical"],
                "identical_files": comparison["identical_files"],
                "diverged_files": comparison["diverged_files"],
                "one_sided_files": comparison["one_sided_files"],
            }
            stats["duplicate_modules"] += 1
            if comparison["diverged_files"]:
                stats["diverged_modules"] += 1
            else:
                stats["identical_modules"] += 1
            if comparison["one_sided_files"]:
                # A subset of ``diverged_modules``: the copies differ by a file
                # that exists on one side only, not by content.
                stats["one_sided_modules"] += 1
    return {"duplicates": duplicates, "_stats": stats}


def build_findings(scan: dict[str, Any]) -> list[Finding]:
    """Turn the duplicate-tree scan into envelope findings."""
    findings: list[Finding] = []
    for finding_id in sorted(scan.get("duplicates", {})):
        info = scan["duplicates"][finding_id]
        paths = info["paths"]
        if info["diverged_files"]:
            severity = "high"
            diverged = ", ".join(entry["file"] for entry in info["diverged_files"])
            detail = (
                f"{len(info['diverged_files'])} of {info['file_count']} files differ between "
                f"the copies ({diverged}). The two copies are two different modules to "
                "Python, so a fix applied to one of them silently leaves the other "
                "untouched and the shipped behaviour depends on which one is imported."
            )
        else:
            severity = "medium"
            detail = (
                f"All {info['file_count']} files are byte-identical today, so nothing looks "
                "wrong yet. But the two copies are two different modules to Python, so the "
                "next edit to one of them leaves the other stale — and which copy is live "
                "depends on how the code imports it."
            )
        findings.append(
            Finding(
                id=finding_id,
                title=f"Module '{info['module']}' is shipped twice in app '{info['app']}'",
                severity=severity,
                description=(
                    f"App '{info['app']}' ships the module '{info['module']}' at "
                    f"{len(paths)} different paths ({', '.join(paths)}). {detail}"
                ),
                app=info["app"],
                evidence={
                    "app": info["app"],
                    "module": info["module"],
                    "paths": paths,
                    "file_count": info["file_count"],
                    "identical": info["identical"],
                    "diverged_files": info["diverged_files"],
                    "one_sided_files": info["one_sided_files"],
                    "identical_files": info["identical_files"],
                },
            )
        )
    return findings


def check_duplicate_module_tree(inventory: Inventory) -> CheckResult:
    """Check entry point."""
    scan = scan_duplicate_trees(inventory)
    return CheckResult(
        check_id=CHECK_ID,
        findings=build_findings(scan),
        stats=scan["_stats"],
    )


CHECK_SPEC = CheckSpec(
    check_id=CHECK_ID,
    title="Python module shipped at two paths inside one app",
    description=(
        "Detect the same importable module tree existing at more than one path "
        "inside an app, where a fix applied to one copy silently misses the other."
    ),
    fn=check_duplicate_module_tree,
)
