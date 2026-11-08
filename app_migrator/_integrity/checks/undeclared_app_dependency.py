"""Check: an app points at a DocType it never declared a dependency on.

Why this check exists
---------------------
Audit evidence (``amb_w_tds``, 2026-11-05):

- ``amb_w_tds``'s ``hooks.py`` has **no** ``required_apps`` at all.
- Yet **13** Link / Table fields in its DocTypes point at four DocTypes that
  exist only in ``amb_w_spc``: ``Batch AMB`` (x8), ``Parameter Group
  Substrate`` (x2), ``SPC Batch Parameter`` (x2) and ``SPC Specification``
  (x1).
- Installing ``amb_w_tds`` on its own therefore leaves broken links: the
  target DocTypes are not on the site at all.

Why it matters
--------------
Frappe never validates a Link field's target against the installed apps. The
field syncs happily, the migrate succeeds, and the breakage only shows up
later as a broken link (or a ``LinkValidationError``) in the UI. Declaring the
dependency in ``required_apps`` is what makes the bench refuse to install the
app without it — so an *undeclared* dependency is a defect that no tool
currently reports.

What is reported
----------------
One finding per (app, target DocType) pair — not per field — with every
affected field listed in the evidence, because "13 fields point at
``Batch AMB``" is one defect, not thirteen:

- the target DocType is a **standard** Frappe / ERPNext DocType -> nothing
  is reported at all. A scan root that does not contain ``frappe`` /
  ``erpnext`` cannot ship ``Customer`` or ``Item``, so "no app ships it"
  says nothing about those DocTypes;
- the target DocType is shipped by **no** installed app and is not standard
  -> ``high`` when the scan root does contain ``frappe`` / ``erpnext`` (the
  link can never work), and ``info`` when it does not (the scan root is
  incomplete, so the target may be a standard DocType that is simply not
  in the tree);
- the target DocType is shipped by another app that is **not** in the
  consuming app's ``required_apps`` -> ``medium`` (the dependency is
  implicit and breaks when that app is not installed).

Targets the app ships itself are ignored: that is the normal case. When
``required_apps`` is built at runtime it cannot be judged statically, so the
app is left alone rather than reported.

Why the standard list matters
-----------------------------
The audited scan tree (``amb_w_tds`` + ``amb_w_spc`` +
``rnd_warehouse_management``, no ``frappe`` / ``erpnext``) reported **67**
"no installed app ships DocType 'X'" findings across **45** distinct target
names. **41** of those 45 were standard core DocTypes — ``Item``,
``Customer``, ``Batch``, ``Workflow`` … — so the check was reporting the
*absence of the framework* as 67 defects.

The other 4 were not core, and each needed a different answer:

- ``spc_batch_record``, ``spc_deviation`` and ``spc_electronic_signature``
  **are** shipped — by ``amb_w_spc``, at ``fda_compliance/doctype/<slug>/``.
  A Link field's ``options`` carries the folder slug while the DocType's
  JSON carries the display name (``SPC Deviation``), so the inventory has
  to match on the slug as well; that was a second, separate defect.
- ``AMB Cost Factors`` is genuinely not shipped by any app in the tree.
  ``amb_w_tds`` links to it *and* ships fixtures for it, so it is a real
  lead — but the scan root has no ``frappe`` / ``erpnext``, so it cannot be
  called a defect. It is reported as ``info``.

What remains after both fixes are the **8** real ``medium`` findings: the
cross-app dependencies that neither app declares.
"""
from __future__ import annotations

import re
from typing import Any

from ..base import CheckResult, CheckSpec, Finding
from ..context import AppInfo, Inventory, read_json

CHECK_ID = "undeclared-app-dependency"

# Field types whose ``options`` names another DocType.
_LINK_FIELDTYPES = ("Link", "Table")

# Scan outcome for one (app, target DocType) pair.
_OWN = "own"                # the app ships the target itself — normal
_DECLARED = "declared"      # the owner app is declared in required_apps
_UNDECLARED = "undeclared"  # the owner app is NOT declared in required_apps
_MISSING = "missing"        # no installed app ships the target
_UNKNOWN = "unknown"        # required_apps is built at runtime — cannot judge
_STANDARD = "standard"      # the target is a standard frappe/erpnext DocType

