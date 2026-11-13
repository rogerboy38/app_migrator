"""Core comparison for select-option drift: a stored value the options no longer allow.

Why this exists
---------------
Changing the options of a Select field is a **data-integrity change**, not a
schema change. Frappe validates a document's stored value against the field's
*current* options on every non-cancel save, so a value that was removed from
the options makes the affected documents un-editable: the next save raises on
validation. In the 2026-11-05 audits of ``amb_w_tds`` and
``rnd_warehouse_management`` one such option change would have made **42
submitted Stock Entries un-editable** — a failure that only surfaces when
someone amends a posted document, long after ``bench migrate`` reported
success.

Why it lives outside ``checks/``
-------------------------------
The comparison needs the values a live site actually stores, which the
filesystem ``Inventory`` cannot provide, and the value collector has to be
**injected** so this module stays importable with no Frappe installed. Putting
it here — outside ``app_migrator/_integrity/checks/`` — keeps it out of the
auto-discovered check registry; the command layer
(``app_migrator/commands/select_option_drift.py``) owns the site access.

What counts as drift
--------------------
A stored value is drift when it is not among the field's options. The
comparison is **case-sensitive** (Frappe's own validation is) but surrounding
whitespace is trimmed on both sides. A field with an **empty option list**
constrains nothing — any stored value is legal — so it is skipped rather than
reported; that is the only exception to "not in the options means drift", and
it applies to ``Select`` fields only (a ``Link`` always constrains: its target
records are the allowed set, and a stored link to a deleted record is drift
even when the target holds no records at all).
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from .base import DEFAULT_FINDING_LIMIT, SEVERITY_RANK, Finding

CHECK_ID = "select-option-drift"

# Finding ids are the diff key an agent uses to tell "the same problem again"
# from "a new problem", so they must be stable across runs.
FINDING_ID_PREFIX = "integrity-select-option-drift-"

# Fieldtypes whose stored value is constrained by a list of allowed values.
CONSTRAINED_FIELDTYPES = ("Select", "Link")


def slugify_doctype(doctype: str) -> str:
    """Stable kebab-case slug of a DocType name (``Stock Entry`` -> ``stock-entry``)."""
    slug = re.sub(r"[^a-z0-9]+", "-", str(doctype or "").strip().lower())
    return slug.strip("-")


def finding_id(doctype: str, fieldname: str) -> str:
    """Stable finding id for one (DocType, field) pair.

    The DocType is slugified; the fieldname is kept verbatim because it is the
    literal column name on the site — mangling it would break the mapping from
    a finding id back to the field that has to be fixed.
    """
    return f"{FINDING_ID_PREFIX}{slugify_doctype(doctype)}-{fieldname}"


def _normalise(value: Any) -> str:
    """Trimmed, stringified value used for the option comparison."""
    if value is None:
        return ""
    return str(value).strip()


def compare_select_options(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Compare stored values against the options each field currently allows.

    Args:
        records: iterable of dicts, each::

            {"doctype": str, "fieldname": str, "options": list[str],
             "stored_values": list[str], "doctype_count": int, "app": str}

            ``fieldtype`` and ``constrained`` are optional extras:
            ``fieldtype`` ("Select" / "Link") selects the wording of the
            finding, ``constrained`` (default: "the field has options")
            marks a field as constraining even with an empty option list.

    Returns:
        ``{"drift": [...], "_stats": {...}}`` — one drift entry per field that
        stores a value the field no longer allows. Each entry carries
        ``doctype``, ``fieldname``, ``fieldtype``, ``options``,
        ``stored_values`` (the offending values only), ``doctype_count``,
        ``severity`` and ``app``.

    Severity:
        ``high`` when the doctype holds rows (``doctype_count > 0`` — the
        submitted/cancelled proxy, i.e. documents that would actually fail to
        save), ``medium`` when the doctype is empty (latent drift: nothing
        breaks until the first document is saved).
    """
    drift: list[dict[str, Any]] = []
    stats: dict[str, Any] = {
        "records_scanned": 0,
        "fields_scanned": 0,
        "fields_unconstrained": 0,
        "doctypes_scanned": 0,
        "blank_values_skipped": 0,
        "drift_count": 0,
        "high_count": 0,
        "medium_count": 0,
    }
    doctypes: set = set()

    for record in records or []:
        stats["records_scanned"] += 1
        doctype = str(record.get("doctype") or "")
        fieldname = str(record.get("fieldname") or "")
        if not doctype or not fieldname:
            continue
        doctypes.add(doctype)
        stats["fields_scanned"] += 1

        options = [o for o in (_normalise(v) for v in (record.get("options") or [])) if o]
        constrained = record.get("constrained")
        if constrained is None:
            constrained = bool(options)
        if not constrained:
            # A field with no options constrains nothing: every stored value
            # is legal, so there is nothing to drift from.
            stats["fields_unconstrained"] += 1
            continue

        allowed = set(options)
        offending: list[str] = []
        for value in record.get("stored_values") or []:
            normalised = _normalise(value)
            if not normalised:
                # An unset Select is not "outside the options".
                stats["blank_values_skipped"] += 1
                continue
            if normalised not in allowed and normalised not in offending:
                offending.append(normalised)

        if not offending:
            continue

        count = int(record.get("doctype_count") or 0)
        severity = "high" if count > 0 else "medium"
        drift.append(
            {
                "doctype": doctype,
                "fieldname": fieldname,
                "fieldtype": str(record.get("fieldtype") or ""),
                "options": options,
                "stored_values": offending,
                "doctype_count": count,
                "severity": severity,
                "app": str(record.get("app") or ""),
            }
        )
        stats["drift_count"] += 1
        stats[f"{severity}_count"] += 1

    stats["doctypes_scanned"] = len(doctypes)
    return {"drift": drift, "_stats": stats}


