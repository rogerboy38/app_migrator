"""Check: hooks that point at code which does not exist — or does nothing.

Why this check exists
---------------------
Audit evidence (``rnd_warehouse_management`` / ``amb_w_tds``, 2026-11-05):

- ``rnd_warehouse_management``'s ``hooks.py`` declares
  ``override_whitelisted_methods`` pointing at
  ``...stock_entry.make_custom_stock_entry`` — that function exists **nowhere**
  in the repository. If Frappe ever resolves that override, it fails the
  request.
- The same ``hooks.py`` declares ``has_website_permission`` ->
  ``rnd_warehouse_management.permissions.warehouse_query`` while the app has
  **no** ``permissions`` module at all.
- The app defines ``class CustomStockEntry(Document)`` carrying real business
  logic (SAP movement checks, dual-signature checks, zone status) that is
  **never referenced anywhere** and is not registered in
  ``override_doctype_class`` — so none of that logic ever runs. Meanwhile four
  of the five ``doc_events`` Stock Entry handlers are literally ``pass``.
- ``amb_w_tds``'s ``hooks.py`` claims ownership of ``Plant Configuration``
  while that DocType ships only in ``amb_w_spc`` — an ownership-claim drift.

Why it matters
--------------
Frappe resolves a hook path **lazily**, when the event fires — never at
install time. A hook that points at nothing therefore installs cleanly, the
migrate succeeds, and the business rule is simply never applied. The app looks
healthy in every migration report while the rule it claims to implement is
dead code.

What is reported
----------------
One finding per dead hook target, with the kind of hook, the value as
written, the resolved file / line when the target does exist, and the reason:

- ``doc_events`` / ``scheduler_events`` handler missing -> ``high``; the
  handler exists but its body is only ``pass`` (or only a docstring) ->
  ``medium`` ("handler is a no-op");
- ``override_whitelisted_methods`` target missing -> ``high``;
- ``override_doctype_class`` target missing -> ``high``; target exists but
  the claimed DocType ships in another app -> ``medium`` (ownership drift);
- ``has_website_permission`` handler missing -> ``medium`` (read from both
  shapes Frappe accepts: a dict keyed by DocType, and a plain list);
- a module-level class inheriting ``Document`` that is never registered or
  referenced anywhere in the app -> ``high``.

Resolution is done on the parsed AST, never by importing the app: the package
must stay importable without a bench.
"""
from __future__ import annotations

import ast
import os
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from ..base import CheckResult, CheckSpec, Finding
from ..context import AppInfo, Inventory, iter_python_files, parse_python

CHECK_ID = "dead-hook-target"

# The hook kinds this check understands, and the severity used when their
# target cannot be resolved.
_MISSING_SEVERITY = {
    "doc-event": "high",
    "scheduler-event": "high",
    "override-whitelisted": "high",
    "doctype-class": "high",
    "website-permission": "medium",
}

# Finding statuses (also used to build the stats counters).
_STATUS_MISSING = "missing"
_STATUS_NOOP = "noop"
_STATUS_DRIFT = "drift"
_STATUS_UNREGISTERED = "unregistered"


def _slugify(value: str) -> str:
    """Lower-case kebab slug: ``"Batch AMB"`` -> ``"batch-amb"``."""
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower())
    return slug.strip("-")


def _rel(app: AppInfo, path: str) -> str:
    """Path relative to the app root, with forward slashes (stable ids)."""
    try:
        return os.path.relpath(path, app.root).replace("\\", "/")
    except ValueError:  # pragma: no cover - different drives on Windows
        return path.replace("\\", "/")


# --------------------------------------------------------------------------
# Dotted-path resolution
# --------------------------------------------------------------------------
def _module_candidates(app: AppInfo, module_parts: Sequence[str]) -> list[str]:
    """Package-relative files that could hold ``module_parts``.

    A hook path normally starts with the app name
    (``my_app.stock_entry.on_update``); the app name is not a directory
    inside the package, so it is stripped first.
    """
    parts = list(module_parts)
    if parts and parts[0] == app.name:
        parts = parts[1:]
    if not parts:
        return ["__init__.py"]
    rel = "/".join(parts)
    return [f"{rel}.py", f"{rel}/__init__.py"]


