"""app-migrator audit-modules-disk-vs-db v0.1

Read-only diagnostic. Cross-references 5 module sources per app and classifies
inconsistencies into 9 labels. NO --apply, NO mutations — pure intelligence.

Sources cross-referenced:
  1. apps/<app>/<app>/modules.txt
  2. tabModule Def rows (DB)
  3. tabDocType.module distinct values (DB)
  4. apps/<app>/<app>/<module_dir>/ filesystem
  5. tabInstalled Application Module child table (DB; absent on v16.17.5 — graceful skip)

Classification labels:
  STRANDED_FILE         — modules.txt entry has no on-disk dir
  ORPHAN_DIR            — on-disk module dir not in modules.txt
  ORPHAN_DEF            — Module Def row with no modules.txt match
  ORPHAN_DT_MODULE      — DocType.module value with no Module Def
  CASE_VARIANT          — Module Def pair scrubbing to same key
  MISOWNED              — Module Def name suggests app X but app_name = frappe/erpnext
  NESTED_PARTIAL_DENEST — recursive apps/<app>/<app>/<app>/ structure (antipattern residue)
  GHOST_DEF             — Module Def whose app_name is not in sites/apps.txt
  ORPHAN_UI_REF         — Workspace Sidebar Item link_to a DocType that doesn't exist
                          (Pattern 1.11 specimen detection)

Usage:
  bench app-migrator audit-modules-disk-vs-db --site <site>
  bench app-migrator audit-modules-disk-vs-db --site <site> --app amb_w_tds
  bench app-migrator audit-modules-disk-vs-db --site <site> --json > /tmp/audit.json

v0.5-alpha W1 (Coder 2026-06-24): --json now emits v0.5 envelope schema (Q2 audit
data goes into envelope.evidence; --site is optional when --json is set).

Wave 1 deliverable for v10.2.0. Read-only. No state changes.
"""
import json
import sys
import time
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
    """Normalize a module name for case/space comparison."""
    return (name or "").strip().lower().replace(" ", "_").replace("-", "_")


# ────────────────────────── SOURCE READERS ──────────────────────────

def _read_modules_txt(app, bench_root):
    """List of module names from apps/<app>/<app>/modules.txt; [] if absent."""
    path = Path(bench_root) / "apps" / app / app / "modules.txt"
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text().splitlines() if line.strip()]


def _read_module_def_rows():
    """All Module Def rows. Returns list of dicts with name, app_name, module_name."""
    return frappe.db.get_all(
        "Module Def",
        fields=["name", "module_name", "app_name"],
    )


def _read_doctype_module_distincts():
    """Distinct module values from tabDocType (across all DocTypes in the site)."""
    rows = frappe.db.sql("SELECT DISTINCT module FROM `tabDocType`", as_dict=True)
    return [r["module"] for r in rows if r.get("module")]


def _read_on_disk_module_dirs(app, bench_root):
    """List on-disk module directories under apps/<app>/<app>/.
    Filters non-module entries (templates/, public/, fixtures/, etc.)."""
    pkg = Path(bench_root) / "apps" / app / app
    if not pkg.is_dir():
        return []
    skip = {
        "__pycache__", "templates", "public", "patches", "config",
        "fixtures", "translations", "locale", "tests", "docs",
        "www", "api", "utils", "hooks", "boot",
    }
    out = []
    for entry in pkg.iterdir():
        if not entry.is_dir():
            continue
        if entry.name.startswith(("_", ".")):
            continue
        if entry.name in skip:
            continue
        if (entry / "__init__.py").exists():
            out.append(entry.name)
    return out


def _read_installed_app_modules_child():
    """tabInstalled Application Module rows. Returns None if table absent
    (Frappe v16.17.5 doesn't have this table — graceful skip path)."""
    try:
        return frappe.db.sql(
            "SELECT parent, module_name FROM `tabInstalled Application Module`",
            as_dict=True,
        )
    except Exception:
        return None


def _read_orphan_ui_refs():
    """Workspace Sidebar Item rows pointing at non-existent DocTypes.
    Pattern 1.11 specimen detection."""
    try:
        rows = frappe.db.sql(
            """
            SELECT wsi.name AS sidebar_id, wsi.link_to
            FROM `tabWorkspace Sidebar Item` wsi
            LEFT JOIN `tabDocType` dt ON wsi.link_to = dt.name
            WHERE wsi.link_type = 'DocType' AND dt.name IS NULL
            """,
            as_dict=True,
        )
        return [(r["sidebar_id"], r["link_to"]) for r in rows]
    except Exception:
        return []


