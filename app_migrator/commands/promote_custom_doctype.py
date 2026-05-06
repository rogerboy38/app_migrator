"""app-migrator promote-custom-doctype command

Promotes Customize Form / fixture-extracted custom DocTypes to first-class
source-controlled DocTypes — solves the "import_controller silently returns
BASE Document" bug (Frappe issue #16328 family, unresolved since 2015).

Pipeline (5 phases):
  1. INSPECT     — snapshot tabDocType, tabDocField, tabCustom Field, tabProperty Setter
  2. CLASSIFY    — REDUNDANT / ABSORB / ORPHAN per row
  3. INTEGRATE   — write to JSON (target=absorb), strip fixture metadata, custom→0
  4. CLEAR       — DELETE redundant DB rows; nuclear tabDocField rebuild on conflict
  5. RESYNC      — bench export-fixtures + bench migrate, verify import_controller

Default --dry-run (read-only). Use --apply to commit changes.
Snapshots saved to <bench>/sites/snapshots/promote_<slug>_<hash>.json.
"""
import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f


INT_PROPS = {"in_list_view", "in_standard_filter", "reqd", "hidden",
             "read_only", "bold", "translatable", "no_copy",
             "print_hide", "report_hide", "allow_in_quick_entry"}

FIXTURE_METADATA_KEYS = ("creation", "idx", "modified_by", "owner")

FRAPPE_INTERNAL_APPS = {"frappe", "erpnext", "hrms", "payments", "raven",
                        "raven_ai_agent", "rnd_warehouse_management", "amb_print",
                        "erpnext_mexico_compliance", "telephony", "lms",
                        "helpdesk", "crm", "drive", "builder", "insights",
                        "print_designer", "email_delivery_service",
                        "mexico_einvoice", "utility_billing", "crm_host",
                        "app_migrator"}


@click.command("app-migrator-promote-custom-doctype")
@click.option("--site", required=True, help="Site name")
@click.option("--doctype", help='Single DocType to promote (e.g. "Container Barrels")')
@click.option("--app", help="Promote ALL custom=1 DocTypes in this app")
@click.option("--target", type=click.Choice(["absorb"]), default="absorb",
              help="Where to write customizations (absorb = into doctype.json)")
@click.option("--apply", is_flag=True, help="Apply changes (default is --dry-run)")
@click.option("--skip-frappe-internal", is_flag=True, default=True,
              help="Skip frappe/erpnext/hrms core apps (default: skip)")
@click.option("--auto-export-fixtures", is_flag=True, default=False,
              help="Run bench export-fixtures --app <app> after absorb (recommended)")
@click.option("--auto-migrate", is_flag=True, default=False,
              help="Run bench migrate after absorb (recommended)")
@click.option("--snapshot-dir",
              default="/home/frappe/frappe-bench/sites/snapshots",
              help="Directory for rollback snapshots")
@click.option("--confirm-each", is_flag=True, default=False,
              help="Interactive confirmation per doctype")
