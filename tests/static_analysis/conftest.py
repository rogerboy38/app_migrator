"""Bench-free test substrate for the audit-derived integrity checks.

Two things this conftest does that the parent ``tests/conftest.py`` does not:

1. **Overrides the parent's autouse bench guard.** The parent skips the whole
   session when the ``bench`` CLI is not on PATH, because its tests target the
   VM2 substrate. The integrity checks are deliberately bench-free — they read
   the filesystem and parse files — so they must be runnable anywhere, on a
   laptop with no Frappe installed. Redefining the same fixture name shadows
   the parent's for this directory.

2. **Provides synthetic bench fixtures.** The checks are verified against
   purpose-built app trees that reproduce the exact defects the two audits
   found, so a regression is a test failure rather than a surprise on a
   production bench.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pytest


# --------------------------------------------------------------------------
# Override the parent's autouse guard: these tests must NOT require `bench`.
# --------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _require_bench_on_path():
    """No-op override — the integrity checks are bench-free by design."""
    yield


# --------------------------------------------------------------------------
# Synthetic bench builder
# --------------------------------------------------------------------------
@dataclass
class FakeApp:
    """A synthetic Frappe app to materialise on disk.

    Attributes:
        name: app name (its package dir is ``<root>/<name>/<name>``).
        doctypes: doctype name -> list of standard fieldnames.
        custom_fields: Custom Field fixture records.
        property_setters: Property Setter fixture records.
        hooks: raw ``hooks.py`` source.
        python_files: package-relative path -> source.
        js_files: app-relative path -> source (under ``public/js``).
        fixtures: extra fixture files (name -> records).
    """

    name: str
    doctypes: Dict[str, List[str]] = field(default_factory=dict)
    custom_fields: List[Dict[str, Any]] = field(default_factory=list)
    property_setters: List[Dict[str, Any]] = field(default_factory=list)
    hooks: str = "app_name = '{name}'\n"
    python_files: Dict[str, str] = field(default_factory=dict)
    js_files: Dict[str, str] = field(default_factory=dict)
    fixtures: Dict[str, List[Any]] = field(default_factory=dict)


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def materialise_app(root: str, app: FakeApp) -> str:
    """Write one :class:`FakeApp` under ``root`` and return its directory."""
    app_root = os.path.join(root, app.name)
    pkg = os.path.join(app_root, app.name)
    os.makedirs(pkg, exist_ok=True)
    _write(os.path.join(pkg, "__init__.py"), "")

    _write(os.path.join(app_root, "hooks.py"), app.hooks.format(name=app.name))

    for doctype, fields in app.doctypes.items():
        slug = doctype.lower().replace(" ", "_").replace("-", "_")
        dt_dir = os.path.join(pkg, "doctype", slug)
        payload = {
            "name": doctype,
            "fields": [{"fieldname": f, "fieldtype": "Data"} for f in fields],
        }
        _write(os.path.join(dt_dir, f"{slug}.json"), json.dumps(payload, indent=2))
        _write(
            os.path.join(dt_dir, f"{slug}.py"),
            "import frappe\nfrom frappe.model.document import Document\n\n\n"
            f"class {doctype.replace(' ', '').replace('-', '')}(Document):\n    pass\n",
        )

    if app.custom_fields:
        _write(
            os.path.join(app_root, "fixtures", "custom_field.json"),
            json.dumps(app.custom_fields, indent=2),
        )
    if app.property_setters:
        _write(
            os.path.join(app_root, "fixtures", "property_setter.json"),
            json.dumps(app.property_setters, indent=2),
        )
    for fixture_name, records in app.fixtures.items():
        _write(
            os.path.join(app_root, "fixtures", fixture_name),
            json.dumps(records, indent=2),
        )

    for relpath, source in app.python_files.items():
        _write(os.path.join(pkg, relpath), source)
    for relpath, source in app.js_files.items():
        _write(os.path.join(app_root, "public", "js", relpath), source)

    return app_root


def build_apps_root(root: str, apps: List[FakeApp]) -> str:
    """Materialise a whole bench ``apps/`` directory and write ``apps.txt``."""
    for app in apps:
        materialise_app(root, app)
    _write(os.path.join(root, "apps.txt"), "\n".join(a.name for a in apps) + "\n")
    return root


@pytest.fixture
def apps_root(tmp_path):
    """Factory fixture: ``apps_root([FakeApp(...), ...])`` -> directory path."""
    counter = {"n": 0}

    def _build(apps: List[FakeApp]) -> str:
        counter["n"] += 1
        root = tmp_path / f"bench_{counter['n']}"
        root.mkdir(parents=True, exist_ok=True)
        return build_apps_root(str(root), apps)

    return _build


@pytest.fixture
def inventory():
    """Factory fixture: ``inventory(apps_root_path)`` -> an ``Inventory``."""
    from app_migrator._integrity import Inventory

    def _make(root: str):
        return Inventory(apps_root=root)

    return _make


def find_check(check_id: str):
    """Return the registered check spec for ``check_id``."""
    from app_migrator._integrity.checks import CHECKS

    for spec in CHECKS:
        if spec.check_id == check_id:
            return spec
    raise AssertionError(
        f"check {check_id!r} is not registered; available: "
        f"{[s.check_id for s in CHECKS]}"
    )


def run_check(check_id: str, inv):
    """Run one registered check against an inventory and return its result."""
    return find_check(check_id).run(inv)


def finding_ids(result) -> List[str]:
    """All finding ids of a check result."""
    return [f.id for f in result.findings]
