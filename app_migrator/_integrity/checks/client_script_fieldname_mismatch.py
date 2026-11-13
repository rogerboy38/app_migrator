"""Check: a client script listens on a fieldname the DocType does not have.

Why this check exists
---------------------
Audit / review evidence (2026-11-05): a client script listened on
``sap_movement_type`` while the real field is ``custom_sap_movement_type``.
The handler never fires and the UI shows no error, so the bug is invisible
until someone reports that the button does nothing.

This is the silent sibling of the ``missing-field-reference`` check: a Python
read of an absent field raises ``AttributeError`` (loud, but only when the
branch runs), while a client script bound to an absent field does *nothing*
and says *nothing*.

What is reported
----------------
One finding per (app, DocType, fieldname): the client script references a
fieldname the DocType does not have. Every location is listed, because one
broken script usually means several places listen on the same wrong name.

Severity is ``medium``: the handler simply never fires, so the feature is
dead rather than the data being wrong. Every finding carries a ``suggestions``
list -- the known fieldnames within edit distance 3 of the reference -- so
``sap_movement_type`` points at ``custom_sap_movement_type`` without a human
having to guess.

False positives are the enemy here
----------------------------------
A client script can legitimately reference a field that this app does not
ship in its DocType JSON: the field may have been added by another app's
Custom Field, by a patch, or by a site-level ``Customize Form``. The known
field set is therefore widened with

- the Custom Fields **any** app in the bench ships for that DocType, and
- a curated list of standard Frappe / ERPNext field names,

and JS-only pseudo-fields (``frm.doc.__islocal`` and friends) are skipped
outright. What survives that is worth a human's time.
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterable
from typing import Any

from ..base import CheckResult, CheckSpec, Finding
from ..context import AppInfo, Inventory, read_text

CHECK_ID = "client-script-fieldname-mismatch"

# The reference forms a client script uses to touch a field by name.
_REFERENCE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("frm.fields", re.compile(r"\bfrm\.fields\.([A-Za-z_][A-Za-z0-9_]*)")),
    ("frm.doc", re.compile(r"\bfrm\.doc\.([A-Za-z_][A-Za-z0-9_]*)")),
    ("frm.set_value", re.compile(r"\bfrm\.set_value\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]")),
    ("frm.toggle", re.compile(r"\bfrm\.toggle\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]")),
    ("frm.get_value", re.compile(r"\bfrm\.get_value\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]")),
    (
        "frm.script_manager.trigger",
        re.compile(r"\bfrm\.script_manager\.trigger\(\s*['\"]([A-Za-z_][A-Za-z0-9_]*)['\"]"),
    ),
)

# Pseudo-fields that exist on a document in the browser but are not DocType
# fields. They must never be reported.
JS_ONLY_FIELDS: set[str] = {
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
    "__islocal",
    "__unsaved",
    "__view",
    "__runnable",
}

# Standard Frappe / ERPNext field names. A DocType JSON lists the fields the
# app ships, but a site can carry more than that (a Custom Field added by
# another app, a patch, a site-level Customize Form). Naming a standard field
# is therefore not, by itself, a defect.
STANDARD_FIELDS: set[str] = {
    # -- core document columns --------------------------------------------
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
    "naming_series",
    "title",
    "disabled",
    "language",
    "status",
    "remarks",
    "flags",
    "meta",
    # -- common ERPNext transaction fields --------------------------------
    "company",
    "currency",
    "cost_center",
    "account",
    "party",
    "party_type",
    "customer",
    "supplier",
    "customer_group",
    "supplier_group",
    "item_group",
    "territory",
    "sales_person",
    "project",
    "department",
    "posting_date",
    "posting_time",
    "due_date",
    "schedule_date",
    "reference_type",
    "reference_name",
    "against",
    "against_type",
    "so_reference",
    "po_reference",
    "mode_of_payment",
    "payment_reference",
    "total_amount",
    "net_total",
    "grand_total",
    "paid_amount",
    "balance",
    "taxes_and_charges",
    "apply_tds",
    "warehouse",
    "s_warehouse",
    "t_warehouse",
    "batch_no",
    "serial_no",
    "item_code",
    "item_name",
    "description",
    "qty",
    "rate",
    "amount",
    "uom",
    "stock_uom",
    "conversion_factor",
    "base_rate",
    "discount_percentage",
    "price_list",
    "contact",
    "email",
    "mobile_no",
    "phone",
    "address",
    "city",
    "state",
    "country",
    "postal_code",
    "gstin",
    "pan",
    "ifsc_code",
    "bank_account_no",
}

# The Document / BaseDocument API surface, as seen from the browser. These are
# methods on ``frm.doc``, not fields, so they are never reported.
DOCUMENT_API: set[str] = {
    "save",
    "insert",
    "delete",
    "reload",
    "submit",
    "cancel",
    "set",
    "get",
    "get_value",
    "get_formatted",
    "get_valid_dict",
    "get_table_fieldname",
    "get_title",
    "get_label",
    "get_url",
    "get_url_to_form",
    "get_all_children",
    "get_transactions",
    "get_prev",
    "get_next",
    "get_default",
    "get_count",
    "get_meta",
    "get_system_settings",
    "get_value_from",
    "get_doc_before_save",
    "get_latest",
    "get_onload",
    "get_doc",
    "as_dict",
    "as_dict_no_nulls",
    "cast",
    "db_set",
    "db_insert",
    "db_update",
    "db_set_all",
    "db_get_value",
    "run_method",
    "append",
    "remove",
    "has_value_changed",
    "is_new",
    "check_permission",
    "has_permission",
    "notify_update",
    "set_onload",
    "save_ignore_permissions",
    "load_doc",
    "precision",
    "amended_from",
    "website",
}

# Maximum number of near-miss fieldnames reported as suggestions.
MAX_SUGGESTIONS = 5

# Maximum edit distance for a suggestion.
SUGGESTION_DISTANCE = 3


def _scrub(name: str) -> str:
    """Frappe's folder slug for a DocType name (``Movement Type`` -> ``movement_type``)."""
    return name.lower().replace(" ", "_").replace("-", "_")