@pass_context
def app_migrator_promote_custom_doctype(context, site, doctype, app, target,
                                        apply, skip_frappe_internal,
                                        auto_export_fixtures, auto_migrate,
                                        snapshot_dir, confirm_each):
    """Promote Customize Form / fixture-extracted custom DocTypes to standard.

    Solves the "import_controller silently returns BASE Document" bug by
    absorbing CF/PS rows into source JSON and clearing DB drift.

    Examples:

      \b
      # Single doctype, dry-run:
      bench --site <site> app-migrator promote-custom-doctype \\
        --doctype "Container Barrels"

      \b
      # Single doctype, full workflow:
      bench --site <site> app-migrator promote-custom-doctype \\
        --doctype "Container Barrels" --apply \\
        --auto-export-fixtures --auto-migrate

      \b
      # Bulk: all custom=1 DocTypes in an app:
      bench --site <site> app-migrator promote-custom-doctype \\
        --app amb_w_spc --apply \\
        --auto-export-fixtures --auto-migrate
    """
    if not doctype and not app:
        click.secho("Error: must specify --doctype or --app", fg="red")
        raise click.Abort()
    if doctype and app:
        click.secho("Error: --doctype and --app are mutually exclusive", fg="red")
        raise click.Abort()

    dry_run = not apply
    mode = "DRY-RUN" if dry_run else "APPLY"

    click.secho("\n" + "=" * 78, fg="cyan")
    click.secho(f"  PROMOTE CUSTOM DOCTYPE  —  {mode}", fg="cyan", bold=True)
    click.secho("=" * 78, fg="cyan")

    frappe.init(site=site)
    frappe.connect()

    # ── Build target list ──
    if doctype:
        targets = [doctype]
    else:
        rows = frappe.db.sql("""
            SELECT dt.name, COALESCE(md.app_name, dt.app) AS app
            FROM tabDocType dt
            LEFT JOIN `tabModule Def` md ON md.name = dt.module
            WHERE dt.custom = 1
              AND COALESCE(md.app_name, dt.app) = %s
            ORDER BY dt.name
        """, app, as_dict=True)
        targets = [r.name for r in rows
                   if not (skip_frappe_internal and (r.app or "") in FRAPPE_INTERNAL_APPS)]
        if not targets:
            click.secho(f"\nNo custom=1 DocTypes found in app '{app}'", fg="yellow")
            return

    click.secho(f"\nTargets: {len(targets)}", fg="cyan")
    for t in targets:
        click.echo(f"  • {t}")

    if confirm_each and not dry_run:
        if not click.confirm("\nProceed?", default=True):
            click.secho("Aborted.", fg="yellow")
            return

    snap_path = Path(snapshot_dir)
    if apply:
        snap_path.mkdir(parents=True, exist_ok=True)

    apps_touched = set()
    successes = []
    failures = []

    for dt_name in targets:
        if confirm_each and not click.confirm(f"\nProcess '{dt_name}'?", default=True):
            click.secho(f"  Skipped {dt_name}", fg="yellow")
            continue
        try:
            result = _process_doctype(dt_name, target, dry_run, snap_path)
            apps_touched.add(result["app"])
            successes.append(dt_name)
        except Exception as e:
            click.secho(f"\n  ✗ FAILED for {dt_name}: {type(e).__name__}: {e}", fg="red")
            failures.append((dt_name, f"{type(e).__name__}: {e}"))

    # ── Post-action: export-fixtures + migrate ──
    if apply and auto_export_fixtures and apps_touched:
        click.secho(f"\n{'=' * 78}", fg="cyan")
        click.secho("  EXPORT FIXTURES (locks in cleanup)", fg="cyan")
        click.secho("=" * 78, fg="cyan")
        for a in sorted(apps_touched):
            click.secho(f"\n  bench --site {site} export-fixtures --app {a}", fg="white")
            ret = subprocess.run(
                ["bench", "--site", site, "export-fixtures", "--app", a],
                capture_output=True, text=True,
                cwd="/home/frappe/frappe-bench",
            )
            if ret.stdout:
                click.echo(ret.stdout)
            if ret.returncode != 0:
                click.secho(f"  ✗ export-fixtures failed: {ret.stderr}", fg="red")

    if apply and auto_migrate:
        click.secho(f"\n{'=' * 78}", fg="cyan")
        click.secho("  BENCH MIGRATE", fg="cyan")
        click.secho("=" * 78, fg="cyan")
        ret = subprocess.run(["bench", "--site", site, "migrate"],
                             capture_output=True, text=True,
                             cwd="/home/frappe/frappe-bench")
        click.echo("\n".join(ret.stdout.splitlines()[-12:]))
        if ret.returncode != 0:
            click.secho("\n  ⚠️  migrate failed — likely needs nuclear tabDocField rebuild:", fg="yellow")
            click.secho("  Re-run after:", fg="yellow")
            for dt_name in successes:
                click.secho(
                    f"    bench --site {site} mariadb -e \"DELETE FROM tabDocField WHERE parent='{dt_name}';\"",
                    fg="yellow",
                )
            click.echo(ret.stderr[-1500:])

    # ── Verify ──
    if apply and successes:
        click.secho(f"\n{'=' * 78}", fg="cyan")
        click.secho("  VERIFY", fg="cyan")
        click.secho("=" * 78, fg="cyan")
        from frappe.model.base_document import import_controller
        for dt_name in successes:
            try:
                ctrl = import_controller(dt_name)
                ok_ctrl = ctrl.__module__ != "frappe.model.document"
                row = frappe.db.sql("SELECT custom, app FROM tabDocType WHERE name=%s",
                                    dt_name, as_dict=True)[0]
                cf = frappe.db.count("Custom Field", {"dt": dt_name})
                ps = frappe.db.count("Property Setter", {"doc_type": dt_name})
                ok = ok_ctrl and row.custom == 0 and cf == 0 and ps == 0
                marker = "✓" if ok else "FIX"
                click.echo(f"  [{marker}] {dt_name:35} custom={row.custom} "
                           f"app={(row.app or '-'):12} CF={cf} PS={ps} "
                           f"ctrl={ctrl.__name__}")
            except Exception as e:
                click.secho(f"  [?] {dt_name}: verify error {e}", fg="yellow")

    # ── Summary ──
    click.secho(f"\n{'=' * 78}", fg="cyan")
    click.secho("  SUMMARY", fg="cyan", bold=True)
    click.secho("=" * 78, fg="cyan")
    click.echo(f"  Mode:       {mode}")
    click.echo(f"  Targets:    {len(targets)}")
    click.echo(f"  Successes:  {len(successes)}")
    if failures:
        click.secho(f"  Failures:   {len(failures)}", fg="red")
        for dt_name, err in failures:
            click.echo(f"    - {dt_name}: {err}")
    if dry_run:
        click.secho("\n  This was a DRY-RUN. To apply, re-run with --apply", fg="yellow")
    elif successes:
        click.secho(f"\n  ✓ Promoted {len(successes)} DocType(s) to standard", fg="green")


