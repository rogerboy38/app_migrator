"""app-migrator denest-app command — v2

Renames the same-name-module antipattern folder and cascades all references.

v2 lessons from self-application on app_migrator:
  1. Word-boundary regex scan (catches bare 'app.app' refs, not just 'app.app.X')
  2. patches.txt scan + rewrite
  3. Cross-table DB updates (tabReport/tabPage/tabDashboard/tabPrint Format/
     tabClient Script/tabServer Script) wrapped in SQL_SAFE_UPDATES toggle
  4. __pycache__ clear + retry-once on first bench migrate failure

Default --dry-run. --apply required for changes. Snapshot saved for rollback.

Usage:
  bench app-migrator denest-app --site <site> --app <app> --to-module "<New Name>"
  bench app-migrator denest-app --site <site> --app amb_w_tds --to-module "AMB TDS Core" --apply
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


# Tables that store a `module` column referencing tabModule Def.name
MODULE_REF_TABLES = [
    ("tabReport",          False),
    ("tabPage",            False),
    ("tabDashboard",       False),
    ("`tabPrint Format`",  True),
    ("`tabClient Script`", True),
    ("`tabServer Script`", True),
]


@click.command("app-migrator-denest-app")
@click.option("--site", required=True, help="Site name (for DB updates)")
@click.option("--app", required=True, help="App with the antipattern")
@click.option("--to-module", required=True,
              help='New module name (e.g. "App Migrator Core"). '
                   'MUST scrub to a value DIFFERENT from app name.')
@click.option("--apply", is_flag=True, help="Apply changes (default --dry-run)")
@click.option("--bench-root", default="/home/frappe/frappe-bench")
@click.option("--snapshot-dir",
              default="/home/frappe/frappe-bench/sites/snapshots")
@pass_context
def app_migrator_denest_app(context, site, app, to_module, apply,
                              bench_root, snapshot_dir):
    """Rename the same-name-module antipattern folder and cascade references."""
    bench_root = Path(bench_root)
    new_slug = _scrub(to_module)
    dry_run = not apply
    mode = "DRY-RUN" if dry_run else "APPLY"

    click.secho("\n" + "=" * 78, fg="cyan")
    click.secho(f"  DENEST-APP v2 — {app}  →  '{to_module}'  [{mode}]",
                fg="cyan", bold=True)
    click.secho("=" * 78, fg="cyan")

    # ── Validation ──
    if new_slug == app:
        click.secho(f"\n✗ ERROR: scrub('{to_module}') = '{new_slug}' equals app name '{app}'.\n"
                     f"  This is the antipattern. Choose a different module name.",
                     fg="red")
        click.secho(f"  Suggestions: '{app}_core', 'main', 'core'", fg="cyan")
        raise click.Abort()

    app_pkg = bench_root / "apps" / app / app
    if not app_pkg.exists():
        click.secho(f"✗ App package not found: {app_pkg}", fg="red")
        raise click.Abort()

    antipattern_folder = app_pkg / app
    if not antipattern_folder.exists():
        click.secho(f"✗ Antipattern folder not found: {antipattern_folder}", fg="red")
        click.secho("  This app may not have the antipattern. "
                    "Run audit-app-for-antipattern.", fg="cyan")
        raise click.Abort()

    new_folder = app_pkg / new_slug
    if new_folder.exists():
        click.secho(f"✗ Target folder already exists: {new_folder}", fg="red")
        raise click.Abort()

    # ── Read modules.txt to find the antipattern entry ──
    modules_txt = app_pkg / "modules.txt"
    modules = [m.strip() for m in modules_txt.read_text().splitlines() if m.strip()]
    antipattern_module_name = next((m for m in modules if _scrub(m) == app), None)
    if not antipattern_module_name:
        click.secho(f"✗ No modules.txt entry scrubs to '{app}'", fg="red")
        raise click.Abort()

    click.echo(f"\n  Antipattern module:  {antipattern_module_name!r}")
    click.echo(f"  Antipattern folder:  {antipattern_folder.relative_to(bench_root)}")
    click.echo(f"  → New module name:    {to_module!r}")
    click.echo(f"  → New folder:         {new_folder.relative_to(bench_root)}")

    # ── Build the cascade plan ──
    old_pkg = f"{app}.{app}"
    new_pkg = f"{app}.{new_slug}"
    # Word boundary regex: catches bare 'app.app' AND 'app.app.X' but not 'app.application'
    pattern = re.compile(rf"\b{re.escape(app)}\.{re.escape(app)}\b")

    # Count DocTypes inside antipattern folder
    dt_dir = antipattern_folder / "doctype"
    dt_count = 0
    if dt_dir.exists():
        dt_count = sum(1 for d in dt_dir.iterdir()
                       if d.is_dir() and (d / f"{d.name}.json").exists())

    # Find all files containing old_pkg references
    affected_py_files = []
    for py_file in bench_root.rglob("apps/*/**/*.py"):
        if "__pycache__" in str(py_file) or ".bak" in str(py_file):
            continue
        try:
            if pattern.search(py_file.read_text()):
                affected_py_files.append(py_file)
        except Exception:
            pass

    # patches.txt
    patches_txt = app_pkg / "patches.txt"
    patches_has_old_ref = False
    if patches_txt.exists():
        try:
            patches_has_old_ref = bool(pattern.search(patches_txt.read_text()))
        except Exception:
            pass

    # ── Display plan ──
    click.secho(f"\n┌── PLAN ────", fg="cyan")
    click.echo(f"│  1. Rename folder")
    click.echo(f"│     {antipattern_folder.relative_to(bench_root)}")
    click.echo(f"│  → {new_folder.relative_to(bench_root)}    ({dt_count} DocType(s))")
    click.echo(f"│  2. Update modules.txt: '{antipattern_module_name}' → '{to_module}'")
    click.echo(f"│  3. Rewrite import refs (\\b{old_pkg}\\b → {new_pkg})")
    click.echo(f"│     in {len(affected_py_files)} .py file(s)")
    click.echo(f"│  4. patches.txt rewrite: "
                f"{'YES' if patches_has_old_ref else 'no (file empty or no refs)'}")
    click.echo(f"│  5. DB updates:")
    click.echo(f"│     • UPDATE `tabModule Def` SET name='{to_module}' "
                f"WHERE name='{antipattern_module_name}'")
    click.echo(f"│     • UPDATE tabDocType SET module='{to_module}' "
                f"WHERE module='{antipattern_module_name}' ({dt_count} row(s) max)")
    click.echo(f"│     • UPDATE module col on 6 ancillary tables (Report/Page/")
    click.echo(f"│       Dashboard/Print Format/Client Script/Server Script)")
    click.echo(f"│  6. Clear __pycache__ for app + retry-once-on-fail bench migrate")
    click.echo(f"└────")

    if dry_run:
        click.secho(f"\n  This was a DRY-RUN. To apply, re-run with --apply.", fg="yellow")
        if affected_py_files and len(affected_py_files) <= 30:
            click.secho(f"\n  Affected .py files:", fg="cyan")
            for f in affected_py_files:
                click.echo(f"    • {f.relative_to(bench_root)}")
        elif affected_py_files:
            click.secho(f"\n  Affected .py files (first 15 of {len(affected_py_files)}):",
                        fg="cyan")
            for f in affected_py_files[:15]:
                click.echo(f"    • {f.relative_to(bench_root)}")
            click.echo(f"    ... and {len(affected_py_files) - 15} more")
        return

    # ─────────────────────────────── APPLY ────────────────────────────────
    snap = Path(snapshot_dir)
    snap.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_file = snap / f"denest_{app}_{ts}.json"
    snapshot_file.write_text(json.dumps({
        "app": app,
        "antipattern_module": antipattern_module_name,
        "to_module": to_module,
        "old_folder": str(antipattern_folder),
        "new_folder": str(new_folder),
        "affected_py_files": [str(f) for f in affected_py_files],
        "modules_txt_before": modules_txt.read_text(),
        "patches_txt_before": patches_txt.read_text() if patches_txt.exists() else None,
        "timestamp": ts,
    }, indent=2))
    click.secho(f"\n  📦 Snapshot: {snapshot_file}", fg="green")

    # 1. Rename folder
    antipattern_folder.rename(new_folder)
    click.secho(f"  ✓ Renamed folder", fg="green")

    # 2. Update modules.txt
    new_modules = [to_module if _scrub(m) == app else m for m in modules]
    modules_txt.write_text("\n".join(new_modules) + "\n")
    click.secho(f"  ✓ Updated modules.txt", fg="green")

    # 3. Rewrite imports across all affected .py files (regex-based)
    for f in affected_py_files:
        content = f.read_text()
        new_content = pattern.sub(new_pkg, content)
        f.write_text(new_content)
    click.secho(f"  ✓ Rewrote imports in {len(affected_py_files)} file(s)", fg="green")

    # 4. patches.txt rewrite
    if patches_has_old_ref:
        pt_content = patches_txt.read_text()
        new_pt = pattern.sub(new_pkg, pt_content)
        patches_txt.write_text(new_pt)
        click.secho(f"  ✓ Updated patches.txt", fg="green")
    else:
        click.echo(f"  ○ patches.txt: no rewrite needed")

    # 5. DB updates (within SQL_SAFE_UPDATES toggle)
    frappe.init(site=site)
    frappe.connect()
    frappe.db.sql("SET SQL_SAFE_UPDATES=0")
    try:
        # Primary: tabModule Def + tabDocType
        frappe.db.sql("UPDATE `tabModule Def` SET name=%s WHERE name=%s",
                      (to_module, antipattern_module_name))
        frappe.db.sql("UPDATE tabDocType SET module=%s WHERE module=%s",
                      (to_module, antipattern_module_name))
        # Cross-table: 6 ancillary tables
        cross_count = 0
        for table_spec, has_name_col in MODULE_REF_TABLES:
            try:
                where = "WHERE module=%s"
                if has_name_col:
                    where += " AND name IS NOT NULL"
                frappe.db.sql(
                    f"UPDATE {table_spec} SET module=%s {where}",
                    (to_module, antipattern_module_name),
                )
                cross_count += 1
            except Exception as e:
                click.echo(f"  ⚠ {table_spec} update skipped: {e}")
    finally:
        frappe.db.sql("SET SQL_SAFE_UPDATES=1")
    frappe.db.commit()
    click.secho(f"  ✓ Updated DB rows ({cross_count}/{len(MODULE_REF_TABLES)} cross-tables)",
                fg="green")

    # 6. Clear __pycache__ for the app, then bench migrate (retry-once-on-fail)
    cleared = 0
    for cache_dir in bench_root.rglob(f"apps/{app}/**/__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)
        cleared += 1
    if cleared:
        click.echo(f"  ✓ Cleared {cleared} __pycache__ dir(s)")

    click.secho(f"\n  Running bench migrate...", fg="cyan")
    ret = subprocess.run(["bench", "--site", site, "migrate"],
                         capture_output=True, text=True,
                         cwd=str(bench_root))
    if ret.returncode != 0 and "ModuleNotFoundError" in ret.stderr:
        click.secho(f"  ⚠ First migrate failed (ModuleNotFoundError); "
                    f"clearing more pycache + retrying...", fg="yellow")
        for cache_dir in bench_root.rglob("__pycache__"):
            shutil.rmtree(cache_dir, ignore_errors=True)
        ret = subprocess.run(["bench", "--site", site, "migrate"],
                             capture_output=True, text=True,
                             cwd=str(bench_root))

    click.echo("\n".join(ret.stdout.splitlines()[-8:]))
    if ret.returncode != 0:
        click.secho(f"\n  ⚠  bench migrate failed:", fg="yellow")
        click.echo(ret.stderr[-1500:])
        click.secho(f"\n  Snapshot at {snapshot_file} preserves pre-change state.",
                    fg="yellow")
        return

    click.secho(f"\n{'=' * 78}", fg="green")
    click.secho(f"  ✓ DENEST COMPLETE — {app} no longer has the antipattern",
                fg="green", bold=True)
    click.secho(f"=" * 78, fg="green")
    click.echo(f"  Module:    '{antipattern_module_name}' → '{to_module}'")
    click.echo(f"  Folder:    {app}/ → {new_slug}/")
    click.echo(f"  .py files: {len(affected_py_files)} updated")
    click.echo(f"  DocTypes:  {dt_count} re-anchored")
    click.echo(f"  Snapshot:  {snapshot_file.name}")