def build_findings(
    drift: Iterable[dict[str, Any]],
    limit: int = DEFAULT_FINDING_LIMIT,
) -> list[Finding]:
    """Turn drift entries into findings with stable ids.

    The findings are ordered worst-first, then by id, and truncated to
    ``limit`` (the true count stays available in the scan stats, so
    truncation never hides a number).
    """
    findings: list[Finding] = []
    for entry in drift or []:
        doctype = str(entry.get("doctype") or "")
        fieldname = str(entry.get("fieldname") or "")
        fieldtype = str(entry.get("fieldtype") or "")
        options = list(entry.get("options") or [])
        stored = list(entry.get("stored_values") or [])
        count = int(entry.get("doctype_count") or 0)
        severity = str(entry.get("severity") or "medium")
        app = str(entry.get("app") or "") or None

        if fieldtype == "Link":
            problem = (
                f"stores a link to a record that no longer exists ({', '.join(stored)})"
            )
            impact = (
                "Frappe cannot resolve the link, so every non-cancel save of the "
                "affected documents raises."
            )
        else:
            problem = (
                f"stores a value that is not among the field's options "
                f"({', '.join(stored)} vs {', '.join(options) or 'no options'})"
            )
            impact = (
                "Frappe validates the stored value against the current options on "
                "every non-cancel save, so the affected documents become "
                "un-editable."
            )

        if count > 0:
            exposure = (
                f"{doctype} holds {count} row(s), so documents that are saved after "
                "the option change will fail validation."
            )
        else:
            exposure = (
                f"{doctype} holds no rows today, so nothing breaks yet; the drift is "
                "latent and surfaces on the first document saved."
            )

        findings.append(
            Finding(
                id=finding_id(doctype, fieldname),
                title=f"Select option drift: {doctype}.{fieldname}",
                severity=severity,
                description=(
                    f"Field '{doctype}.{fieldname}' {problem}. {impact} "
                    f"{exposure} Removing an option is a data-integrity change, not "
                    f"a schema change: re-add the option or migrate the stored "
                    f"values before migrating."
                ),
                app=app,
                evidence={
                    "doctype": doctype,
                    "fieldname": fieldname,
                    "fieldtype": fieldtype,
                    "options": options,
                    "stored_values": stored,
                    "doctype_count": count,
                },
            )
        )

    findings.sort(key=lambda f: (SEVERITY_RANK.get(f.severity, 99), f.id))
    if limit is None:
        return findings
    return findings[:limit]