# ─── Pipeline phases ────────────────────────────────────────────────────────

def _process_doctype(dt_name, target, dry_run, snapshot_dir):
    row = frappe.db.sql("""
        SELECT dt.name, dt.module, dt.custom,
               COALESCE(md.app_name, dt.app) AS app
        FROM tabDocType dt
        LEFT JOIN `tabModule Def` md ON md.name = dt.module
        WHERE dt.name = %s
    """, dt_name, as_dict=True)[0]

    app_name = row.app
    if not app_name:
        raise RuntimeError(f"Cannot resolve app for {dt_name} (module={row.module})")

    bench_root = Path("/home/frappe/frappe-bench")
    app_root = bench_root / "apps" / app_name / app_name
    slug = frappe.scrub(dt_name)
    candidates = list(app_root.rglob(f"doctype/{slug}/{slug}.json"))
    if not candidates:
        raise RuntimeError(f"JSON not found for {dt_name} under {app_root}")
    json_path = candidates[0]

    click.secho(f"\n┌─── {dt_name} ───", fg="cyan")
    click.echo(f"│  app:        {app_name}")
    click.echo(f"│  module:     {row.module}")
    click.echo(f"│  json:       {json_path.relative_to(bench_root)}")
    click.echo(f"│  DB custom:  {row.custom}")

    snapshot = _build_snapshot(dt_name, json_path)
    snap_hash = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]

    if not dry_run:
        snap_file = snapshot_dir / f"promote_{slug}_{snap_hash}.json"
        snap_file.write_text(json.dumps(snapshot, indent=2, default=str))
        click.echo(f"│  snapshot:   {snap_file.name}")
    else:
        click.echo(f"│  snapshot:   (would write promote_{slug}_{snap_hash}.json)")

    ps_decisions = _classify_property_setters(snapshot["ps_rows"], snapshot["json_fields"])
    cf_decisions = _classify_custom_fields(snapshot["cf_rows"], snapshot["json_fields"])

    ps_redundant = sum(1 for d in ps_decisions if d["verdict"] == "REDUNDANT")
    ps_absorb = sum(1 for d in ps_decisions if d["verdict"] == "ABSORB")
    ps_orphan = sum(1 for d in ps_decisions if d["verdict"] == "ORPHAN")
    cf_redundant = sum(1 for d in cf_decisions if d["verdict"] == "REDUNDANT")
    cf_absorb = sum(1 for d in cf_decisions if d["verdict"] == "ABSORB")

    click.echo(f"│  PS rows:    {len(snapshot['ps_rows'])} "
               f"(REDUNDANT={ps_redundant}, ABSORB={ps_absorb}, ORPHAN={ps_orphan})")
    click.echo(f"│  CF rows:    {len(snapshot['cf_rows'])} "
               f"(REDUNDANT={cf_redundant}, ABSORB={cf_absorb})")

    if dry_run:
        for d in ps_decisions:
            ps = d["ps"]
            scope = ps.get("field_name") or "(doctype)"
            click.echo(f"│    PS {d['verdict']:9} {scope}.{ps['property']}: "
                       f"{d.get('cur_val')!r} -> {d['new_val']!r}")
        for d in cf_decisions:
            cf = d["cf"]
            click.echo(f"│    CF {d['verdict']:9} {cf['fieldname']} ({cf['fieldtype']})")
        click.echo("└──── (dry-run, no changes)")
        return {"app": app_name}

    _apply_changes(dt_name, json_path, snapshot, ps_decisions, cf_decisions)
    click.secho("└──── ✓ promoted", fg="green")
    return {"app": app_name}


