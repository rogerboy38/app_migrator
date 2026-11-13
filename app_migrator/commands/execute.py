"""app-migrator-execute command (T1.8.2 — extracted from __init__.py)"""

import json
import time

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f
from ._envelope import emit_envelope, make_envelope
from ._shared import ProgressTracker


def _extract_doctypes(plan):
    """Return a flat list of {'name', 'target_app'} dicts from either plan schema.

    W3 finding #3: `generate-plan` and `execute` used incompatible plan schemas,
    so the canonical generate->execute pipeline raised ``KeyError: 'doctypes'``.
    This shim consumes both:

    - Legacy flat schema:  ``plan['doctypes'] = [{'name', 'target_app'}, ...]``
    - Intelligent phased schema (generate-plan): ``plan['phases'][i]['doctypes'] =
      ['DocType Name', ...]`` with the target app at ``plan['target_app']``.

    DocType entries may be plain strings (phased) or dicts (flat); both normalize
    to ``{'name': <str>, 'target_app': <str|None>}``.
    """
    target = plan.get("target_app") or plan.get("target")

    def _norm(dt):
        if isinstance(dt, dict):
            return {"name": dt.get("name"), "target_app": dt.get("target_app", target)}
        return {"name": dt, "target_app": target}

    if "doctypes" in plan:
        return [_norm(dt) for dt in plan["doctypes"]]
    return [_norm(dt) for phase in plan.get("phases", []) for dt in phase.get("doctypes", [])]


@click.command('app-migrator-execute')
@click.option('--json', 'as_json', is_flag=True, help='Emit v0.5 envelope JSON (report-only preview of the resolved plan)')
@click.option('--site', required=True, help='Site name')
@click.option('--plan', 'plan_file', required=True, help='Migration plan file')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_execute(context, as_json, site, plan_file, dry_run):
    """Execute a migration plan"""
    start = time.time()
    if not as_json:
        mode = "DRY-RUN" if dry_run else "APPLY"
        print(f"🚀 Executing migration [{mode}]")
        print("=" * 60)

    try:
        with open(plan_file) as f:
            plan = json.load(f)
    except Exception as e:
        if as_json:
            emit_envelope(make_envelope(
                command="execute",
                status="error",
                summary=f"execute failed: cannot load plan ({type(e).__name__})",
                findings=[{"id": "execute-plan-load-error", "title": "Plan load failed",
                           "severity": "high", "description": str(e)}],
                site=site, start_time=start,
            ))
        raise

    # --json is report-only: preview the resolved plan as an envelope, never apply.
    if as_json:
        doctypes = _extract_doctypes(plan)
        if doctypes:
            names = ", ".join(d["name"] for d in doctypes[:10])
            findings = [{"id": "execute-planned-doctypes", "title": "DocTypes to migrate",
                         "severity": "info",
                         "description": f"{len(doctypes)} doctype(s): {names}" + (" ..." if len(doctypes) > 10 else "")}]
        else:
            findings = [{"id": "execute-empty-plan", "title": "Plan resolved to no doctypes",
                         "severity": "warn", "description": "The plan resolved to 0 doctypes to migrate."}]
        emit_envelope(make_envelope(
            command="execute",
            status="ok" if doctypes else "warn",
            summary=f"execute preview: {len(doctypes)} doctype(s) resolved from plan (report-only, no changes applied)",
            findings=findings,
            evidence=[{"type": "resolved_doctypes", "data": doctypes}],
            suggested_next_commands=[{
                "command": f"bench app-migrator execute --site {site} --plan {plan_file} --apply",
                "approval_required": True,
                "description": "Apply the migration (destructive).",
            }],
            site=site, start_time=start,
        ))

    if not dry_run:
        if not click.confirm("⚠️ This will modify your database. Continue?"):
            print("❌ Cancelled")
            return

    frappe.init(site=site)
    frappe.connect()

    doctypes = _extract_doctypes(plan)
    tracker = ProgressTracker("Migration", len(doctypes))

    for dt in doctypes:
        tracker.update(f"Processing {dt['name']}")
        if not dry_run:
            frappe.db.sql("""
                UPDATE `tabDocType` SET module = %s WHERE name = %s
            """, (dt["target_app"], dt["name"]))

    if not dry_run:
        frappe.db.commit()

    frappe.db.close()
    tracker.complete()

    if dry_run:
        print("\n✅ Dry-run complete. Run with --apply to execute.")
    else:
        print(f"\n✅ Migration complete! Run 'bench --site {site} migrate'")
