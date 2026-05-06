"""app-migrator audit-orphan-doctypes — find DocTypes with broken module references.

Read-only diagnostic. Detects three orphan classes:

  1. STRANDED       — tabDocType.module references a Module Def that doesn't exist.
                      Symptom: bench migrate fails "Module X not found".

  2. CASE_MISMATCH  — Two Module Def rows scrub to the same name (Title Case +
                      lowercase variant). DocTypes anchored to the variant become
                      effectively orphaned because Frappe's case-sensitive lookup
                      may pick the wrong one. (The bug we found in amb_w_tds where
                      COA Quality Test Parameter had module='amb_w_tds' lowercase.)

  3. FILESYSTEM     — tabDocType.module is valid but no source files exist at the
                      expected path. Symptom: import_controller falls back to BASE
                      Document silently.

Pairs with denest-app, migrate-module, promote-custom-doctype as a precursor
diagnostic. Use this BEFORE running cleanup commands to know what you're about to fix.

Usage:
  bench --site <site> app-migrator audit-orphan-doctypes
  bench --site <site> app-migrator audit-orphan-doctypes --app amb_w_tds
  bench --site <site> app-migrator audit-orphan-doctypes --output /tmp/orphans.txt
"""
from collections import defaultdict
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


@click.command("app-migrator-audit-orphan-doctypes")
@click.option("--site", required=True, help="Site name")
@click.option("--app", help="Filter to a specific app (default: all apps)")
@click.option("--output", help="Write report to file (default: stdout)")
@click.option("--bench-root", default="/home/frappe/frappe-bench")
@pass_context
def app_migrator_audit_orphan_doctypes(context, site, app, output, bench_root):
    """Audit DocTypes for broken module references (read-only)."""
    bench_root = Path(bench_root)

    frappe.init(site=site)
    frappe.connect()

    lines = []
    def emit(s=""):
        lines.append(s)

    emit("=" * 95)
    title = f"  ORPHAN DOCTYPE AUDIT — site={site}"
    if app:
        title += f", app={app}"
    emit(title)
    emit("=" * 95)

    # ── CLASS 1: STRANDED — module not in tabModule Def ──
    where_app = "AND dt.app=%s" if app else ""
    args = (app,) if app else ()
    stranded = frappe.db.sql(f"""
        SELECT dt.name, dt.module, dt.app, dt.custom
        FROM tabDocType dt
        LEFT JOIN `tabModule Def` md ON md.name = dt.module
        WHERE md.name IS NULL {where_app}
        ORDER BY dt.module, dt.name
    """, args, as_dict=True)

    emit(f"\n{'─' * 95}")
    emit(f"  CLASS 1 — STRANDED ({len(stranded)} found)")
    emit("  tabDocType.module references a Module Def that doesn't exist.")
    emit(f"{'─' * 95}")
    if stranded:
        emit(f"  {'DocType':40} {'module (missing)':25} {'app':15} {'cust'}")
        for r in stranded:
            emit(f"  {r.name:40} {r.module!r:25} {(r.app or '-'):15} {r.custom}")
        emit("\n  Suggested fix per row (review before applying):")
        emit("    UPDATE tabDocType SET module=<canonical> WHERE name=<doctype>;")
    else:
        emit("  ✓ no stranded orphans")

    # ── CLASS 2: CASE_MISMATCH — Module Def pairs that scrub to same name ──
    all_mds = frappe.db.sql("SELECT name, app_name FROM `tabModule Def`", as_dict=True)
    md_by_name = {md.name: md for md in all_mds}
    case_mismatch_pairs = []
    for md in all_mds:
        scrubbed = _scrub(md.name)
        if scrubbed != md.name and scrubbed in md_by_name:
            # Found pair: md.name (canonical) + scrubbed (variant)
            case_mismatch_pairs.append((md.name, scrubbed, md.app_name))

    emit(f"\n{'─' * 95}")
    emit(f"  CLASS 2 — CASE_MISMATCH ({len(case_mismatch_pairs)} duplicate pairs)")
    emit("  Two Module Def rows scrub to the same name (canonical + variant).")
    emit(f"{'─' * 95}")
    if case_mismatch_pairs:
        emit(f"  {'Canonical':35} {'Variant (duplicate)':30} {'app'}")
        for canonical, variant, app_name in case_mismatch_pairs:
            emit(f"  {canonical:35} {variant:30} {app_name}")
            anchored = frappe.db.sql(
                "SELECT name FROM tabDocType WHERE module=%s", variant, as_dict=True
            )
            if anchored:
                for a in anchored:
                    emit(f"    ↳ DocType anchored to variant: {a.name}")
        emit("\n  Suggested fix per pair:")
        emit("    UPDATE tabDocType SET module=<canonical>, app=<app_name> WHERE module=<variant>;")
        emit("    DELETE FROM `tabModule Def` WHERE name=<variant>;")
        emit("  Or run: bench app-migrator denest-app (auto-includes scrub variants in v6+).")
    else:
        emit("  ✓ no case-mismatch duplicates")

    # ── CLASS 3: FILESYSTEM — module exists in DB but no source files at expected path ──
    canonical_dts = frappe.db.sql(f"""
        SELECT dt.name, dt.module, dt.app
        FROM tabDocType dt
        JOIN `tabModule Def` md ON md.name = dt.module
        WHERE dt.custom = 0 {where_app}
        ORDER BY dt.app, dt.module, dt.name
    """, args, as_dict=True)

    filesystem_orphans = []
    for r in canonical_dts:
        if not r.app:
            continue
        slug_module = _scrub(r.module)
        slug_doctype = _scrub(r.name)
        # Try expected paths (handle nested AND flat layouts)
        expected_paths = [
            bench_root / "apps" / r.app / r.app / slug_module / "doctype" / slug_doctype / f"{slug_doctype}.json",
            bench_root / "apps" / r.app / r.app / r.app / "doctype" / slug_doctype / f"{slug_doctype}.json",
        ]
        if not any(p.exists() for p in expected_paths):
            filesystem_orphans.append((r.name, r.module, r.app, expected_paths[0]))

    emit(f"\n{'─' * 95}")
    emit(f"  CLASS 3 — FILESYSTEM ({len(filesystem_orphans)} found)")
    emit("  tabDocType.module valid but no source files at any expected path.")
    emit(f"{'─' * 95}")
    if filesystem_orphans:
        emit(f"  {'DocType':40} {'module':25} {'app':15} {'expected (one of)'}")
        for name, mod, ap, path in filesystem_orphans[:30]:
            try:
                rel = path.relative_to(bench_root)
            except ValueError:
                rel = path
            emit(f"  {name:40} {mod:25} {ap:15} {rel}")
        if len(filesystem_orphans) > 30:
            emit(f"  ... and {len(filesystem_orphans) - 30} more")
    else:
        emit("  ✓ no filesystem orphans")

    # ── SUMMARY ──
    total = len(stranded) + len(case_mismatch_pairs) + len(filesystem_orphans)
    emit(f"\n{'=' * 95}")
    emit("  SUMMARY")
    emit(f"{'=' * 95}")
    emit(f"  STRANDED       (module not in tabModule Def):    {len(stranded)}")
    emit(f"  CASE_MISMATCH  (duplicate Module Def pairs):     {len(case_mismatch_pairs)}")
    emit(f"  FILESYSTEM     (no source files at any path):    {len(filesystem_orphans)}")
    emit("")
    if total:
        emit(f"  ⚠ Total orphan signals: {total}")
        emit("  Resolution paths:")
        emit("    • STRANDED + CASE_MISMATCH → bench app-migrator denest-app/migrate-module")
        emit("      auto-includes scrub variants in DB cascade (v6+)")
        emit("    • FILESYSTEM → check app installation, restore source files, or bench migrate")
    else:
        emit("  ✓ No orphan signals — all DocType module refs resolve cleanly.")

    frappe.destroy()

    text = "\n".join(lines)
    if output:
        Path(output).write_text(text)
        click.echo(f"Report written to {output}")
    else:
        click.echo(text)