def _module_exists(app: AppInfo, module_parts: Sequence[str]) -> str | None:
    """The file that holds ``module_parts``, when there is one."""
    for rel in _module_candidates(app, module_parts):
        path = os.path.join(app.package, *rel.split("/"))
        if os.path.isfile(path):
            return path
    return None


def _lookup(tree: ast.Module, name: str) -> tuple[ast.AST | None, str | None]:
    """Find a module-level definition called ``name``."""
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node, "function"
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node, "class"
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return node, "variable"
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            return node, "variable"
    return None, None


def _resolve_attr(
    tree: ast.Module, attr_parts: Sequence[str]
) -> tuple[ast.AST | None, str | None]:
    """Resolve an attribute path inside one module.

    Supports ``name`` and ``Class.name`` (a method of a module-level class).
    """
    node, kind = _lookup(tree, attr_parts[0])
    if node is None:
        return None, None
    if len(attr_parts) == 1:
        return node, kind
    if kind != "class":
        return None, None
    for sub in node.body:
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name == attr_parts[1]:
            if len(attr_parts) > 2:
                return None, None
            return sub, "function"
    return None, None


def _is_noop(node: ast.AST) -> bool:
    """True when a function body does nothing at all.

    A body that only holds ``pass``, only a docstring, or only ``...`` is a
    no-op: the handler runs and changes nothing.
    """
    body = list(getattr(node, "body", []) or [])
    if not body:
        return False
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            value = stmt.value.value
            if isinstance(value, str) or value is Ellipsis:
                continue
        return False
    return True


@dataclass
class _Resolution:
    """Outcome of resolving one dotted hook target."""

    ok: bool
    file: str | None = None
    line: int | None = None
    kind: str | None = None
    noop: bool = False
    module_file: str | None = None
    module_dotted: str | None = None
    attr: str | None = None


class _AppResolver:
    """Resolves dotted hook targets inside one app's package."""

    def __init__(self, app: AppInfo) -> None:
        self.app = app

    def resolve(self, dotted: str) -> _Resolution:
        """Resolve ``dotted`` to a definition inside the app package."""
        parts = [part for part in (dotted or "").split(".") if part]
        if len(parts) < 2:
            return _Resolution(ok=False, attr=parts[-1] if parts else None)

        existing: list[tuple[int, str, str]] = []
        for k in range(len(parts) - 1, 0, -1):
            mod_parts = parts[:k]
            attr_parts = parts[k:]
            for rel in _module_candidates(self.app, mod_parts):
                path = os.path.join(self.app.package, *rel.split("/"))
                if not os.path.isfile(path):
                    continue
                tree = parse_python(path)
                if tree is None:
                    continue
                if not any(entry[0] == k for entry in existing):
                    existing.append((k, path, ".".join(mod_parts)))
                node, kind = _resolve_attr(tree, attr_parts)
                if node is None:
                    continue
                return _Resolution(
                    ok=True,
                    file=path,
                    line=getattr(node, "lineno", None),
                    kind=kind,
                    noop=kind == "function" and _is_noop(node),
                    module_file=path,
                    module_dotted=".".join(mod_parts),
                    attr=attr_parts[0],
                )

        # Nothing resolved: explain what is missing.
        immediate = parts[:-1]
        immediate_file = _module_exists(self.app, immediate)
        if immediate_file is not None:
            # The module exists, the attribute does not.
            return _Resolution(
                ok=False,
                module_file=immediate_file,
                module_dotted=".".join(immediate),
                attr=parts[-1],
            )
        if existing:
            k, path, module_dotted = existing[0]
            if k == 1:
                # Only the package itself resolved: a submodule is missing.
                return _Resolution(
                    ok=False,
                    module_file=None,
                    module_dotted=".".join(immediate),
                    attr=parts[-1],
                )
            return _Resolution(
                ok=False,
                module_file=path,
                module_dotted=module_dotted,
                attr=parts[k],
            )
        return _Resolution(
            ok=False,
            module_file=None,
            module_dotted=".".join(immediate),
            attr=parts[-1],
        )


