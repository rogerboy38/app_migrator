"""Check: a controller reads a field that its DocType does not have.

Why this check exists
---------------------
Audit evidence (``rnd_warehouse_management``, 2026-11-05): the Stock Entry
controller reads ``sap_movement_code`` and ``requires_dual_signature`` off a
``Movement Type`` document, but **neither field exists** on the ``Movement
Type`` DocType -- its fields are ``movement_code``, ``sap_equivalent``,
``purpose``, ``default_stock_entry_type``, ... . The defect survived for
months precisely because the code was never executed: nothing raised, so
nothing looked broken.

What is reported
----------------
One finding per (app, DocType, fieldname): the field is read, the DocType
does not ship it, so the read raises ``AttributeError`` the first time that
branch runs. Severity is ``medium`` -- a missing field fails loudly at
runtime rather than silently corrupting data, but it only fails when the
branch is reached, which is exactly why it went unnoticed.

The DocType named in the finding is **the DocType the read is about**:

- ``self.<field>`` in a DocType controller -> that controller's DocType;
- ``doc.<field>`` -> the DocType ``doc`` was loaded from, when the code says
  so (``doc = frappe.get_doc("Movement Type", ...)``), otherwise the
  controller's own DocType;
- ``<something>_doc.<field>`` -> the DocType named by the variable, when the
  app ships it (``movement_type_doc`` -> ``Movement Type``).

A read on a document whose DocType the app does not ship is skipped: its
field set is unknown, so nothing can be said about it.

False positives are the enemy here: a check that cries wolf trains people to
ignore it. The analysis is therefore deliberately narrow:

- only DocType controller files (``<package>/doctype/<slug>/<slug>.py``) are read;
- only *reads* (``ast.Load``) count -- writing to an unknown attribute is not
  an ``AttributeError``;
- the Document / BaseDocument API surface is excluded by name;
- a name the controller defines itself (method, property or class attribute)
  is code, not a field, and is excluded;
- a name the controller assigns on the document is an instance attribute, not
  a field, and is excluded;
- names starting with ``_`` are private, not fields;
- a field another app ships as a Custom Field for the same DocType counts as
  known, because it exists at runtime.
"""
from __future__ import annotations

import ast
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from ..base import CheckResult, CheckSpec, Finding
from ..context import AppInfo, Inventory, iter_python_files, parse_python

CHECK_ID = "missing-field-reference"

# The Document / BaseDocument API surface that shows up on ``self`` / ``doc``
# but is NOT a DocType field. A missing *field* raises AttributeError; a
# missing *method* raises it too, but that is a different bug class (and the
# framework surfaces it immediately), so it is not this check's job.
BASE_DOCUMENT_API: Set[str] = {
    # -- persistence ------------------------------------------------------
    "save",
    "insert",
    "delete",
    "reload",
    "submit",
    "cancel",
    "db_set",
    "db_insert",
    "db_update",
    "db_set_all",
    "db_get_value",
    "save_ignore_permissions",
    "load_doc",
    "get_latest",
    "get_doc_before_save",
    # -- generic document API ---------------------------------------------
    "get",
    "set",
    "get_value",
    "get_value_from",
    "get_formatted",
    "get_valid_dict",
    "get_table_fieldname",
    "get_count",
    "get_meta",
    "get_system_settings",
    "get_title",
    "get_label",
    "get_url",
    "get_url_to_form",
    "get_all_children",
    "get_transactions",
    "get_default",
    "as_dict",
    "as_dict_no_nulls",
    "cast",
    "get_prev",
    "get_next",
    "has_value_changed",
    "is_new",
    "run_method",
    "append",
    "remove",
    "check_permission",
    "has_permission",
    "notify_update",
    "set_onload",
    "get_onload",
    # -- standard columns every document carries --------------------------
    "doctype",
    "name",
    "owner",
    "creation",
    "modified",
    "modified_by",
    "docstatus",
    "idx",
    "parent",
    "parenttype",
    "parentfield",
    "flags",
    "meta",
    "precision",
    "status",
    "amended_from",
    # -- controller hooks (methods, not fields) ---------------------------
    "validate",
    "before_save",
    "on_update",
    "on_update_after_submit",
    "before_insert",
    "on_trash",
    "after_insert",
    "after_delete",
    "on_submit",
    "on_cancel",
    "before_rename",
    "after_rename",
    "before_cancel",
    "update_after_submit",
    # -- internals --------------------------------------------------------
    "_meta",
    "_doc_before_save",
}

