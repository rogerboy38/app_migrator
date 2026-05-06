"""app-migrator migrate-module command — Mode B (cross-app module add).

Moves a module from one Frappe app to another, with full cascade:
  - Filesystem move
  - Import path rewrites across all apps
  - modules.txt updates (both source and target)
  - DB updates (tabModule Def, tabDocType.app/.module, 6 ancillary tables)
  - bench migrate with retry-once-on-cache-miss

Reuses denest-app v4 hardening (word-boundary regex, SKIP_PATH_PATTERNS,
rewrite-before-move ordering, SQL_SAFE_UPDATES toggle).

Default --dry-run. --apply required for changes.

Usage:
  # Move module keeping its name (most common):
  bench app-migrator migrate-module \\
    --site <site> \\
    --source-app payments \\
    --source-module "Payment Gateways" \\
    --target-app payments_core

  # Move + rename during the move:
  bench app-migrator migrate-module \\
    --site <site> \\
    --source-app payments \\
    --source-module "Payment Gateways" \\
    --target-app payments_core \\
    --target-module "Gateway Integrations" \\
    --apply

Limitations (v1):
  - Cross-app hook entries (e.g. override_doctype_class lines in source app
    that reference the moved module) get their import paths rewritten in
    place, but are NOT relocated to target app's hooks.py. Manual cleanup
    of cross-app hook semantics may be needed post-migration.
  - Source app must use STANDARD layout (module folder NOT same name as app).
    If source has antipattern, run denest-app first.
"""
import json
import re
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


def _scrub(name):
    return name.strip().lower().replace(" ", "_").replace("-", "_")


# Reuse denest-app v3+v4 hardening
SKIP_PATH_PATTERNS = (
    "__pycache__",
    ".bak",
    "/archived/",
    "/backup/",
    "/backups/",
    "/_archive/",
    "/snapshots/",
    "/node_modules/",
    "/.git/",
)

MODULE_REF_TABLES = [
    ("tabReport",          False),
    ("tabPage",            False),
    ("tabDashboard",       False),
    ("`tabPrint Format`",  True),
    ("`tabClient Script`", True),
    ("`tabServer Script`", True),
]


@click.command("app-migrator-migrate-module")
@click.option("--site", required=True, help="Site name (for DB updates)")
@click.option("--source-app", required=True, help="App that currently owns the module")
@click.option("--source-module", required=True,
              help="Module to migrate (e.g., 'Payment Gateways')")
@click.option("--target-app", required=True,
              help="App to move the module into (must already exist)")
@click.option("--target-module",
              help="New module name (optional, defaults to source-module). "
                   "MUST scrub to a value DIFFERENT from target-app name.")
@click.option("--apply", is_flag=True, help="Apply changes (default --dry-run)")
@click.option("--bench-root", default="/home/frappe/frappe-bench")
@click.option("--snapshot-dir",
              default="/home/frappe/frappe-bench/sites/snapshots")
@click.option("--auto-fix-orphans", is_flag=True, default=False,
              help="Auto-collapse CASE_MISMATCH orphans found during pre-flight")