def _resolve_target(inventory: Inventory, app: AppInfo, dotted: str) -> _Resolution:
    """Resolve a hook target, allowing a target that lives in another app.

    A hook may legitimately point into another installed app. Only a target
    that resolves nowhere is dead.
    """
    resolution = _AppResolver(app).resolve(dotted)
    if resolution.ok:
        return resolution
    for other in inventory.apps:
        if other.name == app.name:
            continue
        other_resolution = _AppResolver(other).resolve(dotted)
        if other_resolution.ok:
            return other_resolution
    return resolution


def _reason(resolution: _Resolution) -> str:
    """Human reason for a target that did not resolve."""
    if resolution.module_file is None:
        return f"module '{resolution.module_dotted}' does not exist in the app"
    return f"'{resolution.attr}' is not defined in module '{resolution.module_dotted}'"


def _handler_slug(handler: str, app: AppInfo) -> str:
    """Slug of a hook handler path, without the leading app name."""
    parts = [part for part in (handler or "").split(".") if part]
    if parts and parts[0] == app.name:
        parts = parts[1:]
    return _slugify(".".join(parts)) or _slugify(handler)


# --------------------------------------------------------------------------
# App source analysis (classes and references)
# --------------------------------------------------------------------------
def _app_python_files(app: AppInfo) -> list[str]:
    """Every python file of the app, including its ``hooks.py``."""
    files = list(iter_python_files(app.package))
    hooks_path = app.hooks.path
    if hooks_path and os.path.isfile(hooks_path):
        files.append(hooks_path)
    return sorted(files)


def _iter_references(tree: ast.Module) -> Iterable[tuple[str, int, str]]:
    """Yield every name an AST tree mentions: ``(name, line, kind)``."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            yield node.id, node.lineno, "name"
        elif isinstance(node, ast.Attribute):
            yield node.attr, node.lineno, "attribute"
        elif isinstance(node, ast.alias):
            yield node.name.split(".")[-1], node.lineno, "import"
            if node.asname:
                yield node.asname, node.lineno, "import"
        elif isinstance(node, ast.ClassDef):
            yield node.name, node.lineno, "classdef"
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield node.name, node.lineno, "funcdef"
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", node.value):
                yield token, node.lineno, "string"


@dataclass
class _AppSource:
    """The app's python source, indexed for class / reference questions."""

    app: AppInfo
    files: list[str] = field(default_factory=list)
    classes: dict[str, tuple[ast.ClassDef, str]] = field(default_factory=dict)
    references: dict[str, list[tuple[str, int, str]]] = field(default_factory=dict)

    @classmethod
    def build(cls, app: AppInfo) -> "_AppSource":
        source = cls(app=app)
        source.files = _app_python_files(app)
        for path in source.files:
            tree = parse_python(path)
            if tree is None:
                continue
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    source.classes.setdefault(node.name, (node, path))
            for name, lineno, kind in _iter_references(tree):
                source.references.setdefault(name, []).append((path, lineno, kind))
        return source

    def references_to(self, name: str, exclude: tuple[str, int] | None = None) -> int:
        """How often ``name`` is mentioned, ignoring its own definition."""
        count = 0
        for path, lineno, kind in self.references.get(name, []):
            if exclude and kind == "classdef" and path == exclude[0] and lineno == exclude[1]:
                continue
            count += 1
        return count


def _base_names(node: ast.ClassDef) -> list[str]:
    """Names of the classes a class definition inherits from."""
    names: list[str] = []
    for base in node.bases:
        if isinstance(base, ast.Name):
            names.append(base.id)
        elif isinstance(base, ast.Attribute):
            names.append(base.attr)
        elif isinstance(base, ast.Call):
            func = base.func
            if isinstance(func, ast.Name):
                names.append(func.id)
            elif isinstance(func, ast.Attribute):
                names.append(func.attr)
    return names


def _is_document_class(
    node: ast.ClassDef,
    classes: dict[str, tuple[ast.ClassDef, str]],
    seen: set[str] | None = None,
) -> bool:
    """True when the class inherits ``Document`` (directly or via a base)."""
    seen = set() if seen is None else seen
    for base in _base_names(node):
        if base in seen:
            continue
        if base == "Document" or base.endswith("Document"):
            return True
        other = classes.get(base)
        if other is not None and _is_document_class(other[0], classes, seen | {base}):
            return True
    return False