_NON_WORD = re.compile(r"[^a-z0-9]")

# Binding sentinels for a local name.
_SELF = "\x00self"       # bound to the controller's own document
_UNKNOWN = "\x00unknown"  # bound to a document of an unknown DocType


def _scrub(name: str) -> str:
    """Frappe's folder slug for a DocType name (``Movement Type`` -> ``movement_type``)."""
    return name.lower().replace(" ", "_").replace("-", "_")


def _normalise(name: str) -> str:
    """Loose comparison key for a DocType name (``Stock Entry`` -> ``stockentry``)."""
    return _NON_WORD.sub("", name.lower())


def _controller_slug(app: AppInfo, path: str) -> Optional[str]:
    """Return the DocType slug when ``path`` is a ``doctype/<slug>/<slug>.py`` file.

    Only the DocType controller itself is analysed: helper modules, test files
    and ``__init__.py`` are not controllers and are skipped.

    The three trailing path segments are what identify a controller, not the
    directory they sit in. Frappe apps are not consistent about that: the
    audited ``amb_w_tds`` and ``rnd_warehouse_management`` both use a doubly
    nested package, so their controllers live at
    ``<app>/<app>/<app>/doctype/<slug>/<slug>.py`` rather than
    ``<app>/<app>/doctype/<slug>/<slug>.py``. Matching only the exact
    three-segment shape silently matched **zero** controllers on those apps.
    """
    rel = os.path.relpath(path, app.package).replace(os.sep, "/")
    parts = rel.split("/")
    if len(parts) < 3:
        return None
    slug = parts[-2]
    if parts[-3] != "doctype":
        return None
    if parts[-1] != f"{slug}.py":
        return None
    return slug


def _resolve_doctype(app: AppInfo, slug: str) -> Optional[str]:
    """The DocType the folder ``slug`` belongs to (None when the app does not ship it)."""
    paths = app.doctype_json_paths()
    for name, json_path in paths.items():
        if os.path.basename(os.path.dirname(json_path)) == slug:
            return name
    for name in paths:
        if _scrub(name) == slug.lower():
            return name
    return None


def _slug_for_doctype(app: AppInfo, doctype: str) -> str:
    """The stable folder slug used in finding ids for ``doctype``."""
    json_path = app.doctype_json_paths().get(doctype)
    if json_path:
        return os.path.basename(os.path.dirname(json_path))
    return _scrub(doctype)


def _doctype_for_variable(app: AppInfo, base_name: str) -> Optional[str]:
    """Resolve a ``<something>_doc`` variable name to a DocType the app ships.

    ``movement_type_doc`` is the Frappe convention for "a Movement Type
    document". When the app ships that DocType we know which field set the
    variable belongs to; when it does not, the variable cannot be judged and
    the read is skipped.
    """
    if not base_name.endswith("_doc") or len(base_name) <= len("_doc"):
        return None
    target = base_name[: -len("_doc")].lower()
    for name in app.doctype_json_paths():
        lowered = name.lower()
        if lowered == target or lowered.replace(" ", "_") == target or _scrub(lowered) == target:
            return name
    return None


def _binding_for(value: ast.AST) -> str:
    """What a local name is bound to, as far as the code says.

    ``self`` -> the controller's own document; ``frappe.get_doc("X", ...)`` ->
    an ``X`` document; anything else -> an unknown document.
    """
    if isinstance(value, ast.Name) and value.id == "self":
        return _SELF
    if isinstance(value, ast.Call):
        func = value.func
        if isinstance(func, ast.Attribute) and func.attr in (
            "get_doc",
            "get_last_doc",
            "new_doc",
        ):
            if value.args:
                first = value.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    return first.value
    return _UNKNOWN


class _Scope:
    """One lexical scope: a module, a class body or a function body."""

    def __init__(self, parent: Optional["_Scope"] = None) -> None:
        self.parent = parent
        self.bindings: Dict[str, str] = {}

    def lookup(self, name: str) -> Optional[str]:
        scope: Optional[_Scope] = self
        while scope is not None:
            if name in scope.bindings:
                return scope.bindings[name]
            scope = scope.parent
        return None