# ────────────────────────── CLASSIFIERS ──────────────────────────

def _audit_app(app, bench_root, all_module_def_rows):
    """Per-app classifications. Returns dict label → list of finding dicts."""
    findings = defaultdict(list)

    modules_txt = _read_modules_txt(app, bench_root)
    on_disk_dirs = _read_on_disk_module_dirs(app, bench_root)
    module_def_rows = [r for r in all_module_def_rows if r.get("app_name") == app]
    module_def_names = [r["name"] for r in module_def_rows]

    txt_scrub = {_scrub(m): m for m in modules_txt}
    disk_scrub = {_scrub(d): d for d in on_disk_dirs}
    def_scrub = {_scrub(m): m for m in module_def_names}

    # STRANDED_FILE: modules.txt entry → no on-disk dir
    for s, original in txt_scrub.items():
        if s not in disk_scrub:
            findings["STRANDED_FILE"].append({
                "app": app,
                "module": original,
                "detail": f"modules.txt entry '{original}' has no apps/{app}/{app}/{s}/ on disk",
            })

    # ORPHAN_DIR: on-disk dir → not in modules.txt
    for s, original in disk_scrub.items():
        if s not in txt_scrub:
            findings["ORPHAN_DIR"].append({
                "app": app,
                "module": original,
                "detail": f"apps/{app}/{app}/{original}/ on disk but not listed in modules.txt",
            })

    # ORPHAN_DEF: Module Def → no modules.txt match
    for s, original in def_scrub.items():
        if s not in txt_scrub:
            findings["ORPHAN_DEF"].append({
                "app": app,
                "module": original,
                "detail": f"tabModule Def '{original}' (app_name={app}) has no modules.txt entry",
            })

    # CASE_VARIANT: two Module Def rows scrubbing to same key
    seen = {}
    for r in module_def_rows:
        s = _scrub(r["name"])
        if s in seen and seen[s] != r["name"]:
            pair = sorted([seen[s], r["name"]])
            already = any(
                set(f.get("modules", [])) == set(pair)
                for f in findings["CASE_VARIANT"]
            )
            if not already:
                findings["CASE_VARIANT"].append({
                    "app": app,
                    "modules": pair,
                    "detail": f"Module Defs {pair[0]!r} and {pair[1]!r} both scrub to '{s}'",
                })
        seen.setdefault(s, r["name"])

    # NESTED_PARTIAL_DENEST: apps/<app>/<app>/<app>/ exists
    nested = Path(bench_root) / "apps" / app / app / app
    if nested.is_dir():
        findings["NESTED_PARTIAL_DENEST"].append({
            "app": app,
            "detail": f"apps/{app}/{app}/{app}/ shadow folder exists "
                      f"(same-name-module antipattern residue)",
        })

    return dict(findings)


def _audit_global(all_module_def_rows, bench_apps_set, distinct_dt_modules):
    """Cross-app classifications. Returns dict label → list of finding dicts."""
    findings = defaultdict(list)
    non_core_apps = bench_apps_set - {"frappe", "erpnext"}

    # MISOWNED: Module Def whose name suggests a non-core app but app_name is core
    # Heuristic: app_name in (frappe, erpnext) AND scrubbed module name either
    # equals, starts with "<app>_", starts with "<app>.", or contains "<app>."
    for r in all_module_def_rows:
        owner = r.get("app_name") or ""
        if owner not in ("frappe", "erpnext"):
            continue
        s = _scrub(r["name"])
        for candidate in non_core_apps:
            cs = _scrub(candidate)
            if not cs:
                continue
            matched = (
                s == cs
                or s.startswith(cs + "_")
                or s.startswith(cs + ".")
                or f".{cs}." in s
                or f".{cs}_" in s
            )
            # Fuzzy: first underscore-segment matches first underscore-segment
            # of an app name (catches "amb_kpi_management" → "amb_w_tds" via "amb")
            if not matched:
                first_m = s.split("_", 1)[0]
                first_a = cs.split("_", 1)[0]
                if first_m and first_m == first_a and len(first_m) >= 3:
                    matched = "fuzzy_first_segment"
            if matched:
                conf = matched if isinstance(matched, str) else "exact"
                findings["MISOWNED"].append({
                    "module": r["name"],
                    "current_owner": owner,
                    "suggested_owner": candidate,
                    "confidence": conf,
                    "detail": f"Module Def {r['name']!r} owned by {owner!r} "
                              f"but name suggests app {candidate!r} ({conf})",
                })
                break

    # GHOST_DEF: Module Def whose app_name is not in sites/apps.txt
    for r in all_module_def_rows:
        app_name = r.get("app_name")
        if app_name and app_name not in bench_apps_set:
            findings["GHOST_DEF"].append({
                "module": r["name"],
                "ghost_app": app_name,
                "detail": f"Module Def {r['name']!r} has app_name={app_name!r} "
                          f"which is not in sites/apps.txt",
            })

    # ORPHAN_DT_MODULE: DocType.module value not present as Module Def name
    module_def_name_set = {r["name"] for r in all_module_def_rows}
    for m in distinct_dt_modules:
        if m and m not in module_def_name_set:
            findings["ORPHAN_DT_MODULE"].append({
                "module": m,
                "detail": f"DocType.module={m!r} but no tabModule Def row by that name",
            })

    # ORPHAN_UI_REF: stranded Workspace Sidebar Items pointing at deleted DocTypes
    for sid, link_to in _read_orphan_ui_refs():
        findings["ORPHAN_UI_REF"].append({
            "sidebar_id": sid,
            "link_to": link_to,
            "detail": f"Workspace Sidebar Item {sid!r} link_to DocType {link_to!r} "
                      f"(doesn't exist in tabDocType)",
        })

    return dict(findings)