def _is_convention_path(app: AppInfo, path: str) -> bool:
    """True for files Frappe resolves by convention, not by reference.

    DocType controllers live in ``doctype/<slug>/<slug>.py`` and are loaded by
    convention; test modules are not part of the app's runtime.
    """
    rel = os.path.relpath(path, app.package).replace("\\", "/")
    parts = rel.split("/")
    directories = parts[:-1]
    filename = parts[-1]
    if "doctype" in directories or "tests" in directories:
        return True
    return filename.startswith("test_") or filename.endswith("_test.py")


# --------------------------------------------------------------------------
# Hook scanners
# --------------------------------------------------------------------------
def _hook_dict(app: AppInfo, name: str) -> dict[str, Any]:
    """A hook value, but only when it is a literal dict."""
    value = app.hooks.get(name)
    return value if isinstance(value, dict) else {}


def _iter_handlers(value: Any) -> Iterable[tuple[str | None, str]]:
    """Yield ``(event, handler)`` pairs from a hook value.

    ``doc_events`` is written either as ``{doctype: [handler, ...]}`` or as
    ``{doctype: {event: [handler, ...]}}``; both shapes are accepted.
    """
    if isinstance(value, str):
        yield None, value
        return
    if isinstance(value, (list, tuple)):
        for handler in value:
            if isinstance(handler, str):
                yield None, handler
        return
    if isinstance(value, dict):
        for event, handlers in value.items():
            if isinstance(handlers, str):
                yield event, handlers
            elif isinstance(handlers, (list, tuple)):
                for handler in handlers:
                    if isinstance(handler, str):
                        yield event, handler


