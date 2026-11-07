"""Check: the same Python package shipped at two paths inside one app.

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
imported as ``amb_w_tds.api.batch_api``, the other as ``api.batch_api``. A fix
applied to one copy silently leaves the other untouched, so the bug the fix was
meant to remove comes back on the next migrate — and the copy that is still
shipped is whichever one some other code happens to import.

What is reported
----------------
One finding per duplicated module path inside an app. Copies that have already
diverged are ``high`` — that is a live defect. Copies that are still
byte-identical are ``medium``: nothing is broken yet, but the next edit to one
copy turns it into one.
"""
from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Dict, List, Optional

from ..base import CheckResult, CheckSpec, Finding
from ..context import SKIP_DIRS, Inventory

CHECK_ID = "duplicate-module-tree"

#: Files that mark a directory as an importable Python package.
PACKAGE_MARKER = "__init__.py"


def _slug(text: str) -> str:
    """Kebab-case slug, used to build stable finding ids."""
    slug = re.sub(r"[^0-9a-zA-Z]+", "-", str(text)).strip("-").lower()
    return slug or "unknown"


def _module_suffix(app: Any, dirpath: str) -> str:
    """Module path of ``dirpath`` relative to the app's Python package.

    A directory inside the package yields its path relative to the package
    (``api``). A directory outside it — a second copy of the package at the
    app root — yields its path relative to the app root (``api`` as well).
    That is what makes the two copies collide on the same module suffix.
    """
    package = os.path.abspath(app.package)
    target = os.path.abspath(dirpath)
    if target == package:
        return ""
    if target.startswith(package + os.sep):
        rel = os.path.relpath(target, package)
    else:
        rel = os.path.relpath(target, app.root)
    rel = rel.replace(os.sep, "/")
    return "" if rel == "." else rel


def _module_dirs(app: Any) -> Dict[str, List[str]]:
    """Map module suffix -> the ABSOLUTE path of every copy of that module.

    Absolute paths are returned so that comparison never has to re-join them
    onto a base that may not be the one they were found under. The
    human-facing, unambiguous form is produced separately by
    ``_display_path`` (apps-root-relative), because an app-root-relative form
    would collapse one copy to a bare ``api`` — exactly the ambiguity this
    check exists to remove.
    """
    groups: Dict[str, List[str]] = {}
    for dirpath, dirnames, filenames in os.walk(app.root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        if PACKAGE_MARKER not in filenames:
            continue
        suffix = _module_suffix(app, dirpath)
        if not suffix:
            continue
        groups.setdefault(suffix, []).append(os.path.abspath(dirpath))
    return groups


def _display_path(app: Any, dirpath: str) -> str:
    """Path of a module copy relative to the bench ``apps/`` directory."""
    apps_root = os.path.dirname(os.path.abspath(app.root))
    return os.path.relpath(os.path.abspath(dirpath), apps_root).replace(os.sep, "/")


def _sha256(path: str) -> Optional[str]:
    """SHA-256 of a file's bytes, or ``None`` when it cannot be read."""
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def _file_hashes(dirpath: str) -> Dict[str, Optional[str]]:
    """Map file path (relative to ``dirpath``) -> sha256 of its content."""
    hashes: Dict[str, Optional[str]] = {}
    for sub, dirnames, filenames in os.walk(dirpath):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            if filename.endswith((".pyc", ".pyo")):
                continue
            full = os.path.join(sub, filename)
            rel = os.path.relpath(full, dirpath).replace(os.sep, "/")
            hashes[rel] = _sha256(full)
    return hashes


def _compare_copies(copies_abs: List[str], display: Dict[str, str]) -> Dict[str, Any]:
    """Compare the files of two or more copies of the same module tree.

    ``copies_abs`` are absolute directories; ``display`` maps each absolute
    path to the apps-root-relative path used in the finding evidence.
    """
    per_copy: Dict[str, Dict[str, Optional[str]]] = {}
    for abs_path in copies_abs:
        per_copy[abs_path] = _file_hashes(abs_path)
    all_files = sorted({name for files in per_copy.values() for name in files})
    diverged: List[Dict[str, Any]] = []
    identical_files = 0
    for name in all_files:
        digests = {display[abs_path]: per_copy[abs_path].get(name) for abs_path in copies_abs}
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
    }


def scan_duplicate_trees(inventory: Inventory) -> Dict[str, Any]:
    """Scan every app for module trees that exist at more than one path.

    Returns a dict with a ``duplicates`` map of finding id -> comparison
    facts, plus scan counters under ``_stats``.
    """
    duplicates: Dict[str, Any] = {}
    stats: Dict[str, Any] = {
        "apps_scanned": len(inventory.apps),
        "module_dirs_scanned": 0,
        "duplicate_modules": 0,
        "diverged_modules": 0,
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
            }
            stats["duplicate_modules"] += 1
            if comparison["identical"]:
                stats["identical_modules"] += 1
            else:
                stats["diverged_modules"] += 1
    return {"duplicates": duplicates, "_stats": stats}


def build_findings(scan: Dict[str, Any]) -> List[Finding]:
    """Turn the duplicate-tree scan into envelope findings."""
    findings: List[Finding] = []
    for finding_id in sorted(scan.get("duplicates", {})):
        info = scan["duplicates"][finding_id]
        paths = info["paths"]
        if info["identical"]:
            severity = "medium"
            detail = (
                f"All {info['file_count']} files are byte-identical today, so nothing looks "
                "wrong yet. But the two copies are two different modules to Python, so the "
                "next edit to one of them leaves the other stale — and which copy is live "
                "depends on how the code imports it."
            )
        else:
            severity = "high"
            diverged = ", ".join(entry["file"] for entry in info["diverged_files"])
            detail = (
                f"{len(info['diverged_files'])} of {info['file_count']} files have already "
                f"diverged ({diverged}). The two copies are two different modules to "
                "Python, so a fix applied to one of them silently leaves the other "
                "untouched and the shipped behaviour depends on which one is imported."
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