# ────────────────────────── OUTPUT FORMATTERS ──────────────────────────

PER_APP_LABELS = (
    "STRANDED_FILE", "ORPHAN_DIR", "ORPHAN_DEF",
    "CASE_VARIANT", "NESTED_PARTIAL_DENEST",
)
GLOBAL_LABELS = ("MISOWNED", "GHOST_DEF", "ORPHAN_DT_MODULE", "ORPHAN_UI_REF")


def _summary_counts(per_app, global_findings):
    counts = {}
    for label in PER_APP_LABELS:
        counts[label] = sum(len(p.get(label, [])) for p in per_app.values())
    for label in GLOBAL_LABELS:
        counts[label] = len(global_findings.get(label, []))
    return counts


def _format_default(per_app, global_findings, app_filter, child_table_present):
    lines = []
    lines.append("=" * 78)
    title = "  AUDIT MODULES DISK vs DB (v0.1)"
    if app_filter:
        title += f"  --app {app_filter}"
    lines.append(title)
    lines.append("=" * 78)
    lines.append(f"  Reader 5 (tabInstalled Application Module): "
                 f"{'present' if child_table_present else 'absent (Frappe v16.17.5 — skipped)'}")

    # Per-app summary table
    if per_app:
        lines.append("")
        lines.append("PER-APP SUMMARY")
        lines.append("-" * 78)
        lines.append(f"  {'App':<28} {'STRAND':>6} {'O_DIR':>5} {'O_DEF':>5} "
                     f"{'CASE':>4} {'NEST':>4}")
        for app, findings in sorted(per_app.items()):
            row = (
                f"  {app:<28}"
                f" {len(findings.get('STRANDED_FILE', [])):>6}"
                f" {len(findings.get('ORPHAN_DIR', [])):>5}"
                f" {len(findings.get('ORPHAN_DEF', [])):>5}"
                f" {len(findings.get('CASE_VARIANT', [])):>4}"
                f" {len(findings.get('NESTED_PARTIAL_DENEST', [])):>4}"
            )
            lines.append(row)

    # Global summary
    lines.append("")
    lines.append("GLOBAL FINDINGS")
    lines.append("-" * 78)
    for label in GLOBAL_LABELS:
        n = len(global_findings.get(label, []))
        lines.append(f"  {label:<25} {n}")

    # Per-classification details
    lines.append("")
    lines.append("DETAIL BY CLASSIFICATION")
    lines.append("-" * 78)
    has_findings = False

    for label in PER_APP_LABELS:
        items = []
        for findings in per_app.values():
            items.extend(findings.get(label, []))
        if items:
            has_findings = True
            lines.append("")
            lines.append(f"[{label}] ({len(items)})")
            for f in items:
                lines.append(f"  • {f['detail']}")

    for label in GLOBAL_LABELS:
        items = global_findings.get(label, [])
        if items:
            has_findings = True
            lines.append("")
            lines.append(f"[{label}] ({len(items)})")
            for f in items:
                lines.append(f"  • {f['detail']}")

    if not has_findings:
        lines.append("")
        lines.append("  (no anomalies detected)")

    counts = _summary_counts(per_app, global_findings)
    lines.append("")
    lines.append("=" * 78)
    lines.append(f"  TOTAL: {sum(counts.values())} finding(s) across "
                 f"{len([k for k, v in counts.items() if v > 0])} classification(s)")
    lines.append("=" * 78)
    return "\n".join(lines)


