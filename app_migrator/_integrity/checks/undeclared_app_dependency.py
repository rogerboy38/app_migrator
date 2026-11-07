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

- the target DocType is shipped by **no** installed app -> ``high``
  (the link can never work);
- the target DocType is shipped by another app that is **not** in the
  consuming app's ``required_apps`` -> ``medium`` (the dependency is
  implicit and breaks when that app is not installed).

Targets the app ships itself are ignored: that is the normal case. When
``required_apps`` is built at runtime it cannot be judged statically, so the
app is left alone rather than reported.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

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


def _slugify(value: str) -> str:
    """Lower-case kebab slug: ``"Batch AMB"`` -> ``"batch-amb"``."""
    slug = re.sub(r"[^a-z0-9]+", "-", (value or "").lower())
    return slug.strip("-")


def _link_fields(app: AppInfo) -> Dict[str, List[Dict[str, str]]]:
    """Map target DocType -> the fields of ``app`` that point at it.

    Only ``Link`` and ``Table`` fields are considered: both name a DocType in
    their ``options``. The declaring DocType is kept in the evidence so a
    reviewer can find the field in the app's own schema.
    """
    targets: Dict[str, List[Dict[str, str]]] = {}
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


def scan_undeclared_dependencies(inventory: Inventory) -> Dict[str, Any]:
    """Return the undeclared cross-app DocType dependencies.

    Returns a dict with an ``apps`` map (app name -> {required_apps, targets})
    plus scan counters under ``_stats``.
    """
    apps: Dict[str, Any] = {}
    link_fields = 0
    unresolved = 0
    undeclared = 0
    dynamic = 0

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

        entries: Dict[str, Any] = {}
        for target, fields in sorted(targets.items()):
            # MariaDB's default collation is case-insensitive, so the
            # inventory resolves the target the way the database would.
            owners = inventory.app_for_doctype(target)
            owner_app = None
            if app.name in owners:
                status = _OWN
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
        "_stats": {
            "apps_scanned": len(inventory.apps),
            "link_fields_scanned": link_fields,
            "unresolved_targets": unresolved,
            "undeclared_targets": undeclared,
            "dynamic_required_apps": dynamic,
        },
    }


def build_findings(scan: Dict[str, Any]) -> List[Finding]:
    """Turn the undeclared-dependency scan into envelope findings."""
    findings: List[Finding] = []
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
            evidence: Dict[str, Any] = {
                "app": app_name,
                "doctype": target,
                "fieldname": first.get("fieldname", ""),
                "fieldtype": first.get("fieldtype", ""),
                "targets": fields,
                "required_apps": required,
            }
            if status == _MISSING:
                severity = "high"
                evidence["owner_apps"] = []
                title = f"No installed app ships DocType '{target}'"
                description = (
                    f"App '{app_name}' points {len(fields)} field(s) at DocType "
                    f"'{target}', but no installed app ships that DocType. The link "
                    f"can never resolve: installing '{app_name}' alone leaves "
                    f"'{first.get('fieldname')}' pointing at nothing."
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