def _entry(
    kind: str,
    slug: str,
    status: str,
    severity: str,
    title: str,
    description: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """One raw finding entry (the app name is added when building)."""
    return {
        "kind": kind,
        "slug": slug,
        "status": status,
        "severity": severity,
        "title": title,
        "description": description,
        "evidence": evidence,
    }


def _missing_entry(
    kind: str,
    slug: str,
    hook: str,
    value: str,
    resolution: _Resolution,
    evidence_extra: dict[str, Any],
) -> dict[str, Any]:
    """Entry for a hook target that does not resolve."""
    evidence = {
        "kind": kind,
        "hook": hook,
        "value": value,
        "reason": _reason(resolution),
    }
    evidence.update(evidence_extra)
    return _entry(
        kind=kind,
        slug=slug,
        status=_STATUS_MISSING,
        severity=_MISSING_SEVERITY[kind],
        title=f"{hook} target does not exist: {value}",
        description=(
            f"hook '{hook}' in this app points at '{value}', but "
            f"{evidence['reason']}. Frappe resolves hook paths lazily, so the "
            f"hook installs cleanly and then never runs."
        ),
        evidence=evidence,
    )


def _noop_entry(
    kind: str,
    slug: str,
    hook: str,
    value: str,
    resolution: _Resolution,
    app: AppInfo,
    evidence_extra: dict[str, Any],
) -> dict[str, Any]:
    """Entry for a hook handler that exists but does nothing."""
    evidence = {
        "kind": kind,
        "hook": hook,
        "value": value,
        "file": _rel(app, resolution.file) if resolution.file else None,
        "line": resolution.line,
        "reason": "handler is a no-op",
    }
    evidence.update(evidence_extra)
    return _entry(
        kind=kind,
        slug=slug,
        status=_STATUS_NOOP,
        severity="medium",
        title=f"{hook} handler is a no-op: {value}",
        description=(
            f"hook '{hook}' in this app points at '{value}', whose body is only "
            f"'pass' (or only a docstring): the handler is a no-op. The rule it "
            f"claims to implement never takes effect."
        ),
        evidence=evidence,
    )


def _scan_doc_events(app: AppInfo, inventory: Inventory) -> list[dict[str, Any]]:
    """``doc_events`` handlers that are missing or do nothing."""
    collected: dict[str, dict[str, Any]] = {}
    for doctype, value in sorted(_hook_dict(app, "doc_events").items()):
        for event, handler in _iter_handlers(value):
            handler = handler.strip()
            if not handler:
                continue
            entry = collected.setdefault(handler, {"doctypes": [], "events": []})
            if doctype not in entry["doctypes"]:
                entry["doctypes"].append(doctype)
            if event and event not in entry["events"]:
                entry["events"].append(event)

    results: list[dict[str, Any]] = []
    for handler, entry in sorted(collected.items()):
        resolution = _resolve_target(inventory, app, handler)
        extra = {"doctypes": entry["doctypes"], "events": entry["events"]}
        slug = _handler_slug(handler, app)
        if not resolution.ok:
            results.append(
                _missing_entry("doc-event", slug, "doc_events", handler, resolution, extra)
            )
        elif resolution.noop:
            results.append(
                _noop_entry("doc-event", slug, "doc_events", handler, resolution, app, extra)
            )
    return results


def _scan_scheduler_events(app: AppInfo, inventory: Inventory) -> list[dict[str, Any]]:
    """``scheduler_events`` handlers that are missing or do nothing."""
    collected: dict[str, dict[str, Any]] = {}
    for event, value in sorted(_hook_dict(app, "scheduler_events").items()):
        for _, handler in _iter_handlers(value):
            handler = handler.strip()
            if not handler:
                continue
            entry = collected.setdefault(handler, {"events": []})
            if event not in entry["events"]:
                entry["events"].append(event)

    results: list[dict[str, Any]] = []
    for handler, entry in sorted(collected.items()):
        resolution = _resolve_target(inventory, app, handler)
        extra = {"events": entry["events"]}
        slug = _handler_slug(handler, app)
        if not resolution.ok:
            results.append(
                _missing_entry(
                    "scheduler-event", slug, "scheduler_events", handler, resolution, extra
                )
            )
        elif resolution.noop:
            results.append(
                _noop_entry(
                    "scheduler-event", slug, "scheduler_events", handler, resolution, app, extra
                )
            )
    return results


def _scan_override_whitelisted(app: AppInfo, inventory: Inventory) -> list[dict[str, Any]]:
    """``override_whitelisted_methods`` targets that do not resolve."""
    collected: dict[str, list[str]] = {}
    for original, target in sorted(_hook_dict(app, "override_whitelisted_methods").items()):
        if not isinstance(target, str) or not target.strip():
            continue
        target = target.strip()
        collected.setdefault(target, []).append(str(original))

    results: list[dict[str, Any]] = []
    for target, originals in sorted(collected.items()):
        resolution = _resolve_target(inventory, app, target)
        if resolution.ok:
            continue
        results.append(
            _missing_entry(
                "override-whitelisted",
                _handler_slug(target, app),
                "override_whitelisted_methods",
                target,
                resolution,
                {"originals": originals},
            )
        )
    return results


def _website_permission_handlers(app: AppInfo) -> list[tuple[str, list[str]]]:
    """``has_website_permission`` handlers and the DocTypes that own them.

    Frappe accepts two shapes for this hook:

    - a **dict** keyed by DocType -> handler path. This is the shape every
      audited app uses: ``rnd_warehouse_management`` keys it by
      ``"Warehouse"`` and ``"Stock Entry"``. A scanner that only understands
      a plain list sees *no* targets at all and reports nothing;
    - a **plain list** of handler paths, accepted by some Frappe versions.

    Returns ``(handler, doctypes)`` pairs sorted by handler. The doctype list
    is empty for the list shape (there is no owner to name). Entries that are
    not strings are skipped.
    """
    value = app.hooks.get("has_website_permission")
    collected: dict[str, list[str]] = {}

    def _add(handler: Any, doctype: str | None) -> None:
        if not isinstance(handler, str):
            return
        handler = handler.strip()
        if not handler:
            return
        owners = collected.setdefault(handler, [])
        if doctype and doctype not in owners:
            owners.append(doctype)

    if isinstance(value, dict):
        for doctype, handler in value.items():
            _add(handler, str(doctype))
    elif isinstance(value, (list, tuple)):
        for handler in value:
            _add(handler, None)

    return [(handler, collected[handler]) for handler in sorted(collected)]


def _scan_website_permission(app: AppInfo, inventory: Inventory) -> list[dict[str, Any]]:
    """``has_website_permission`` handlers that do not resolve.

    The dict shape carries the owning DocType as evidence: ``doctypes`` lists
    every DocType that maps to the handler, ``doctype`` names the owner when
    there is exactly one.
    """
    results: list[dict[str, Any]] = []
    for handler, doctypes in _website_permission_handlers(app):
        resolution = _resolve_target(inventory, app, handler)
        if resolution.ok:
            continue
        extra: dict[str, Any] = {}
        if doctypes:
            extra["doctypes"] = doctypes
            if len(doctypes) == 1:
                extra["doctype"] = doctypes[0]
        results.append(
            _missing_entry(
                "website-permission",
                _handler_slug(handler, app),
                "has_website_permission",
                handler,
                resolution,
                extra,
            )
        )
    return results


def _shipped_name(inventory: Inventory, doctype: str) -> str | None:
    """The name a DocType is actually shipped under (casing may differ)."""
    for name in inventory.all_shipped_doctypes():
        if name.lower() == (doctype or "").lower():
            return name
    return None


def _scan_override_doctype_class(app: AppInfo, inventory: Inventory) -> list[dict[str, Any]]:
    """``override_doctype_class`` targets that do not resolve, or claim drift."""
    results: list[dict[str, Any]] = []
    for doctype, target in sorted(_hook_dict(app, "override_doctype_class").items()):
        if not isinstance(target, str) or not target.strip():
            continue
        target = target.strip()
        slug = _slugify(doctype)
        resolution = _resolve_target(inventory, app, target)
        if not resolution.ok:
            results.append(
                _missing_entry(
                    "doctype-class",
                    slug,
                    "override_doctype_class",
                    target,
                    resolution,
                    {"doctype": doctype},
                )
            )
            continue
        if resolution.kind != "class":
            evidence = {
                "kind": "doctype-class",
                "hook": "override_doctype_class",
                "value": target,
                "doctype": doctype,
                "file": _rel(app, resolution.file) if resolution.file else None,
                "line": resolution.line,
                "reason": "target does not resolve to a class",
            }
            results.append(
                _entry(
                    kind="doctype-class",
                    slug=slug,
                    status=_STATUS_MISSING,
                    severity="high",
                    title=f"override_doctype_class target is not a class: {target}",
                    description=(
                        f"hook 'override_doctype_class' in this app points "
                        f"'{doctype}' at '{target}', which resolves to a "
                        f"{resolution.kind}, not a class. Frappe cannot install "
                        f"the override."
                    ),
                    evidence=evidence,
                )
            )
            continue

        owners = inventory.app_for_doctype(doctype)
        if not owners or app.name in owners:
            # Either nobody ships the DocType (it may live in an app that is
            # not installed here) or this app owns it — nothing to report.
            continue
        owner_app = owners[0]
        evidence = {
            "kind": "doctype-class",
            "hook": "override_doctype_class",
            "value": target,
            "doctype": doctype,
            "shipped_as": _shipped_name(inventory, doctype),
            "owner_app": owner_app,
            "file": _rel(app, resolution.file) if resolution.file else None,
            "line": resolution.line,
            "reason": "claims ownership of a DocType shipped by another app",
        }
        results.append(
            _entry(
                kind="doctype-class",
                slug=slug,
                status=_STATUS_DRIFT,
                severity="medium",
                title=(
                    f"override_doctype_class claims a DocType owned by another "
                    f"app: {doctype}"
                ),
                description=(
                    f"hook 'override_doctype_class' in this app claims "
                    f"'{doctype}', but that DocType ships in '{owner_app}' and "
                    f"not here. The override only applies where '{owner_app}' "
                    f"is installed, so the claimed behaviour is site-dependent."
                ),
                evidence=evidence,
            )
        )
    return results


def _count_hook_targets(app: AppInfo) -> int:
    """How many hook targets the app declares (whether they resolve or not)."""
    total = 0
    for value in _hook_dict(app, "doc_events").values():
        total += sum(1 for _ in _iter_handlers(value))
    for value in _hook_dict(app, "scheduler_events").values():
        total += sum(1 for _ in _iter_handlers(value))
    total += len(_hook_dict(app, "override_whitelisted_methods"))
    total += len(_website_permission_handlers(app))
    total += len(_hook_dict(app, "override_doctype_class"))
    return total


def _scan_unregistered_classes(app: AppInfo, source: _AppSource) -> list[dict[str, Any]]:
    """``Document`` subclasses that nothing in the app ever references."""
    results: list[dict[str, Any]] = []
    for name, (node, path) in sorted(source.classes.items()):
        if not _is_document_class(node, source.classes):
            continue
        if _is_convention_path(app, path):
            continue
        if source.references_to(name, exclude=(path, node.lineno)) > 0:
            continue
        evidence = {
            "kind": "unregistered-class",
            "hook": "override_doctype_class",
            "value": name,
            "class": name,
            "file": _rel(app, path),
            "line": node.lineno,
            "reason": "defined but never registered or referenced",
        }
        results.append(
            _entry(
                kind="unregistered-class",
                slug=_slugify(name),
                status=_STATUS_UNREGISTERED,
                severity="high",
                title=f"Document class is never registered or referenced: {name}",
                description=(
                    f"class '{name}' inherits Document and is defined in "
                    f"{_rel(app, path)}, but nothing in this app imports it, "
                    f"registers it in override_doctype_class, or mentions it "
                    f"anywhere else. Its logic never runs."
                ),
                evidence=evidence,
            )
        )
    return results


# --------------------------------------------------------------------------
# Check entry points
# --------------------------------------------------------------------------
def scan_dead_hook_targets(inventory: Inventory) -> dict[str, Any]:
    """Return the dead hook targets of every app.

    Returns a dict with an ``apps`` map (app name -> list of raw entries)
    plus scan counters under ``_stats``.
    """
    apps: dict[str, Any] = {}
    hooks_scanned = 0
    targets_missing = 0
    targets_noop = 0
    targets_drift = 0
    classes_scanned = 0
    unregistered = 0

    for app in inventory.apps:
        source = _AppSource.build(app)
        classes_scanned += len(source.classes)
        hooks_scanned += _count_hook_targets(app)
        entries: list[dict[str, Any]] = []
        entries += _scan_doc_events(app, inventory)
        entries += _scan_scheduler_events(app, inventory)
        entries += _scan_override_whitelisted(app, inventory)
        entries += _scan_website_permission(app, inventory)
        entries += _scan_override_doctype_class(app, inventory)
        entries += _scan_unregistered_classes(app, source)
        apps[app.name] = entries

        for entry in entries:
            if entry["status"] == _STATUS_MISSING:
                targets_missing += 1
            elif entry["status"] == _STATUS_NOOP:
                targets_noop += 1
            elif entry["status"] == _STATUS_DRIFT:
                targets_drift += 1
            elif entry["status"] == _STATUS_UNREGISTERED:
                unregistered += 1

    return {
        "apps": apps,
        "_stats": {
            "apps_scanned": len(inventory.apps),
            "hooks_scanned": hooks_scanned,
            "targets_missing": targets_missing,
            "targets_noop": targets_noop,
            "targets_drift": targets_drift,
            "classes_scanned": classes_scanned,
            "unregistered_classes": unregistered,
        },
    }


def build_findings(scan: dict[str, Any]) -> list[Finding]:
    """Turn the dead-hook scan into envelope findings."""
    findings: list[Finding] = []
    for app_name, entries in sorted(scan.get("apps", {}).items()):
        for entry in entries:
            evidence = dict(entry["evidence"])
            evidence["app"] = app_name
            findings.append(
                Finding(
                    id=f"integrity-{CHECK_ID}-{app_name}-{entry['kind']}-{entry['slug']}",
                    title=entry["title"],
                    severity=entry["severity"],
                    description=entry["description"],
                    app=app_name,
                    evidence=evidence,
                )
            )
    return findings


def check_dead_hook_target(inventory: Inventory) -> CheckResult:
    """Check entry point."""
    scan = scan_dead_hook_targets(inventory)
    return CheckResult(
        check_id=CHECK_ID,
        findings=build_findings(scan),
        stats=scan["_stats"],
    )


CHECK_SPEC = CheckSpec(
    check_id=CHECK_ID,
    title="Hooks that point at missing or no-op code",
    description=(
        "Detect hooks (doc_events, scheduler_events, override_whitelisted_methods, "
        "has_website_permission, override_doctype_class) whose target does not "
        "exist, plus Document subclasses nothing ever references."
    ),
    fn=check_dead_hook_target,
)
