"""app-migrator-audit-integrity: cross-app integrity checks derived from real audits.

This command is the home of the checks that two production audits asked for
(``amb_w_tds`` @ 98e7d47 and ``rnd_warehouse_management`` @ 95a913a, both
2026-11-05). Each check answers one question that neither app could answer
about itself:

- ``shared-fixture-ownership`` — do two apps ship the same Custom Field or
  Property Setter, so migrate order decides the surviving definition?
- (further checks are registered as separate modules under
  ``app_migrator/commands/_integrity/checks/``)

The detection cores are **import-safe and bench-free** so they can be
unit-tested in-process; only this click wrapper touches the envelope/exit
path. That split is inherited from ``module_conflicts.py`` (W2(d)).
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

import click

try:
    from frappe.commands import pass_context
except ImportError:  # pragma: no cover - bench-free import path
    def pass_context(f):
        return f

from ._envelope import EXIT_CODE_MAPPING, emit_envelope, make_envelope
from .._integrity import DEFAULT_APPS_ROOT, DEFAULT_FINDING_LIMIT, SEVERITY_RANK, Inventory
from .._integrity.checks import CHECKS

COMMAND_NAME = "audit-integrity"


def _selected_checks(check_names: List[str]):
    """Resolve the requested check ids to specs.

    An empty request means "all checks". An unknown id is an error — silently
    running fewer checks than asked for is how a gap becomes invisible.
    """
    if not check_names:
        return list(CHECKS)
    wanted = []
    for raw in check_names:
        for part in raw.split(","):
            part = part.strip()
            if part:
                wanted.append(part)
    by_id = {spec.check_id: spec for spec in CHECKS}
    unknown = [name for name in wanted if name not in by_id]
    if unknown:
        raise click.BadParameter(
            f"unknown check(s): {', '.join(sorted(set(unknown)))}. "
            f"Available: {', '.join(sorted(by_id))}"
        )
    # Preserve registry order, not request order, so output is stable.
    return [spec for spec in CHECKS if spec.check_id in set(wanted)]


def _min_severity_rank(severity: str) -> int:
    return SEVERITY_RANK.get(severity, 0)


def run_checks(
    inventory: Inventory,
    check_names: List[str],
    severity: str = "info",
    limit: int = DEFAULT_FINDING_LIMIT,
) -> Dict[str, Any]:
    """Run the selected checks and return an aggregated result.

    Returns a dict with ``findings`` (list of envelope-shaped finding dicts),
    ``per_check`` (stats per check) and ``total`` (true finding count, before
    truncation).
    """
    specs = _selected_checks(check_names)
    cutoff = _min_severity_rank(severity)
    all_findings: List[Dict[str, Any]] = []
    per_check: Dict[str, Any] = {}
    total = 0

    for spec in specs:
        result = spec.run(inventory)
        kept = [
            f for f in result.findings
            if SEVERITY_RANK.get(f.severity, 99) <= cutoff
        ]
        ordered = result.ordered_findings(limit=limit)
        # ordered is already truncated to `limit`; re-apply the severity filter
        # in the same worst-first order.
        ordered = [
            f for f in ordered
            if SEVERITY_RANK.get(f.severity, 99) <= cutoff
        ]
        total += len(kept)
        per_check[spec.check_id] = {
            "title": spec.title,
            "findings": len(kept),
            "stats": result.stats,
        }
        all_findings.extend(f.to_dict() for f in ordered)

    return {
        "findings": all_findings,
        "per_check": per_check,
        "total": total,
        "checks_run": [spec.check_id for spec in specs],
    }


@click.command('app-migrator-audit-integrity')
@click.option('--site', default=None, help='Site name (informational; not required)')
@click.option('--json', 'as_json', is_flag=True, help='Emit v0.5 envelope JSON')
@click.option('--apps-root', default=None, help='bench apps/ directory to scan')
@click.option('--check', 'check_names', multiple=True,
              help='Only run this check (repeatable, or comma-separated). Default: all.')
@click.option('--severity', default='info',
              type=click.Choice(['high', 'medium', 'low', 'info'], case_sensitive=False),
              help='Only report findings at or above this severity.')
@click.option('--limit', default=DEFAULT_FINDING_LIMIT, show_default=True, type=int,
              help='Max findings carried in the envelope')
@pass_context
def app_migrator_audit_integrity(context, site, as_json, apps_root, check_names, severity, limit):
    """Cross-app integrity checks derived from the amb_w_tds / rnd_warehouse_management audits."""
    start = time.time()

    resolved_root = apps_root or DEFAULT_APPS_ROOT
    inventory = Inventory(apps_root=resolved_root)

    try:
        outcome = run_checks(inventory, list(check_names), severity=severity, limit=limit)
    except click.BadParameter:
        raise
    except Exception as exc:  # pragma: no cover - defensive
        envelope = make_envelope(
            command=COMMAND_NAME,
            status="error",
            summary=f"audit-integrity failed: {exc}",
            findings=[],
            evidence=[{"kind": "error", "error": str(exc), "type": type(exc).__name__}],
            site=site,
            start_time=start,
        )
        if as_json:
            emit_envelope(envelope)
        raise click.ClickException(f"audit-integrity failed: {exc}")

    findings = outcome["findings"]
    total = outcome["total"]
    truncated = total - len(findings)

    if as_json:
        status = "warn" if total else "ok"
        summary = (
            f"audit-integrity: {total} finding(s) across "
            f"{len(outcome['checks_run'])} check(s) on {len(inventory.apps)} app(s)"
            + (f" (carrying {len(findings)})" if truncated > 0 else "")
        )
        envelope = make_envelope(
            command=COMMAND_NAME,
            status=status,
            summary=summary,
            findings=findings,
            evidence=[
                {"kind": "per_check", "checks": outcome["per_check"]},
                {"kind": "scan_params",
                 "apps_root": resolved_root,
                 "checks": outcome["checks_run"],
                 "severity": severity,
                 "findings_truncated": max(truncated, 0)},
                {"kind": "scan_stats", **inventory.stats()},
            ],
            suggested_next_commands=[
                {
                    "command": "bench app-migrator audit-integrity --json",
                    "approval_required": False,
                    "description": "Re-run the full integrity sweep and diff the finding ids.",
                },
                {
                    "command": "bench app-migrator audit-app-integrity --check shared-fixture-ownership",
                    "approval_required": True,
                    "description": (
                        "Decide a single owner for each shared fixture record before "
                        "changing anything; fixture edits are destructive to the other app."
                    ),
                },
            ],
            site=site,
            start_time=start,
        )
        emit_envelope(envelope)

    # Human-readable fallback (no --json).
    click.echo("Audit-Integrity: cross-app integrity checks")
    click.echo(
        f"Apps root: {resolved_root}  |  Apps scanned: {len(inventory.apps)}  |  "
        f"Checks run: {len(outcome['checks_run'])}"
    )
    for check_id, info in outcome["per_check"].items():
        click.echo(f"  {check_id}: {info['findings']} finding(s)")
    if not findings:
        click.echo("No integrity findings.")
    else:
        for finding in findings:
            click.echo(f"  [{finding['severity']}] {finding['id']}: {finding['title']}")
            click.echo(f"      {finding['description']}")
    if truncated > 0:
        click.echo(f"  ... {truncated} more finding(s) not shown (use --limit).")
    click.echo("Use --json for v0.5 envelope output.")

    # Same status -> exit-code mapping in both modes, so CI gates work
    # regardless of whether --json was passed.
    raise SystemExit(EXIT_CODE_MAPPING.get("warn" if total else "ok", 0))
