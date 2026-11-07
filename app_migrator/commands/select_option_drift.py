"""app-migrator-select-option-drift: stored values a Select field no longer allows.

Why this command exists
-----------------------
Changing the options of a Select field is a **data-integrity change**, not a
schema change. Frappe validates a document's stored value against the field's
*current* options on every non-cancel save, so a value that was removed from
the options makes the affected documents un-editable: the next save raises on
validation. In the 2026-11-05 audits of ``amb_w_tds`` and
``rnd_warehouse_management`` one such option change would have made **42
submitted Stock Entries un-editable** — a failure that only surfaces when
someone amends a posted document, long after ``bench migrate`` reported
success.

app_migrator has to find this **before** the migrate, so that the option
change ships together with the data fix (re-add the option, or migrate the
stored values to a value that is still allowed).

What it reads
-------------
- ``frappe.get_meta(doctype)`` — the field list of every DocType on the site.
- ``frappe.get_all(doctype, pluck=<fieldname>, distinct=True)`` — the distinct
  values actually stored in that column.
- ``frappe.get_all(<link target>, filters={"name": ("in", <stored>)})`` — which
  stored ``Link`` values still resolve to an existing record.
- ``frappe.db.count(doctype)`` — how many rows the DocType holds (the
  submitted/cancelled proxy that decides ``high`` vs ``medium``).

This command is **report-only**: it reads the site and writes nothing, so it
is safe to run against production. The detection core
(``app_migrator/_integrity/select_option_drift.py``) is import-safe and
bench-free so it can be unit-tested in-process; only this click wrapper
touches the envelope / exit path.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import click

try:
    import frappe
except ImportError:  # pragma: no cover - bench-free import path
    frappe = None  # type: ignore[assignment]

try:
    from frappe.commands import pass_context
except ImportError:  # pragma: no cover - bench-free import path
    def pass_context(f):
        return f


from ._envelope import EXIT_CODE_MAPPING, emit_envelope, make_envelope
from .._integrity import DEFAULT_APPS_ROOT, DEFAULT_FINDING_LIMIT, Inventory
from .._integrity.select_option_drift import (
    CHECK_ID,
    CONSTRAINED_FIELDTYPES,
    build_findings,
    compare_select_options,
    scan_select_options,
)

COMMAND_NAME = "select-option-drift"

# Cap on DocTypes read from the site. The scan touches every table of the
# site, so it is bounded; the number of DocTypes actually scanned is always
# reported in the envelope evidence, so the cap never hides a number.
MAX_DOCTYPES_SCANNED = 500


class SiteSelectCollector:
    """Reads the constrained fields and their stored values from a live site.

    Every site call is wrapped: a DocType that cannot be read (missing table,
    renamed column, unreadable link target) is skipped and recorded in
    ``errors`` rather than aborting the whole scan.
    """

    def __init__(self, max_doctypes: int = MAX_DOCTYPES_SCANNED) -> None:
        self.max_doctypes = max_doctypes
        self.doctypes_seen = 0
        self.doctypes_skipped = 0
        self.errors: List[str] = []
        self._meta_cache: Dict[str, Any] = {}
        self._stored_cache: Dict[Any, List[str]] = {}

    # -- collector protocol ------------------------------------------------
    def doctypes(self) -> List[str]:
        """Every DocType on the site."""
        try:
            names = frappe.get_all("DocType", pluck="name", limit_page_length=0)
        except Exception as exc:
            self.errors.append(f"DocType list unreadable: {exc}")
            return []
        return [str(n) for n in names or []]

    def fields(self, doctype: str) -> List[Dict[str, Any]]:
        """Descriptors of the constrained (Select / Link) fields of a DocType."""
        meta = self._meta(doctype)
        if meta is None:
            return []
        descriptors: List[Dict[str, Any]] = []
        for df in getattr(meta, "fields", None) or []:
            fieldtype = getattr(df, "fieldtype", "") or ""
            if fieldtype not in CONSTRAINED_FIELDTYPES:
                continue
            fieldname = getattr(df, "fieldname", "") or ""
            if not fieldname:
                continue
            descriptors.append({"fieldname": fieldname, "fieldtype": fieldtype})
        return descriptors

    def stored_values(self, doctype: str, fieldname: str) -> List[str]:
        """The distinct values actually stored in a column."""
        key = (doctype, fieldname)
        if key in self._stored_cache:
            return self._stored_cache[key]
        try:
            values = frappe.get_all(
                doctype, pluck=fieldname, distinct=True, limit_page_length=0,
            )
        except Exception as exc:
            self.errors.append(f"{doctype}.{fieldname}: stored values unreadable: {exc}")
            values = []
        values = [str(v) for v in values or [] if v is not None]
        self._stored_cache[key] = values
        return values

    def options(self, doctype: str, fieldname: str) -> List[str]:
        """The values the field currently allows.

        For a ``Select`` that is the field's own option list. For a ``Link``
        it is the set of stored values that still resolve to an existing
        record — the cheap way to answer "which stored links are dangling?"
        without listing the whole target table.
        """
        df = self._docfield(doctype, fieldname)
        if df is None:
            return []
        fieldtype = getattr(df, "fieldtype", "") or ""
        if fieldtype == "Select":
            raw = str(getattr(df, "options", "") or "")
            return [line.strip() for line in raw.split("\n") if line.strip()]

        target = str(getattr(df, "options", "") or "")
        stored = self._stored_cache.get((doctype, fieldname)) or []
        if not target or not stored:
            return []
        try:
            existing = frappe.get_all(
                target,
                filters={"name": ("in", stored)},
                pluck="name",
                limit_page_length=0,
            )
        except Exception as exc:
            self.errors.append(f"{doctype}.{fieldname}: link target '{target}' unreadable: {exc}")
            return []
        return [str(v) for v in existing or []]

    def row_count(self, doctype: str) -> int:
        """How many rows the DocType holds."""
        try:
            return int(frappe.db.count(doctype) or 0)
        except Exception as exc:
            self.errors.append(f"{doctype}: row count unreadable: {exc}")
            return 0

    # -- internals ---------------------------------------------------------
    def _meta(self, doctype: str) -> Any:
        if doctype in self._meta_cache:
            return self._meta_cache[doctype]
        try:
            meta = frappe.get_meta(doctype)
        except Exception as exc:
            self.errors.append(f"{doctype}: meta unreadable: {exc}")
            meta = None
        self._meta_cache[doctype] = meta
        return meta

    def _docfield(self, doctype: str, fieldname: str) -> Any:
        meta = self._meta(doctype)
        if meta is None:
            return None
        for df in getattr(meta, "fields", None) or []:
            if getattr(df, "fieldname", "") == fieldname:
                return df
        return None


def _resolve_site(site: Optional[str]) -> Optional[str]:
    """The site to scan: the explicit one, else the site's current one."""
    if site:
        return site
    try:
        current = getattr(getattr(frappe, "local", None), "site", None)
    except Exception:
        current = None
    return str(current) if current else None


