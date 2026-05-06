"""app-migrator denest-app command — rename same-name-module antipattern folder.

Renames apps/<app>/<app>/<app>/  →  apps/<app>/<app>/<scrub(new_module)>/
and cascades all references: modules.txt, Python imports across all apps,
hooks.py, tabModule Def, tabDocType.module rows.

Default --dry-run. Use --apply to commit. Snapshot for rollback.

Usage:
  bench app-migrator denest-app --app app_migrator --to-module "App Migrator Core"
  bench app-migrator denest-app --app amb_w_tds --to-module "AMB TDS Core" --apply
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


@click.command("app-migrator-denest-app")
@click.option("--site", required=True, help="Site name (for DB updates)")
@click.option("--app", required=True, help="App with the antipattern")
@click.option("--to-module", required=True,
              help="New module name (e.g. \"App Migrator Core\"). "
                   "MUST scrub to a value DIFFERENT from app name.")
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
    click.secho(f"  DENEST-APP — {app}  →  module rename to '{to_module}'  [{mode}]",
                fg="cyan", bold=True)
    click.secho("=" * 78, fg="cyan")

    # Validation
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
        click.secho("  This app may not have the antipattern. Run audit-app-for-antipattern.",
                    fg="cyan")
        raise click.Abort()

    new_folder = app_pkg / new_slug
    if new_folder.exists():
        click.secho(f"✗ Target folder already exists: {new_folder}", fg="red")
        raise click.Abort()

    # Read modules.txt
    modules_txt = app_pkg / "modules.txt"
    modules = [m.strip() for m in modules_txt.read_text().splitlines() if m.strip()]
    antipattern_module_name = None
    for m in modules:
        if _scrub(m) == app:
            antipattern_module_name = m
            break
    if not antipattern_module_name:
        click.secho(f"✗ No modules.txt entry scrubs to '{app}'", fg="red")
        raise click.Abort()

    click.echo(f"\n  Antipattern module name: {antipattern_module_name!r}")
    click.echo(f"  Antipattern folder:      {antipattern_folder.relative_to(bench_root)}")
    click.echo(f"  → New module name:       {to_module!r}")
    click.echo(f"  → New folder:            {new_folder.relative_to(bench_root)}")

    # ── Plan filesystem actions ──
    click.secho(f"\n┌── PLAN ────", fg="cyan")
    click.echo(f"│  1. Rename folder")
    click.echo(f"│     {antipattern_folder.relative_to(bench_root)}")
    click.echo(f"│  → {new_folder.relative_to(bench_root)}")

    # Count DTs in the antipattern folder
    dt_dir = antipattern_folder / "doctype"
    dt_count = 0
    if dt_dir.exists():
        dt_count = sum(1 for d in dt_dir.iterdir()
                       if d.is_dir() and (d / f"{d.name}.json").exists())
    click.echo(f"│     ({dt_count} DocType(s) inside)")

    click.echo(f"│  2. Update modules.txt: '{antipattern_module_name}' → '{to_module}'")

    # Find all .py files referencing app.app.X imports
    old_pkg = f"{app}.{app}."
    new_pkg = f"{app}.{new_slug}."
    affected_files = []
    for py_file in bench_root.glob("apps/*/*.py"):
        try:
            if old_pkg in py_file.read_text():
                affected_files.append(py_file)
        except Exception:
            pass
    for py_file in bench_root.glob("apps/*/*/**/*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            if old_pkg in py_file.read_text():
                affected_files.append(py_file)
        except Exception:
            pass

    click.echo(f"│  3. Rewrite imports: '{old_pkg}' → '{new_pkg}'")
    click.echo(f"│     Affected files: {len(affected_files)}")
    if affected_files and len(affected_files) <= 20:
        for f in affected_files[:20]:
            click.echo(f"│       • {f.relative_to(bench_root)}")
    elif affected_files:
        for f in affected_files[:10]:
            click.echo(f"│       • {f.relative_to(bench_root)}")
        click.echo(f"│       ... and {len(affected_files) - 10} more")

    # DB plan
    click.echo(f"│  4. DB updates:")
    click.echo(f"│     • UPDATE `tabModule Def` SET name='{to_module}' "
                f"WHERE name='{antipattern_module_name}'")
    click.echo(f"│     • UPDATE tabDocType SET module='{to_module}' "
                f"WHERE module='{antipattern_module_name}' "
                f"({dt_count} row(s))")
    click.echo(f"│  5. bench migrate")
    click.echo(f"└────")

    if dry_run:
        click.secho(f"\n  This was a DRY-RUN. To apply, re-run with --apply.", fg="yellow")
        return

    # ── APPLY phase ──
    snap = Path(snapshot_dir)
    snap.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_file = snap / f"denest_{app}_{ts}.json"
    snapshot_data = {
        "app": app,
        "antipattern_module": antipattern_module_name,
        "to_module": to_module,
        "old_folder": str(antipattern_folder),
        "new_folder": str(new_folder),
        "affected_files": [str(f) for f in affected_files],
        "modules_txt_before": modules_txt.read_text(),
    }
    snapshot_file.write_text(json.dumps(snapshot_data, indent=2))
    click.secho(f"\n  📦 Snapshot: {snapshot_file}", fg="green")

    # 1. Rename folder
    antipattern_folder.rename(new_folder)
    click.secho(f"  ✓ Renamed folder", fg="green")

    # 2. Update modules.txt
    new_modules = [to_module if _scrub(m) == app else m for m in modules]
    modules_txt.write_text("\n".join(new_modules) + "\n")
    click.secho(f"  ✓ Updated modules.txt", fg="green")

    # 3. Rewrite imports across all affected files
    for f in affected_files:
        content = f.read_text()
        new_content = content.replace(old_pkg, new_pkg)
        f.write_text(new_content)
    click.secho(f"  ✓ Rewrote imports in {len(affected_files)} file(s)", fg="green")

    # 4. DB updates via frappe
    frappe.init(site=site)
    frappe.connect()
    frappe.db.sql("UPDATE `tabModule Def` SET name=%s WHERE name=%s",
                  (to_module, antipattern_module_name))
    frappe.db.sql("UPDATE tabDocType SET module=%s WHERE module=%s",
                  (to_module, antipattern_module_name))
    frappe.db.commit()
    click.secho(f"  ✓ Updated DB rows", fg="green")

    # 5. bench migrate
    click.secho(f"\n  Running bench migrate...", fg="cyan")
    ret = subprocess.run(["bench", "--site", site, "migrate"],
                         capture_output=True, text=True,
                         cwd=str(bench_root))
    click.echo("\n".join(ret.stdout.splitlines()[-8:]))
    if ret.returncode != 0:
        click.secho(f"\n  ⚠  bench migrate failed:", fg="yellow")
        click.echo(ret.stderr[-1500:])
        click.secho(f"\n  Snapshot at {snapshot_file} can restore previous state.", fg="yellow")
        return

    click.secho(f"\n{'=' * 78}", fg="green")
    click.secho(f"  ✓ DENEST COMPLETE — {app} no longer has the antipattern", fg="green", bold=True)
    click.secho(f"=" * 78, fg="green")
    click.echo(f"  Module renamed: '{antipattern_module_name}' → '{to_module}'")
    click.echo(f"  Folder renamed: {app}/ → {new_slug}/")
    click.echo(f"  Imports updated: {len(affected_files)} file(s)")
    click.echo(f"  DocTypes re-anchored: {dt_count}")