# The apps that ship the standard DocTypes. When neither of them is in the
# scan root, the scan root is incomplete: an unresolved target may simply be
# a core DocType that is not in the tree, so it cannot be called a defect.
CORE_APP_NAMES = frozenset({"frappe", "erpnext"})

# --------------------------------------------------------------------------
# Standard Frappe / ERPNext DocTypes.
#
# VERSIONED / APPROXIMATE — read this before editing the list.
#
# This is a hand-maintained snapshot of the DocType names that ``frappe`` and
# ``erpnext`` ship (roughly the Frappe v14 / ERPNext v14 era). It is **not**
# authoritative and it **will drift**:
#
# - the framework adds and renames DocTypes between releases, so a name that
#   is missing here produces a finding that is not a defect;
# - conversely, a name that is present here silences a finding even if a
#   custom app happens to ship a DocType with the same name — a custom app
#   shadowing a core DocType name is a separate (rare) defect that this
#   check deliberately does not report.
#
# It is a *suppression* list, so it is deliberately generous: the cost of a
# name in the list is one suppressed finding, the cost of a name outside it
# is one noisy finding. When in doubt, prefer adding the name.
#
# Seeded from the 2026-11-05 audit of the ``amb_w_tds`` scan tree (the 45
# distinct DocTypes that produced 67 bogus "no installed app ships DocType"
# findings) plus the obvious core Frappe / ERPNext DocTypes.
# --------------------------------------------------------------------------
STANDARD_DOCTYPES = frozenset({
    # -- Frappe core ------------------------------------------------------
    "Access Log",
    "Audit Log",
    "Comment",
    "Communication",
    "Custom Field",
    "Dashboard Chart",
    "DocPerm",
    "DocType",
    "Error Log",
    "File",
    "Has Role",
    "Module Def",
    "Note",
    "Notification",
    "Patch Log",
    "Personal Note",
    "Personal Tag",
    "Print Format",
    "Property Setter",
    "Report",
    "Role",
    "Scheduled Job Log",
    "Server Script",
    "Session Default",
    "Tag",
    "ToDo",
    "User",
    "Version",
    "Web Form",
    "Workspace",
    "Client Script",
    # -- ERPNext core -----------------------------------------------------
    "Address",
    "Bank Account",
    "Batch",
    "Bin",
    "BOM",
    "BOM Item",
    "Brand",
    "Company",
    "Contact",
    "Cost Center",
    "Country",
    "Currency",
    "Customer",
    "Customer Group",
    "Delivery Note",
    "Delivery Note Item",
    "Department",
    "Employee",
    "Equipment",
    "Item",
    "Item Attribute",
    "Item Attribute Value",
    "Item Group",
    "Item Price",
    "Item Quality Inspection Parameter",
    "Item Tax",
    "Journal Entry",
    "Language",
    "Location",
    "Material Issue",
    "Material Issue Item",
    "Material Receipt",
    "Material Receipt Item",
    "Material Request",
    "Material Request Item",
    "Mode of Payment",
    "Operation",
    "Payment Entry",
    "Payment Entry Reference",
    "Payment Terms Template",
    "Price List",
    "Production Line",
    "Production Plan",
    "Project",
    "Purchase Invoice",
    "Purchase Invoice Item",
    "Purchase Receipt",
    "Purchase Receipt Item",
    "Purchase Taxes and Charges",
    "Quality Inspection",
    "Quality Inspection Method",
    "Quality Inspection Parameter",
    "Quality Inspection Parameter Group",
    "Quality Procedure",
    "Quotation",
    "Quotation Item",
    "Routing",
    "Sales Invoice",
    "Sales Invoice Item",
    "Sales Order",
    "Sales Order Item",
    "Sales Partner",
    "Sales Person",
    "Sales Taxes and Charges",
    "Serial No",
    "Stock Entry",
    "Stock Entry Detail",
    "Supplier",
    "Supplier Quotation",
    "Supplier Quotation Item",
    "Tax Category",
    "Territory",
    "Terms",
    "UOM",
    "UOM Conversion Detail",
    "Warehouse",
    "Work Order",
    "Workflow",
    "Workflow Action Master",
    "Workflow State",
    "Workstation",
})