@click.command('app-migrator-select-option-drift')
@click.option('--site', default=None, help='Site name (the scan reads a live site)')
@click.option('--json', 'as_json', is_flag=True, help='Emit v0.5 envelope JSON')
@click.option('--doctype', default=None, help='Only scan this DocType')
@click.option('--field', default=None, help='Only scan this fieldname')
@click.option('--limit', default=DEFAULT_FINDING_LIMIT, show_default=True, type=int,
              help='Max findings carried in the envelope')
@pass_context
def app_migrator_select_option_drift(context, site, as_json, doctype, field, limit):
    """Find stored values a Select field no longer allows. Report-only."""
    start = time.time()

    def _fail(summary: str, evidence: List[Dict[str, Any]]) -> None:
        """Emit an error envelope (or a plain message) and exit non-zero."""
        envelope = make_envelope(
            command=COMMAND_NAME,
            status="error",
            summary=summary,
            findings=[],
            evidence=evidence,
            site=site,
            start_time=start,
        )
        if as_json:
            emit_envelope(envelope)
        click.echo(f"Error: {summary}", err=True)
        raise SystemExit(EXIT_CODE_MAPPING.get("error", 40))

    if frappe is None:
        _fail(
            "select-option-drift needs a Frappe site: the 'frappe' module is not "
            "importable in this interpreter. Run it from the bench "
            "(bench app-migrator select-option-drift --site <site>).",
            [{"kind": "error", "error": "frappe is not importable"}],
        )

    resolved_site = _resolve_site(site)
    if not resolved_site:
        _fail(
            "no site to scan: pass --site <site>. The scan reads the stored values "
            "of a live site, so it cannot run without one.",
            [{"kind": "error", "error": "no site given and no current site"}],
        )

    try:
        frappe.init(site=resolved_site)
        frappe.connect()
    except Exception as exc:
        _fail(
            f"could not connect to site '{resolved_site}': {exc}",
            [{"kind": "error", "error": str(exc), "type": type(exc).__name__}],
        )
        return

    collector = SiteSelectCollector()
    try:
        inventory = Inventory(apps_root=DEFAULT_APPS_ROOT)
    except Exception:
        inventory = None

    try:
        records = scan_select_options(
            inventory,
            collector,
            doctype_filter=doctype,
            field_filter=field,
        )
        result = compare_select_options(records)
        drift = result["drift"]
        stats = result["_stats"]
        findings = build_findings(drift, limit=limit)
    except Exception as exc:
        _fail(
            f"select-option-drift failed: {exc}",
            [{"kind": "error", "error": str(exc), "type": type(exc).__name__}],
        )
        return
    finally:
        try:
            frappe.destroy()
        except Exception:
            pass

    truncated = len(drift) - len(findings)
    status = "warn" if drift else "ok"
    summary = (
        f"select-option-drift: {len(drift)} field(s) store a value their options no "
        f"longer allow, across {stats['doctypes_scanned']} doctype(s) / "
        f"{stats['fields_scanned']} constrained field(s)"
        + (f" (showing first {len(findings)})" if truncated > 0 else "")
    )

    if as_json:
        envelope = make_envelope(
            command=COMMAND_NAME,
            status=status,
            summary=summary,
            findings=[f.to_dict() for f in findings],
            evidence=[
                {"kind": "scan_stats", "check": CHECK_ID, **stats},
                {
                    "kind": "scan_params",
                    "site": resolved_site,
                    "doctype": doctype,
                    "field": field,
                    "findings_truncated": max(truncated, 0),
                },
                {
                    "kind": "collector_errors",
                    "error_count": len(collector.errors),
                    "errors": collector.errors[:20],
                },
            ],
            suggested_next_commands=[
                {
                    "command": f"bench app-migrator select-option-drift --site {resolved_site} --json",
                    "approval_required": False,
                    "description": "Re-run the scan and diff the finding ids.",
                },
                {
                    "command": (
                        f"bench app-migrator select-option-drift --site {resolved_site} "
                        f"--doctype <doctype> --field <fieldname> --json"
                    ),
                    "approval_required": False,
                    "description": "Re-run the scan for one field to confirm the stored values.",
                },
                {
                    "command": "bench migrate",
                    "approval_required": True,
                    "description": (
                        "Re-add the removed option or migrate the stored values BEFORE "
                        "migrating: a stored value outside the options makes the "
                        "affected documents un-editable."
                    ),
                },
            ],
            site=resolved_site,
            start_time=start,
        )
        emit_envelope(envelope)

    # Human-readable fallback (no --json).
    click.echo("Select-Option-Drift: stored values a Select field no longer allows")
    click.echo(
        f"Site: {resolved_site}  |  Doctypes scanned: {stats['doctypes_scanned']}  |  "
        f"Constrained fields scanned: {stats['fields_scanned']}  |  "
        f"Drifted fields: {len(drift)}"
    )
    if not findings:
        click.echo("No select-option drift found.")
    for finding in findings:
        click.echo(f"  [{finding.severity}] {finding.id}: {finding.title}")
        click.echo(f"      {finding.description}")
    if truncated > 0:
        click.echo(f"  ... {truncated} more finding(s) not shown (use --limit).")
    click.echo("Use --json for v0.5 envelope output.")

    # Same status -> exit-code mapping in both modes, so CI gates work
    # regardless of whether --json was passed.
    raise SystemExit(EXIT_CODE_MAPPING.get(status, 0))