def _build_snapshot(dt_name, json_path):
    db_dt = frappe.db.sql("SELECT * FROM tabDocType WHERE name=%s", dt_name, as_dict=True)
    db_fields = frappe.db.sql("SELECT * FROM tabDocField WHERE parent=%s ORDER BY idx",
                              dt_name, as_dict=True)
    cf_rows = frappe.db.sql("SELECT * FROM `tabCustom Field` WHERE dt=%s",
                            dt_name, as_dict=True)
    ps_rows = frappe.db.sql("SELECT * FROM `tabProperty Setter` WHERE doc_type=%s",
                            dt_name, as_dict=True)
    with open(json_path) as f:
        j = json.load(f)
    return {
        "doctype": dt_name,
        "json_path": str(json_path),
        "db_dt": [dict(r) for r in db_dt],
        "db_fields": [dict(r) for r in db_fields],
        "cf_rows": [dict(r) for r in cf_rows],
        "ps_rows": [dict(r) for r in ps_rows],
        "json_def": j,
        "json_fields": j.get("fields", []),
    }


def _classify_property_setters(ps_rows, json_fields):
    fields_by_name = {f.get("fieldname"): f for f in json_fields if "fieldname" in f}
    decisions = []
    for ps in ps_rows:
        ps = dict(ps)
        raw = ps["value"]
        new_val = int(raw) if (ps["property"] in INT_PROPS and str(raw).isdigit()) else raw

        target_field = None
        if ps["doctype_or_field"] == "DocField" and ps["field_name"]:
            target_field = fields_by_name.get(ps["field_name"])

        if ps["doctype_or_field"] == "DocField" and not target_field:
            verdict, cur_val = "ORPHAN", None
        elif target_field is not None:
            cur_val = target_field.get(ps["property"])
            verdict = ("REDUNDANT" if (cur_val == new_val
                                       or (cur_val in (None, 0) and new_val == 0))
                       else "ABSORB")
        else:
            cur_val = None
            verdict = "ABSORB"

        decisions.append({"ps": ps, "verdict": verdict,
                          "new_val": new_val, "cur_val": cur_val})
    return decisions


def _classify_custom_fields(cf_rows, json_fields):
    fields_by_name = {f.get("fieldname"): f for f in json_fields if "fieldname" in f}
    decisions = []
    for cf in cf_rows:
        cf = dict(cf)
        verdict = "REDUNDANT" if cf["fieldname"] in fields_by_name else "ABSORB"
        decisions.append({"cf": cf, "verdict": verdict})
    return decisions


def _apply_changes(dt_name, json_path, snapshot, ps_decisions, cf_decisions):
    json_path = Path(json_path)
    backup = json_path.with_suffix(
        json_path.suffix + datetime.now().strftime(".bak_%Y%m%d_%H%M%S")
    )
    shutil.copy2(json_path, backup)

    j = snapshot["json_def"]
    fields = j.get("fields", [])
    fields_by_name = {f.get("fieldname"): f for f in fields if "fieldname" in f}

    # PS absorptions
    for d in ps_decisions:
        ps = d["ps"]
        if d["verdict"] == "ABSORB":
            if ps["doctype_or_field"] == "DocField":
                tf = fields_by_name.get(ps["field_name"])
                if tf:
                    tf[ps["property"]] = d["new_val"]
            else:
                j[ps["property"]] = d["new_val"]

    # CF absorptions
    for d in cf_decisions:
        cf = d["cf"]
        if d["verdict"] == "ABSORB":
            new_field = {"fieldname": cf["fieldname"], "label": cf.get("label"),
                         "fieldtype": cf["fieldtype"]}
            for k in ("options", "reqd", "in_list_view", "depends_on", "fetch_from",
                      "default", "description", "hidden", "read_only"):
                v = cf.get(k)
                if v not in (None, "", 0):
                    new_field[k] = v
            idx = len(fields)
            if cf.get("insert_after"):
                for i, ff in enumerate(fields):
                    if ff.get("fieldname") == cf["insert_after"]:
                        idx = i + 1
                        break
            fields.insert(idx, new_field)
            fields_by_name[cf["fieldname"]] = new_field

    # Flip custom + strip fixture metadata
    j["fields"] = fields
    if j.get("custom") == 1:
        j["custom"] = 0
    for k in FIXTURE_METADATA_KEYS:
        j.pop(k, None)

    json_path.write_text(json.dumps(j, indent=1, sort_keys=False) + "\n")

    # CLEAR DB
    for d in ps_decisions:
        frappe.db.sql("DELETE FROM `tabProperty Setter` WHERE name=%s", d["ps"]["name"])
    for d in cf_decisions:
        frappe.db.sql("DELETE FROM `tabCustom Field` WHERE name=%s", d["cf"]["name"])
    frappe.db.sql("UPDATE tabDocType SET custom=0 WHERE name=%s AND custom=1", dt_name)
    frappe.db.commit()
    frappe.clear_cache()