# Case-insensitive lookup of the list above: MariaDB's default collation is
# case-insensitive, so "item group" and "Item Group" are the same DocType.
_STANDARD_LOOKUP = frozenset(name.lower() for name in STANDARD_DOCTYPES)


def is_standard_doctype(name: str) -> bool:
    """True when ``name`` is a standard Frappe / ERPNext DocType."""
    return (name or "").strip().lower() in _STANDARD_LOOKUP


def core_apps_present(inventory: Inventory) -> bool:
    """True when the scan root contains ``frappe`` or ``erpnext``."""
    return any(app.name.strip().lower() in CORE_APP_NAMES for app in inventory.apps)


def _slugify(value: str) -> str:
    """Lower-case kebab slug: ``"Batch AMB"`` -> ``"batch-amb"``."""
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower())
    return slug.strip("-")


def _link_fields(app: AppInfo) -> dict[str, list[dict[str, str]]]:
    """Map target DocType -> the fields of ``app`` that point at it.

    Only ``Link`` and ``Table`` fields are considered: both name a DocType in
    their ``options``. The declaring DocType is kept in the evidence so a
    reviewer can find the field in the app's own schema.
    """
    targets: dict[str, list[dict[str, str]]] = {}
    for doctype, path in sorted(app.doctype_json_paths().items()):
        data = read_json(path)
        if not isinstance(data, dict):
            continue
        for fielddef in data.get("fields") or []:
            if not isinstance(fielddef, dict):
                continue
            fieldtype = fielddef.get("fieldtype")
            if fieldtype not in _LINK_FIELDTYPES:
                continue
            options = fielddef.get("options")
            if not isinstance(options, str) or not options.strip():
                continue
            targets.setdefault(options.strip(), []).append(
                {
                    "fieldname": str(fielddef.get("fieldname") or ""),
                    "fieldtype": str(fieldtype),
                    "doctype": doctype,
                }
            )
    return targets


def scan_undeclared_dependencies(inventory: Inventory) -> dict[str, Any]:
    """Return the undeclared cross-app DocType dependencies.

    Returns a dict with an ``apps`` map (app name -> {required_apps, targets})
    plus scan counters under ``_stats``.
    """
    apps: dict[str, Any] = {}
    link_fields = 0
    unresolved = 0
    undeclared = 0
    dynamic = 0
    standard = 0
    has_core = core_apps_present(inventory)
    unresolved_without_core = 0

    for app in inventory.apps:
        declared = app.required_apps()
        declared_lower = {str(name).lower() for name in declared}
        # ``required_apps`` can be built at runtime. Then the declaration
        # cannot be judged statically, and claiming "not declared" would be a
        # false positive.
        required_apps_dynamic = (
            "required_apps" in app.hooks.assignments
            and not isinstance(app.hooks.assignments.get("required_apps"), (list, tuple))
        )
        if required_apps_dynamic:
            dynamic += 1
        targets = _link_fields(app)
        link_fields += sum(len(fields) for fields in targets.values())

        entries: dict[str, Any] = {}
        for target, fields in sorted(targets.items()):
            # MariaDB's default collation is case-insensitive, so the
            # inventory resolves the target the way the database would.
            owners = inventory.app_for_doctype(target)
            owner_app = None
            if app.name in owners:
                status = _OWN
            elif is_standard_doctype(target):
                # A standard Frappe / ERPNext DocType is shipped by the
                # framework, not by an app. Its absence from the scan tree
                # says something about the scan root, not about this app:
                # nothing is reported at all.
                status = _STANDARD
                standard += 1
            elif not owners:
                status = _MISSING
                unresolved += 1
            else:
                missing_declaration = [
                    owner for owner in owners if owner.lower() not in declared_lower
                ]
                if not missing_declaration:
                    status = _DECLARED
                elif required_apps_dynamic:
                    status = _UNKNOWN
                else:
                    status = _UNDECLARED
                    owner_app = missing_declaration[0]
                    undeclared += 1
            entries[target] = {
                "fields": fields,
                "owners": owners,
                "status": status,
                "owner_app": owner_app,
            }

        apps[app.name] = {"required_apps": declared, "targets": entries}

    return {
        "apps": apps,
        "core_apps_present": has_core,
        "_stats": {
            "apps_scanned": len(inventory.apps),
            "link_fields_scanned": link_fields,
            "unresolved_targets": unresolved,
            "standard_targets": standard,
            "undeclared_targets": undeclared,
            "dynamic_required_apps": dynamic,
            "core_apps_present": has_core,
        },
    }