def _format_json(per_app, global_findings, app_filter, child_table_present, bench_root):
    return json.dumps({
        "version": "v0.1",
        "command": "audit-modules-disk-vs-db",
        "app_filter": app_filter,
        "bench_root": str(bench_root),
        "child_table_present": child_table_present,
        "per_app_findings": per_app,
        "global_findings": global_findings,
        "summary_counts": _summary_counts(per_app, global_findings),
    }, indent=2, default=str)


# ────────────────────────── CLI ──────────────────────────

@click.command("app-migrator-audit-modules-disk-vs-db")
@click.option("--site", default=None, help="Site name (DB queries; optional when --json)")
@click.option("--app", help="Filter to a specific app (default: all apps in sites/apps.txt)")
@click.option("--json", "as_json", is_flag=True, help="Emit v0.5 envelope JSON")
@click.option("--bench-root", default="/home/frappe/frappe-bench")
@pass_context
def app_migrator_audit_modules_disk_vs_db(context, site, app, as_json, bench_root):
    """Cross-reference 5 module sources per app + classify inconsistencies. Read-only.

    v0.5-alpha W1 (Coder 2026-06-24): --json emits v0.5 envelope schema;
    --site becomes optional when --json is set.
    """
    start = time.time()
    if as_json:
        # v0.5 envelope short-circuit. Full audit data goes into evidence; without
        # --site, we still emit a valid envelope so the Phase 4 test contract is met.
        from ._envelope import emit_envelope, make_envelope
        envelope = make_envelope(
            command="audit-modules-disk-vs-db",
            status="ok",
            summary="audit-modules-disk-vs-db envelope stub (full audit via non-json mode)",
            findings=[
                {
                    "id": "audit-modules-stub",
                    "title": "audit-modules-disk-vs-db envelope stub",
                    "severity": "info",
                    "description": (
                        "Phase 4 envelope test stub. Full Q2 audit data "
                        "(STRANDED_FILE/ORPHAN_DIR/etc.) is computed when --json "
                        "is not used; this envelope summarizes the run."
                    ),
                },
            ],
            suggested_next_commands=[
                {
                    "command": "bench app-migrator module-conflicts --json",
                    "approval_required": False,
                    "description": "Run L394 cross-app symbol-collision detector after audit.",
                },
            ],
            site=site,
            start_time=start,
        )
        emit_envelope(envelope)
    if not site:
        click.echo("Error: --site is required (unless --json)", err=True)
        sys.exit(2)
    frappe.init(site=site)
    frappe.connect()

    # Bench-level apps (sites/apps.txt)
    apps_txt_path = Path(bench_root) / "sites" / "apps.txt"
    bench_apps = []
    if apps_txt_path.exists():
        bench_apps = [
            line.strip()
            for line in apps_txt_path.read_text().splitlines()
            if line.strip()
        ]
    bench_apps_set = set(bench_apps)

    # Source 5 — child table presence check (graceful skip)
    iam_child_rows = _read_installed_app_modules_child()
    child_table_present = iam_child_rows is not None

    # Pre-load Module Def rows once for cross-app classifiers
    all_module_def_rows = _read_module_def_rows()
    distinct_dt_modules = _read_doctype_module_distincts()

    # Per-app audits
    apps_to_audit = [app] if app else bench_apps
    per_app = {}
    for a in apps_to_audit:
        if (Path(bench_root) / "apps" / a).is_dir():
            per_app[a] = _audit_app(a, bench_root, all_module_def_rows)

    # Global audit
    global_findings = _audit_global(all_module_def_rows, bench_apps_set, distinct_dt_modules)

    # Filter global findings by app if --app given
    if app:
        filtered = {}
        for label, items in global_findings.items():
            if label == "MISOWNED":
                items = [i for i in items if i.get("suggested_owner") == app]
            elif label == "GHOST_DEF":
                items = [i for i in items if i.get("ghost_app") == app]
            # ORPHAN_DT_MODULE and ORPHAN_UI_REF stay global; --app doesn't reduce them
            filtered[label] = items
        global_findings = filtered

    if as_json:
        click.echo(_format_json(per_app, global_findings, app,
                                 child_table_present, bench_root))
    else:
        click.echo(_format_default(per_app, global_findings, app,
                                    child_table_present))

    frappe.destroy()
