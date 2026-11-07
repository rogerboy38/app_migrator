"""Check: two apps ship the same Custom Field or Property Setter.

Why this check exists
---------------------
Audited evidence (both audits, 2026-11-05):

- ``rnd_warehouse_management`` ships **63 of its 64** Custom Fields and **all
  21** of its Property Setters identically to ``amb_w_spc``.
- ``amb_w_tds`` ships ``Item-substrate`` (also in ``amb_w_spc``) and
  ``Item-custom_is_sub_batch`` (also in ``rnd_warehouse_management``).
- Across the three apps, six DocTypes carry Custom Fields from more than one
  app.

Why it matters
--------------
Frappe's migrate syncs fixtures in app order. When two apps ship the same
Custom Field, **whichever app syncs last owns the record**. The copies are
identical today, so nothing looks wrong — but the moment one copy is edited,
the effective definition depends on install order, and the two apps silently
drift apart. The repo's own ``hooks.py`` already admits one such case as
"latent dual-capture".

What is reported
----------------
One finding per shared record, carrying every owning app and whether the
copies are currently identical or already divergent. Divergence is escalated
to ``high``; identical copies are ``medium`` because they are a latent trap
rather than an active defect.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..base import CheckResult, CheckSpec, Finding
from ..context import Inventory, app_pair_key, comparable_record

CHECK_ID = "shared-fixture-ownership"

# Volatile fixture keys: two records that differ only here are the same record.
_IGNORED_KEYS = ("modified", "creation", "owner", "idx", "field_order")


def _collect(inventory: Inventory, kind: str) -> Dict[str, Dict[str, Any]]:
    """Map record key -> {app: record} for every app that ships one."""
    owners: Dict[str, Dict[str, Any]] = {}
    for app in inventory.apps:
        records = (
            app.custom_fields() if kind == "custom_field" else app.property_setters()
        )
        for record in records:
            key = app_pair_key(record, kind)
            if not key or key.endswith("-None"):
                continue
            owners.setdefault(key, {})[app.name] = record
    return owners


def _records_differ(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    """True when two copies of the same record are not byte-equivalent."""
    return comparable_record(a, _IGNORED_KEYS) != comparable_record(b, _IGNORED_KEYS)


def scan_shared_fixtures(inventory: Inventory) -> Dict[str, Any]:
    """Return the shared Custom Field / Property Setter records.

    Returns a dict with ``custom_fields`` and ``property_setters`` maps of
    record key -> {app, identical, copies}, plus scan counters.
    """
    result: Dict[str, Any] = {"custom_fields": {}, "property_setters": {}, "_stats": {}}
    for kind, bucket in (("custom_field", "custom_fields"), ("property_setter", "property_setters")):
        owners = _collect(inventory, kind)
        shared: Dict[str, Any] = {}
        for key, by_app in owners.items():
            if len(by_app) < 2:
                continue
            app_names = sorted(by_app)
            first = by_app[app_names[0]]
            identical = all(not _records_differ(first, by_app[name]) for name in app_names[1:])
            shared[key] = {
                "apps": app_names,
                "identical": identical,
                "copies": {name: by_app[name] for name in app_names},
            }
        result[bucket] = shared
        result["_stats"][f"{bucket}_scanned"] = sum(
            1 for _ in _collect(inventory, kind).values()
        )
        result["_stats"][f"{bucket}_shared"] = len(shared)
    result["_stats"]["apps_scanned"] = len(inventory.apps)
    return result


def build_findings(scan: Dict[str, Any]) -> List[Finding]:
    """Turn the shared-fixture scan into envelope findings."""
    findings: List[Finding] = []
    for kind, label in (("custom_fields", "Custom Field"), ("property_setters", "Property Setter")):
        for key, info in sorted(scan.get(kind, {}).items()):
            apps = info["apps"]
            identical = info["identical"]
            severity = "medium" if identical else "high"
            if identical:
                detail = (
                    "The copies are currently identical, so nothing looks wrong today. "
                    "Frappe's migrate syncs fixtures in app order, so whichever app syncs "
                    "last owns this record; the first edit to one copy makes the effective "
                    "definition depend on install order."
                )
            else:
                detail = (
                    "The copies have ALREADY diverged. Frappe's migrate syncs fixtures in "
                    "app order, so whichever app syncs last owns this record and the other "
                    "app's definition is silently discarded on every migrate."
                )
            findings.append(
                Finding(
                    id=f"integrity-{CHECK_ID}-{kind.replace('_', '-')}-{key}",
                    title=f"{label} shipped by {len(apps)} apps: {key}",
                    severity=severity,
                    description=(
                        f"{label} '{key}' is shipped by {len(apps)} apps "
                        f"({', '.join(apps)}). {detail}"
                    ),
                    app=apps[0],
                    evidence={
                        "record_kind": kind,
                        "record_key": key,
                        "owning_apps": apps,
                        "identical": identical,
                    },
                )
            )
    return findings


def check_shared_fixtures(inventory: Inventory) -> CheckResult:
    """Check entry point."""
    scan = scan_shared_fixtures(inventory)
    return CheckResult(
        check_id=CHECK_ID,
        findings=build_findings(scan),
        stats=scan["_stats"],
    )


CHECK_SPEC = CheckSpec(
    check_id=CHECK_ID,
    title="Shared Custom Field / Property Setter ownership",
    description=(
        "Detect Custom Fields and Property Setters shipped by more than one app, "
        "where migrate order decides the surviving definition."
    ),
    fn=check_shared_fixtures,
)