def build_findings(scan: dict[str, Any]) -> list[Finding]:
    """Turn the undeclared-dependency scan into envelope findings."""
    findings: list[Finding] = []
    core_apps_present = bool(scan.get("core_apps_present"))
    for app_name, info in sorted(scan.get("apps", {}).items()):
        required = list(info.get("required_apps") or [])
        declared_text = ", ".join(required) if required else "(none)"
        for target, entry in sorted((info.get("targets") or {}).items()):
            status = entry.get("status")
            if status not in (_MISSING, _UNDECLARED):
                continue
            fields = entry.get("fields") or []
            if not fields:
                continue
            first = fields[0]
            evidence: dict[str, Any] = {
                "app": app_name,
                "doctype": target,
                "fieldname": first.get("fieldname", ""),
                "fieldtype": first.get("fieldtype", ""),
                "targets": fields,
                "required_apps": required,
            }
            if status == _MISSING:
                evidence["owner_apps"] = []
                if core_apps_present:
                    severity = "high"
                    title = f"No installed app ships DocType '{target}'"
                    description = (
                        f"App '{app_name}' points {len(fields)} field(s) at DocType "
                        f"'{target}', but no installed app ships that DocType. The link "
                        f"can never resolve: installing '{app_name}' alone leaves "
                        f"'{first.get('fieldname')}' pointing at nothing."
                    )
                else:
                    severity = "info"
                    title = f"DocType '{target}' is not in the scanned tree"
                    description = (
                        f"App '{app_name}' points {len(fields)} field(s) at DocType "
                        f"'{target}', and no app in the scanned tree ships it. The scan "
                        f"root does not contain frappe / erpnext, so the target may be "
                        f"shipped by an app outside the tree. Reported for review, not "
                        f"as a confirmed defect."
                    )
            else:
                severity = "medium"
                owner_app = entry.get("owner_app")
                evidence["owner_apps"] = list(entry.get("owners") or [])
                evidence["owner_app"] = owner_app
                title = f"DocType '{target}' ships in '{owner_app}', which is not declared"
                description = (
                    f"App '{app_name}' points {len(fields)} field(s) at DocType "
                    f"'{target}', which is shipped by '{owner_app}', but "
                    f"'{owner_app}' is not in its required_apps (declared: "
                    f"{declared_text}). The dependency is implicit, so the links "
                    f"break when '{owner_app}' is not installed."
                )
            findings.append(
                Finding(
                    id=f"integrity-{CHECK_ID}-{app_name}-{_slugify(target)}",
                    title=title,
                    severity=severity,
                    description=description,
                    app=app_name,
                    evidence=evidence,
                )
            )
    return findings


def check_undeclared_app_dependency(inventory: Inventory) -> CheckResult:
    """Check entry point."""
    scan = scan_undeclared_dependencies(inventory)
    return CheckResult(
        check_id=CHECK_ID,
        findings=build_findings(scan),
        stats=scan["_stats"],
    )


CHECK_SPEC = CheckSpec(
    check_id=CHECK_ID,
    title="Undeclared cross-app DocType dependency",
    description=(
        "Detect Link / Table fields that point at a DocType from another app "
        "which the consuming app never declared in required_apps."
    ),
    fn=check_undeclared_app_dependency,
)