class _ReadCollector(ast.NodeVisitor):
    """Collect ``base.attribute`` reads with their scope and enclosing class."""

    def __init__(self) -> None:
        # (scope, enclosing class name, is nested class, base name, attr, line)
        self.reads: List[Tuple[_Scope, Optional[str], bool, str, str, int]] = []
        self._scope = _Scope()
        self._classes: List[str] = []

    # -- scopes -----------------------------------------------------------
    def _push_scope(self) -> None:
        self._scope = _Scope(self._scope)

    def _pop_scope(self) -> None:
        assert self._scope.parent is not None
        self._scope = self._scope.parent

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._classes.append(node.name)
        self._push_scope()
        self.generic_visit(node)
        self._pop_scope()
        self._classes.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._push_scope()
        self.generic_visit(node)
        self._pop_scope()

    visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

    def visit_Assign(self, node: ast.Assign) -> None:
        binding = _binding_for(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._scope.bindings[target.id] = binding
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if node.value is not None and isinstance(node.target, ast.Name):
            self._scope.bindings[node.target.id] = _binding_for(node.value)
        self.generic_visit(node)

    # -- reads ------------------------------------------------------------
    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.ctx, ast.Load) and isinstance(node.value, ast.Name):
            enclosing = self._classes[-1] if self._classes else None
            nested = len(self._classes) > 1
            self.reads.append((self._scope, enclosing, nested, node.value.id, node.attr, node.lineno))
        self.generic_visit(node)


def _class_defined_names(tree: ast.Module) -> Set[str]:
    """Names the controller file defines itself (methods, properties, attributes).

    Those are code, not DocType fields, so ``self.some_helper`` must never be
    reported.
    """
    names: Set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add(stmt.name)
            elif isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        names.add(target.id)
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                names.add(stmt.target.id)
    return names