def _candidate_doctypes(inventory: Any, collector: Any, doctype_filter: str | None) -> list[str]:
    """DocTypes to scan: the explicit filter, else the site's list, else the inventory's."""
    if doctype_filter:
        return [doctype_filter]
    getter = getattr(collector, "doctypes", None)
    if callable(getter):
        try:
            names = [str(n) for n in (getter() or [])]
        except Exception:
            names = []
        if names:
            return names
    shipped = getattr(inventory, "all_shipped_doctypes", None)
    if callable(shipped):
        try:
            return sorted(str(n) for n in (shipped() or {}))
        except Exception:
            return []
    return []


def _app_map(inventory: Any) -> dict[str, str]:
    """DocType (lower-cased) -> owning app, read from the inventory once."""
    shipped = getattr(inventory, "all_shipped_doctypes", None)
    if not callable(shipped):
        return {}
    try:
        doctypes = shipped() or {}
    except Exception:
        return {}
    mapping: dict[str, str] = {}
    for doctype, owners in doctypes.items():
        if not owners:
            continue
        mapping[str(doctype).lower()] = sorted(str(o) for o in owners)[0]
    return mapping


def scan_select_options(
    inventory: Any,
    collector: Any,
    doctype_filter: str | None = None,
    field_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Collect one record per (DocType, constrained field) from a live site.

    The site is reached **only** through the injected collector, so this
    module never touches the database. The collector is any object exposing:

    - ``doctypes()`` -> list of DocType names;
    - ``fields(doctype)`` -> list of ``{"fieldname", "fieldtype"}`` descriptors;
    - ``stored_values(doctype, fieldname)`` -> the distinct stored values;
    - ``options(doctype, fieldname)`` -> the values the field allows;
    - ``row_count(doctype)`` -> how many rows the DocType holds.

    ``stored_values`` is read **before** ``options``, so a collector that
    resolves a ``Link``'s allowed values from the stored values (the cheap
    way) has them cached by then.

    Args:
        inventory: the bench inventory, used to attribute each DocType to the
            app that ships it. May be ``None``.
        collector: the site-provided value collector (see above).
        doctype_filter: only scan this DocType.
        field_filter: only scan this fieldname.

    Returns:
        The records consumed by :func:`compare_select_options`.
    """
    records: list[dict[str, Any]] = []
    app_map = _app_map(inventory)

    for doctype in _candidate_doctypes(inventory, collector, doctype_filter):
        try:
            fields = collector.fields(doctype) or []
        except Exception:
            continue
        for field in fields:
            fieldname = str(field.get("fieldname") or "")
            fieldtype = str(field.get("fieldtype") or "")
            if not fieldname or fieldtype not in CONSTRAINED_FIELDTYPES:
                continue
            if field_filter and fieldname != field_filter:
                continue
            try:
                stored = list(collector.stored_values(doctype, fieldname) or [])
            except Exception:
                continue
            try:
                options = list(collector.options(doctype, fieldname) or [])
            except Exception:
                options = []
            try:
                count = int(collector.row_count(doctype) or 0)
            except Exception:
                count = 0
            records.append(
                {
                    "doctype": doctype,
                    "fieldname": fieldname,
                    "fieldtype": fieldtype,
                    "options": options,
                    # A Link always constrains: its target records are the
                    # allowed set, even when the target holds no records.
                    "constrained": bool(options) or fieldtype == "Link",
                    "stored_values": stored,
                    "doctype_count": count,
                    "app": app_map.get(str(doctype).lower(), ""),
                }
            )
    return records