def _levenshtein(left: str, right: str) -> int:
    """Character-level edit distance between two strings."""
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, lchar in enumerate(left, 1):
        current = [i]
        for j, rchar in enumerate(right, 1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (lchar != rchar),
                )
            )
        previous = current
    return previous[-1]


def _token_distance(left: str, right: str) -> int:
    """Edit distance between two fieldnames measured in ``_``-separated words.

    Field names are word-like, so ``custom_sap_movement_type`` is one word
    away from ``sap_movement_type`` -- which is exactly the shape of the
    defect the audit found.
    """
    return _levenshtein(" ".join(left.split("_")), " ".join(right.split("_")))


def _strip_custom_prefix(name: str) -> str:
    """Drop Frappe's ``custom_`` prefix from a fieldname.

    A custom field named ``custom_x`` is the same field as ``x`` renamed to
    avoid a clash, and that rename is exactly how the audited defect was
    introduced.
    """
    prefix = "custom_"
    if name.startswith(prefix) and len(name) > len(prefix):
        return name[len(prefix) :]
    return name


def _distance(left: str, right: str) -> int:
    """The closer of the character-level and word-level edit distances.

    The word-level measure is what connects ``sap_movement_type`` to
    ``custom_sap_movement_type``; the character-level measure catches plain
    typos such as ``sap_movment_type``.
    """
    direct = _levenshtein(left, right)
    stripped = _levenshtein(
        _strip_custom_prefix(left), _strip_custom_prefix(right)
    )
    return min(direct, stripped)


def _suggestions(reference: str, known: Iterable[str]) -> list[str]:
    """Known fieldnames within edit distance 3 of ``reference``, closest first."""
    scored: list[tuple[int, str]] = []
    for candidate in known:
        distance = _distance(reference, candidate)
        if distance <= SUGGESTION_DISTANCE:
            scored.append((distance, candidate))
    scored.sort()
    return [name for _distance, name in scored[:MAX_SUGGESTIONS]]