def _assigned_attributes(tree: ast.Module) -> Dict[str, Set[str]]:
    """Map ``base name`` -> attribute names assigned on it in this file.

    ``self.cache = {}`` creates an instance attribute, not a field, so a later
    ``self.cache`` read must not be reported.
    """
    assigned: Dict[str, Set[str]] = {}
    targets: List[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets.extend(node.targets)
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets.append(node.target)
    for target in targets:
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
            assigned.setdefault(target.value.id, set()).add(target.attr)
    return assigned


def _controller_class_names(tree: ast.Module, doctype: str) -> Set[str]:
    """The classes in ``tree`` that model ``doctype``.

    Frappe names a controller class after the DocType (``Movement Type`` ->
    ``MovementType``). When no class matches, the Document-derived classes are
    used; failing that, every class in the file.
    """
    wanted = _normalise(doctype)
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    matched = {node.name for node in classes if _normalise(node.name) == wanted}
    if matched:
        return matched
    derived = set()
    for node in classes:
        for base in node.bases:
            base_name = base.id if isinstance(base, ast.Name) else None
            if base_name and base_name.endswith("Document"):
                derived.add(node.name)
    if derived:
        return derived
    return {node.name for node in classes}


def _custom_fields_for_doctype(inventory: Inventory, doctype: str) -> Set[str]:
    """Custom Field names shipped by *any* app for ``doctype``.

    A field another app adds to this DocType exists at runtime, so reading it
    does not raise. Judging only against the owning app would report it as
    missing -- a false positive.
    """
    names: Set[str] = set()
    lowered = doctype.lower()
    for app in inventory.apps:
        for record in app.custom_fields():
            dt = record.get("dt")
            fieldname = record.get("fieldname")
            if isinstance(dt, str) and dt.lower() == lowered and isinstance(fieldname, str):
                names.add(fieldname)
    return names


def scan_missing_field_references(inventory: Inventory) -> Dict[str, Any]:
    """Find every field read whose DocType does not define that field.

    Returns a dict with a ``missing`` map keyed by
    ``<app>|<doctype>|<fieldname>`` and a ``_stats`` counter block.
    """
    missing: Dict[str, Dict[str, Any]] = {}
    controllers_scanned = 0
    references_scanned = 0
    known_cache: Dict[str, Set[str]] = {}

    def known_fields(app: AppInfo, doctype: str) -> Set[str]:
        key = f"{app.name}|{doctype}"
        if key not in known_cache:
            known_cache[key] = app.fieldnames_for(doctype) | _custom_fields_for_doctype(
                inventory, doctype
            )
        return known_cache[key]

    for app in inventory.apps:
        for path in iter_python_files(app.package):
            slug = _controller_slug(app, path)
            if slug is None:
                continue
            controllers_scanned += 1
            doctype = _resolve_doctype(app, slug)
            tree = parse_python(path)
            if doctype is None or tree is None:
                continue
            assigned = _assigned_attributes(tree)
            defined = _class_defined_names(tree)
            controller_classes = _controller_class_names(tree, doctype)
            collector = _ReadCollector()
            collector.visit(tree)
            for scope, enclosing, nested, base_name, attr, lineno in collector.reads:
                references_scanned += 1
                if attr.startswith("_"):
                    continue
                if attr in BASE_DOCUMENT_API:
                    continue
                if attr in defined:
                    continue
                if attr in assigned.get(base_name, set()):
                    continue
                if base_name == "self":
                    # ``self`` inside a helper class is not the document.
                    if nested:
                        continue
                    if enclosing is not None and enclosing not in controller_classes:
                        continue
                    target = doctype
                elif base_name == "doc":
                    binding = scope.lookup(base_name)
                    if binding is None:
                        target = doctype
                    elif binding == _SELF:
                        target = doctype
                    elif binding == _UNKNOWN:
                        # A document, but of a DocType we cannot name.
                        continue
                    else:
                        target = _resolve_doctype(app, _scrub(binding))
                        if target is None:
                            # Another DocType whose fields we do not know.
                            continue
                else:
                    target = _doctype_for_variable(app, base_name)
                    if target is None:
                        continue
                if attr in known_fields(app, target):
                    continue
                key = f"{app.name}|{target}|{attr}"
                if key in missing:
                    continue
                missing[key] = {
                    "app": app.name,
                    "doctype": target,
                    "doctype_slug": _slug_for_doctype(app, target),
                    "fieldname": attr,
                    "file": os.path.relpath(path, app.root).replace(os.sep, "/"),
                    "line": lineno,
                    "known_fields_count": len(known_fields(app, target)),
                }

    stats = {
        "apps_scanned": len(inventory.apps),
        "controllers_scanned": controllers_scanned,
        "field_references_scanned": references_scanned,
        "missing_field_references": len(missing),
    }
    return {"missing": missing, "_stats": stats}


def build_findings(scan: Dict[str, Any]) -> List[Finding]:
    """Turn the missing-field scan into envelope findings."""
    findings: List[Finding] = []
    for _key, info in sorted(scan.get("missing", {}).items()):
        findings.append(
            Finding(
                id=(
                    f"integrity-{CHECK_ID}-{info['app']}-"
                    f"{info['doctype_slug']}-{info['fieldname']}"
                ),
                title=(
                    f"{info['doctype']}.{info['fieldname']} is read but the "
                    f"DocType does not define it"
                ),
                severity="medium",
                description=(
                    f"{info['app']}'s {info['doctype']} controller reads "
                    f"'{info['fieldname']}' ({info['file']}:{info['line']}), but the "
                    f"DocType does not define that field "
                    f"({info['known_fields_count']} field(s) known). The read raises "
                    f"AttributeError the first time that branch runs; because nothing "
                    f"exercises the branch today, the defect stays invisible until "
                    f"production hits it."
                ),
                app=info["app"],
                evidence={
                    "app": info["app"],
                    "doctype": info["doctype"],
                    "fieldname": info["fieldname"],
                    "file": info["file"],
                    "line": info["line"],
                    "known_fields_count": info["known_fields_count"],
                },
            )
        )
    return findings


def check_missing_field_reference(inventory: Inventory) -> CheckResult:
    """Check entry point."""
    scan = scan_missing_field_references(inventory)
    return CheckResult(
        check_id=CHECK_ID,
        findings=build_findings(scan),
        stats=scan["_stats"],
    )


CHECK_SPEC = CheckSpec(
    check_id=CHECK_ID,
    title="Field read that the DocType does not define",
    description=(
        "Detect controller code that reads a field the DocType does not ship, "
        "so the read raises AttributeError as soon as that branch runs."
    ),
    fn=check_missing_field_reference,
)