@pass_context
def app_migrator_migrate_module(context, site, source_app, source_module,
                                  target_app, target_module, apply,
                                  bench_root, snapshot_dir, auto_fix_orphans):
    """Migrate a module from one Frappe app to another (Mode B: cross-app add)."""
    bench_root = Path(bench_root)
    target_module = target_module or source_module
    src_slug = _scrub(source_module)
    tgt_slug = _scrub(target_module)
    dry_run = not apply
    mode = "DRY-RUN" if dry_run else "APPLY"

    click.secho("\n" + "=" * 78, fg="cyan")
    click.secho(f"  MIGRATE-MODULE — {source_app}.{src_slug}  →  "
                f"{target_app}.{tgt_slug}  [{mode}]",
                fg="cyan", bold=True)
    click.secho("=" * 78, fg="cyan")

    # ── Validation ──
    src_app_pkg = bench_root / "apps" / source_app / source_app
    tgt_app_pkg = bench_root / "apps" / target_app / target_app

    if not src_app_pkg.exists():
        click.secho(f"\n✗ Source app not found: {src_app_pkg}", fg="red")
        raise click.Abort()
    if not tgt_app_pkg.exists():
        click.secho(f"\n✗ Target app not found: {tgt_app_pkg}", fg="red")
        click.secho(f"  Tip: bench app-migrator new-fresh-app "
                    f"--app-name {target_app} ...", fg="cyan")
        raise click.Abort()

    if tgt_slug == target_app:
        click.secho("\n✗ ANTIPATTERN BLOCKED:", fg="red", bold=True)
        click.secho(f"  scrub('{target_module}') = '{tgt_slug}' equals "
                    f"target app '{target_app}'.", fg="red")
        click.secho(f"  Use --target-module to pick a different name "
                    f"(e.g., '{target_module} Core').", fg="cyan")
        raise click.Abort()

    src_module_folder = src_app_pkg / src_slug
    if not src_module_folder.exists():
        click.secho(f"\n✗ Source module folder not found: {src_module_folder}",
                    fg="red")
        nested_alt = src_app_pkg / source_app / src_slug
        if nested_alt.exists():
            click.secho(f"  HINT: source app uses nested layout; module lives at "
                        f"{nested_alt}", fg="cyan")
            click.secho(f"  Run denest-app on {source_app} first to fix the "
                        f"antipattern.", fg="cyan")
        raise click.Abort()

    tgt_module_folder = tgt_app_pkg / tgt_slug
    if tgt_module_folder.exists():
        click.secho(f"\n✗ Target folder already exists: {tgt_module_folder}",
                    fg="red")
        raise click.Abort()

    src_modules_txt = src_app_pkg / "modules.txt"
    src_modules = [m.strip() for m in src_modules_txt.read_text().splitlines()
                   if m.strip() and not m.startswith("#")]
    if source_module not in src_modules:
        click.secho(f"\n✗ '{source_module}' not in {src_modules_txt}", fg="red")
        click.secho(f"  Available: {src_modules}", fg="cyan")
        raise click.Abort()

    tgt_modules_txt = tgt_app_pkg / "modules.txt"
    tgt_modules = []
    if tgt_modules_txt.exists():
        tgt_modules = [m.strip() for m in tgt_modules_txt.read_text().splitlines()
                       if m.strip() and not m.startswith("#")]
    if target_module in tgt_modules:
        click.secho(f"\n✗ '{target_module}' already exists in {tgt_modules_txt}",
                    fg="red")
        raise click.Abort()

    frappe.init(site=site)
    frappe.connect()
    # ----- v3: orphan pre-flight (Task #27) -------------------------------
    click.secho("\n  Pre-flight: scanning for orphan DocTypes on involved modules...", fg="cyan")

    def _scrub_pf(s):
        return (s or "").lower().replace(" ", "_").replace("-", "_")

    involved = {source_module, target_module} if target_module else {source_module}
    involved_scrubbed = {_scrub_pf(m) for m in involved}

    stranded = frappe.db.sql("""
        SELECT dt.name, dt.module, dt.app
        FROM `tabDocType` dt
        LEFT JOIN `tabModule Def` md ON md.name = dt.module
        WHERE md.name IS NULL AND dt.module IN %(mods)s
    """, {"mods": tuple(involved) or ("__none__",)}, as_dict=True)

    md_rows = frappe.db.sql(
        "SELECT name FROM `tabModule Def` WHERE name IN %(mods)s "
        "OR LOWER(REPLACE(REPLACE(name,' ','_'),'-','_')) IN %(scrubbed)s",
        {"mods": tuple(involved) or ("__none__",),
         "scrubbed": tuple(involved_scrubbed) or ("__none__",)},
        as_dict=True,
    )
    by_key = {}
    for r in md_rows:
        by_key.setdefault(_scrub_pf(r["name"]), []).append(r["name"])
    case_mismatch = {k: v for k, v in by_key.items() if len(v) > 1}

    filesystem_orphans = []
    for mod in involved:
        scrubbed = _scrub_pf(mod)
        for app_check in (source_app, target_app):
            if not app_check:
                continue
            cand_nested = bench_root / "apps" / app_check / app_check / scrubbed
            cand_flat = bench_root / "apps" / app_check / scrubbed
            if not cand_nested.exists() and not cand_flat.exists():
                cnt = frappe.db.sql(
                    "SELECT COUNT(*) FROM `tabDocType` WHERE module=%s AND app=%s",
                    (mod, app_check),
                )[0][0]
                if cnt:
                    filesystem_orphans.append({"module": mod, "app": app_check, "doctype_count": cnt})

    has_orphans = bool(stranded or case_mismatch or filesystem_orphans)
    if not has_orphans:
        click.secho("  ✓ No orphans on involved modules", fg="green")
    else:
        click.secho("\n  ⚠ Orphan DocTypes detected on involved modules:", fg="yellow")
        if stranded:
            click.secho(f"    STRANDED: {len(stranded)} DocType(s) reference a missing Module Def", fg="yellow")
            for r in stranded[:5]:
                click.secho(f"      - {r['name']} (module={r['module']}, app={r['app']})", fg="yellow")
        if case_mismatch:
            click.secho(f"    CASE_MISMATCH: {len(case_mismatch)} group(s)", fg="yellow")
            for key, names in case_mismatch.items():
                click.secho(f"      - {key}: {names}", fg="yellow")
        if filesystem_orphans:
            click.secho(f"    FILESYSTEM: {len(filesystem_orphans)} module(s) in DB without source folder", fg="yellow")
            for fo in filesystem_orphans:
                click.secho(f"      - {fo['module']} (app={fo['app']}, doctypes={fo['doctype_count']})", fg="yellow")

        if stranded or filesystem_orphans:
            click.secho(
                "\n  ✗ Aborting: STRANDED/FILESYSTEM orphans need human review.\n"
                f"    Run: bench app-migrator audit-orphan-doctypes --site {site}\n"
                "    Resolve orphans, then re-run migrate-module.",
                fg="red",
            )
            if apply:
                import sys as _sys
                _sys.exit(1)
            else:
                click.secho("    (would abort in --apply mode)", fg="yellow")

        if case_mismatch and not auto_fix_orphans:
            click.secho(
                "\n  ✗ Aborting: CASE_MISMATCH orphans found.\n"
                f"    Run: bench app-migrator audit-orphan-doctypes --site {site}\n"
                "    Then re-run with --auto-fix-orphans to clean inline.",
                fg="red",
            )
            if apply:
                import sys as _sys
                _sys.exit(1)
            else:
                click.secho("    (would abort in --apply mode)", fg="yellow")

        if case_mismatch and auto_fix_orphans and apply:
            click.secho("\n  → --auto-fix-orphans: cleaning CASE_MISMATCH orphans...", fg="cyan")
            for _key, names in case_mismatch.items():
                ugly = [n for n in names if n != _scrub_pf(n)]
                clean = [n for n in names if n == _scrub_pf(n)]
                if not clean:
                    keep, drop_list = names[0], names[1:]
                else:
                    keep, drop_list = clean[0], ugly or [n for n in names if n != clean[0]]
                for drop_name in drop_list:
                    click.secho(f"    collapsing '{drop_name}' → '{keep}'", fg="cyan")
                    frappe.db.sql("UPDATE tabDocType SET module=%s WHERE module=%s", (keep, drop_name))
                    frappe.db.sql("UPDATE `tabCustom Field` SET module=%s WHERE module=%s", (keep, drop_name))
                    frappe.db.sql("UPDATE `tabProperty Setter` SET module=%s WHERE module=%s", (keep, drop_name))
                    frappe.db.sql("DELETE FROM `tabModule Def` WHERE name=%s", drop_name)
            frappe.db.commit()
            click.secho("    ✓ CASE_MISMATCH orphans collapsed", fg="green")
    # ----- end v3 orphan pre-flight ---------------------------------------




    # ── Build cascade plan ──
    old_pkg = f"{source_app}.{src_slug}"
    new_pkg = f"{target_app}.{tgt_slug}"
    pattern = re.compile(rf"\b{re.escape(old_pkg)}\b")

    # Count DocTypes
    dt_dir = src_module_folder / "doctype"
    dt_names = []
    if dt_dir.exists():
        for d in sorted(dt_dir.iterdir()):
            if d.is_dir() and (d / f"{d.name}.json").exists():
                dt_names.append(d.name)
    dt_count = len(dt_names)

    # Find affected .py files across all apps
    affected_py_files = []
    for py_file in bench_root.rglob("apps/*/**/*.py"):
        py_str = str(py_file)
        if any(skip in py_str for skip in SKIP_PATH_PATTERNS):
            continue
        try:
            if pattern.search(py_file.read_text()):
                affected_py_files.append(py_file)
        except Exception:
            pass

    # ── Display plan ──
    click.secho("\n┌── PLAN ────", fg="cyan")
    click.echo("│  Move folder:")
    click.echo(f"│     {src_module_folder.relative_to(bench_root)}")
    click.echo(f"│  →  {tgt_module_folder.relative_to(bench_root)}")
    click.echo(f"│     ({dt_count} DocType(s))")
    click.echo(f"│  Rewrite imports: '\\b{old_pkg}\\b' → '{new_pkg}'")
    click.echo(f"│     in {len(affected_py_files)} .py file(s)")
    click.echo(f"│  modules.txt: remove '{source_module}' from {source_app}")
    click.echo(f"│  modules.txt: add '{target_module}' to {target_app}")
    click.echo("│  DB updates:")
    if target_module != source_module:
        click.echo("│    • tabModule Def: rename + change app_name")
    else:
        click.echo("│    • tabModule Def: change app_name only "
                   "(name unchanged)")
    click.echo(f"│    • tabDocType.app: '{source_app}' → '{target_app}' "
               f"({dt_count} rows max)")
    if target_module != source_module:
        click.echo(f"│    • tabDocType.module: '{source_module}' → "
                   f"'{target_module}' ({dt_count} rows max)")
        click.echo("│    • 6 ancillary tables: rename module column")
    click.echo("│  Clear __pycache__ + bench migrate (retry-once)")
    click.echo("└────")

    if dry_run:
        click.secho("\n  This was a DRY-RUN. To apply, re-run with --apply.",
                    fg="yellow")
        if dt_names and len(dt_names) <= 30:
            click.secho("\n  DocTypes that will move:", fg="cyan")
            for n in dt_names:
                click.echo(f"    • {n}")
        elif dt_names:
            click.secho(f"\n  DocTypes (first 15 of {len(dt_names)}):", fg="cyan")
            for n in dt_names[:15]:
                click.echo(f"    • {n}")
        if affected_py_files and len(affected_py_files) <= 30:
            click.secho("\n  Affected .py files:", fg="cyan")
            for f in affected_py_files:
                click.echo(f"    • {f.relative_to(bench_root)}")
        elif affected_py_files:
            click.secho(f"\n  Affected .py files (first 15 of "
                        f"{len(affected_py_files)}):", fg="cyan")
            for f in affected_py_files[:15]:
                click.echo(f"    • {f.relative_to(bench_root)}")
            click.echo(f"    ... and {len(affected_py_files) - 15} more")
        return

    # ─────────────────────────── APPLY ───────────────────────────
    snap = Path(snapshot_dir)
    snap.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_file = snap / f"migrate_module_{source_app}_{src_slug}_to_{target_app}_{ts}.json"
    snapshot_file.write_text(json.dumps({
        "source_app": source_app,
        "source_module": source_module,
        "target_app": target_app,
        "target_module": target_module,
        "src_module_folder": str(src_module_folder),
        "tgt_module_folder": str(tgt_module_folder),
        "affected_py_files": [str(f) for f in affected_py_files],
        "src_modules_txt_before": src_modules_txt.read_text(),
        "tgt_modules_txt_before": tgt_modules_txt.read_text() if tgt_modules_txt.exists() else "",
        "dt_names": dt_names,
        "timestamp": ts,
    }, indent=2))
    click.secho(f"\n  📦 Snapshot: {snapshot_file}", fg="green")

    # 1. Rewrite imports BEFORE move (denest-app v4 lesson)
    rewritten = 0
    for f in affected_py_files:
        try:
            content = f.read_text()
        except FileNotFoundError:
            click.echo(f"  ⚠ skipped (gone): {f}")
            continue
        new_content = pattern.sub(new_pkg, content)
        if new_content != content:
            f.write_text(new_content)
            rewritten += 1
    click.secho(f"  ✓ Rewrote imports in {rewritten} of "
                f"{len(affected_py_files)} file(s)", fg="green")

    # 2. Move folder cross-app
    shutil.move(str(src_module_folder), str(tgt_module_folder))
    click.secho(f"  ✓ Moved module folder to {target_app}", fg="green")

    # 3. Update modules.txt files
    new_src_modules = [m for m in src_modules if m != source_module]
    src_modules_txt.write_text(("\n".join(new_src_modules) + "\n")
                                if new_src_modules else "")
    click.secho(f"  ✓ Removed '{source_module}' from {source_app}/modules.txt",
                fg="green")

    new_tgt_modules = [*tgt_modules, target_module]
    tgt_modules_txt.write_text("\n".join(new_tgt_modules) + "\n")
    click.secho(f"  ✓ Added '{target_module}' to {target_app}/modules.txt",
                fg="green")

    # 4. DB updates
    frappe.db.sql("SET SQL_SAFE_UPDATES=0")
    try:
        # tabModule Def
        if target_module != source_module:
            frappe.db.sql("UPDATE `tabModule Def` SET name=%s, app_name=%s "
                          "WHERE name=%s",
                          (target_module, target_app, source_module))
        else:
            frappe.db.sql("UPDATE `tabModule Def` SET app_name=%s WHERE name=%s",
                          (target_app, source_module))

        # tabDocType
        if target_module != source_module:
            frappe.db.sql("UPDATE tabDocType SET app=%s, module=%s "
                          "WHERE module=%s",
                          (target_app, target_module, source_module))
        else:
            frappe.db.sql("UPDATE tabDocType SET app=%s WHERE module=%s",
                          (target_app, source_module))

        # Ancillary tables (only if module renamed)
        if target_module != source_module:
            for table_spec, has_name_col in MODULE_REF_TABLES:
                try:
                    where = "WHERE module=%s"
                    if has_name_col:
                        where += " AND name IS NOT NULL"
                    frappe.db.sql(
                        f"UPDATE {table_spec} SET module=%s {where}",
                        (target_module, source_module),
                    )
                except Exception as e:
                    click.echo(f"  ⚠ {table_spec} update skipped: {e}")
    finally:
        frappe.db.sql("SET SQL_SAFE_UPDATES=1")
    frappe.db.commit()
    click.secho("  ✓ Updated DB rows", fg="green")
    # 5. v2: export-fixtures from both apps — locks in the cleanup
    # Without this, fixture files (source/fixtures/custom_field.json etc.) still
    # reference DocTypes that moved to target. The next bench migrate would
    # re-import stale entries from the source's fixtures and re-create the
    # drift we just cleaned. Lesson harvested into intelligence_engine as
    # 'fixtures_regenerate_drift_after_db_cleanup'. The workflow rule:
    # "after cleaning DB, always run bench export-fixtures before bench migrate".
    click.secho("\n  Exporting fixtures (locks in the cleanup)...", fg="cyan")
    for app_to_export in (source_app, target_app):
        ret_ef = subprocess.run(
            ["bench", "--site", site, "export-fixtures", "--app", app_to_export],
            capture_output=True, text=True, cwd=str(bench_root),
        )
        if ret_ef.returncode == 0:
            click.secho(f"  ✓ Exported fixtures for {app_to_export}", fg="green")
        else:
            # Non-fatal: app may not have fixtures configured. Warn and continue.
            click.secho(f"  ⚠ export-fixtures for {app_to_export} returned non-zero "
                        f"(may have no fixtures configured — continuing)",
                        fg="yellow")

    # 6. Clear pycache (bench-wide for safety)
    cleared = 0
    for cache_dir in bench_root.rglob("__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)
        cleared += 1
    if cleared:
        click.echo(f"  ✓ Cleared {cleared} __pycache__ dir(s)")

    # 7. bench migrate (with retry-once on cache miss)
    click.secho("\n  Running bench migrate...", fg="cyan")
    ret = subprocess.run(["bench", "--site", site, "migrate"],
                         capture_output=True, text=True, cwd=str(bench_root))
    combined_output = ret.stdout + ret.stderr
    if ret.returncode != 0 and "ModuleNotFoundError" in combined_output:
        click.secho("  ⚠ First migrate hit ModuleNotFoundError; "
                    "clearing pycache + retrying...", fg="yellow")
        for cache_dir in bench_root.rglob("__pycache__"):
            shutil.rmtree(cache_dir, ignore_errors=True)
        ret = subprocess.run(["bench", "--site", site, "migrate"],
                             capture_output=True, text=True, cwd=str(bench_root))

    click.echo("\n".join(ret.stdout.splitlines()[-8:]))
    if ret.returncode != 0:
        click.secho("\n  ⚠ bench migrate failed:", fg="yellow")
        click.echo(ret.stderr[-1500:])
        click.secho(f"\n  Snapshot at {snapshot_file}", fg="yellow")
        return

    click.secho(f"\n{'=' * 78}", fg="green")
    click.secho("  ✓ MIGRATE-MODULE COMPLETE", fg="green", bold=True)
    click.secho("=" * 78, fg="green")
    click.echo(f"  Module:    '{source_module}' → '{target_module}'")
    click.echo(f"  Folder:    {source_app}/{src_slug}/ → {target_app}/{tgt_slug}/")
    click.echo(f"  DocTypes:  {dt_count} re-anchored to {target_app}")
    click.echo(f"  .py files: {rewritten} rewritten")
    click.echo(f"  Snapshot:  {snapshot_file.name}")