def _js_files(app: AppInfo) -> list[str]:
    """Every ``.js`` file under the app's ``public/js`` tree.

    Frappe apps ship client scripts either inside the Python package
    (``<app>/<app>/public/js/`` — what all three audited apps do) or at the
    app root (``<app>/public/js/``). Both are scanned.
    """
    found: list[str] = []
    for base in (app.package, app.root):
        root = os.path.join(base, "public", "js")
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in ("node_modules", "__pycache__"))
            for filename in sorted(filenames):
                if filename.endswith(".js"):
                    found.append(os.path.join(dirpath, filename))
    # The same file can be reachable through both bases in a nested layout.
    unique: list[str] = []
    seen = set()
    for path in sorted(found):
        real = os.path.abspath(path)
        if real in seen:
            continue
        seen.add(real)
        unique.append(path)
    return unique


def _js_relative_parts(app: AppInfo, path: str) -> list[str]:
    """Path of a JS file relative to the ``public/js`` tree that holds it.

    The tree may live inside the Python package (``<app>/<app>/public/js/``)
    or at the app root (``<app>/public/js/``); both are tried.
    """
    for base in (app.package, app.root):
        js_root = os.path.join(base, "public", "js")
        rel = os.path.relpath(path, js_root).replace(os.sep, "/")
        if not rel.startswith(".."):
            return rel.split("/")
    return []


def _doctype_for_slug(app: AppInfo, slug: str) -> str | None:
    """The DocType a ``public/js/<slug>/`` folder belongs to.

    The slug is matched against the DocTypes the app ships: exactly, then
    case-insensitively, then with ``_`` read as a space.
    """
    paths = app.doctype_json_paths()
    if slug in paths:
        return slug
    lowered = slug.lower()
    for name in paths:
        if name.lower() == lowered:
            return name
    spaced = lowered.replace("_", " ")
    for name in paths:
        if name.lower() == spaced:
            return name
    return None


def _slug_for_doctype(app: AppInfo, doctype: str) -> str:
    """The stable folder slug used in finding ids for ``doctype``."""
    json_path = app.doctype_json_paths().get(doctype)
    if json_path:
        return os.path.basename(os.path.dirname(json_path))
    return _scrub(doctype)


def _references(source: str) -> list[tuple[str, str, int]]:
    """``(reference form, fieldname, line)`` for every field reference found."""
    found: list[tuple[str, str, int]] = []
    for form, pattern in _REFERENCE_PATTERNS:
        for match in pattern.finditer(source):
            line = source.count("\n", 0, match.start()) + 1
            found.append((form, match.group(1), line))
    return found


def _custom_fields_for_doctype(inventory: Inventory, doctype: str) -> set[str]:
    """Custom Field names shipped by *any* app for ``doctype``.

    A field another app adds to this DocType exists at runtime, so a script
    referring to it is correct. Judging only against the owning app would
    report it as a mismatch -- a false positive.
    """
    names: set[str] = set()
    lowered = doctype.lower()
    for app in inventory.apps:
        for record in app.custom_fields():
            dt = record.get("dt")
            fieldname = record.get("fieldname")
            if isinstance(dt, str) and dt.lower() == lowered and isinstance(fieldname, str):
                names.add(fieldname)
    return names


def scan_client_script_mismatches(inventory: Inventory) -> dict[str, Any]:
    """Find every client-script field reference the DocType does not have.

    Returns a dict with a ``mismatches`` map keyed by
    ``<app>|<doctype>|<fieldname>`` and a ``_stats`` counter block.
    """
    mismatches: dict[str, dict[str, Any]] = {}
    js_files_scanned = 0
    files_skipped = 0
    references_scanned = 0

    for app in inventory.apps:
        known_cache: dict[str, set[str]] = {}
        for path in _js_files(app):
            js_files_scanned += 1
            parts = _js_relative_parts(app, path)
            if not parts:
                files_skipped += 1
                continue
            if len(parts) >= 2:
                # ``public/js/<doctype_slug>/<file>.js`` — the folder names
                # the DocType.
                slug = parts[0]
            else:
                # ``public/js/<doctype_slug>.js`` — a flat file named after
                # the DocType (Frappe's ``doctype_js`` convention). All three
                # audited apps ship their client scripts flat, so resolving
                # only the folder form would skip every file.
                slug = os.path.splitext(parts[0])[0]
            doctype = _doctype_for_slug(app, slug)
            if doctype is None:
                files_skipped += 1
                continue
            source = read_text(path)
            if not source.strip():
                continue
            if doctype not in known_cache:
                known_cache[doctype] = (
                    app.fieldnames_for(doctype)
                    | _custom_fields_for_doctype(inventory, doctype)
                    | STANDARD_FIELDS
                )
            known = known_cache[doctype]
            rel_file = os.path.relpath(path, app.root).replace(os.sep, "/")
            for form, fieldname, line in _references(source):
                references_scanned += 1
                if fieldname.startswith("_"):
                    continue
                if fieldname in JS_ONLY_FIELDS:
                    continue
                if fieldname in known:
                    continue
                key = f"{app.name}|{doctype}|{fieldname}"
                entry = mismatches.get(key)
                if entry is None:
                    entry = {
                        "app": app.name,
                        "doctype": doctype,
                        "doctype_slug": _slug_for_doctype(app, doctype),
                        "fieldname": fieldname,
                        "locations": [],
                        "suggestions": _suggestions(fieldname, known),
                        "known_fields_count": len(known),
                    }
                    mismatches[key] = entry
                location = {"file": rel_file, "line": line, "reference": form}
                if location not in entry["locations"]:
                    entry["locations"].append(location)

    stats = {
        "apps_scanned": len(inventory.apps),
        "js_files_scanned": js_files_scanned,
        "js_files_skipped": files_skipped,
        "field_references_scanned": references_scanned,
        "mismatched_fieldnames": len(mismatches),
    }
    return {"mismatches": mismatches, "_stats": stats}


def build_findings(scan: dict[str, Any]) -> list[Finding]:
    """Turn the client-script scan into envelope findings."""
    findings: list[Finding] = []
    for _key, info in sorted(scan.get("mismatches", {}).items()):
        locations = info["locations"]
        where = ", ".join(f"{loc['file']}:{loc['line']}" for loc in locations)
        suggestions = info["suggestions"]
        hint = ""
        if suggestions:
            hint = f" Did you mean {', '.join(suggestions)}?"
        findings.append(
            Finding(
                id=(
                    f"integrity-{CHECK_ID}-{info['app']}-"
                    f"{info['doctype_slug']}-{info['fieldname']}"
                ),
                title=(
                    f"Client script for {info['doctype']} uses field "
                    f"'{info['fieldname']}', which the DocType does not have"
                ),
                severity="medium",
                description=(
                    f"The client script for {info['doctype']} listens on "
                    f"'{info['fieldname']}' ({where}), but that DocType has no such "
                    f"field ({info['known_fields_count']} field(s) known). The handler "
                    f"never fires and the UI shows no error, so the feature is silently "
                    f"dead.{hint}"
                ),
                app=info["app"],
                evidence={
                    "app": info["app"],
                    "doctype": info["doctype"],
                    "fieldname": info["fieldname"],
                    "locations": locations,
                    "suggestions": suggestions,
                    "known_fields_count": info["known_fields_count"],
                },
            )
        )
    return findings


def check_client_script_fieldname_mismatch(inventory: Inventory) -> CheckResult:
    """Check entry point."""
    scan = scan_client_script_mismatches(inventory)
    return CheckResult(
        check_id=CHECK_ID,
        findings=build_findings(scan),
        stats=scan["_stats"],
    )


CHECK_SPEC = CheckSpec(
    check_id=CHECK_ID,
    title="Client script bound to a fieldname the DocType does not have",
    description=(
        "Detect client scripts that listen on a fieldname the DocType does not "
        "ship, so the handler never fires and nothing is reported."
    ),
    fn=check_client_script_fieldname_mismatch,
)
