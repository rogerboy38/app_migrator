"""app-migrator scan-donor-residue command

Scans a donor app for vestiges of DocTypes that have been migrated to a receiver app.
Finds shadow filesystem folders, hooks.py references, utility modules, and fixture
entries that should be cleaned up after a donor→receiver migration.

Pairs with promote-custom-doctype: after promoting custom DocTypes to a receiver app,
this command finds what's left behind on the donor that needs cleaning.

Usage:
  # Auto-detect moved DocTypes by comparing donor and receiver source trees:
  bench --site <site> app-migrator scan-donor-residue \\
    --donor amb_w_tds --receiver amb_w_spc

  # Or specify the moved DocTypes explicitly:
  bench --site <site> app-migrator scan-donor-residue \\
    --donor amb_w_tds --doctypes "Batch AMB,Container Barrels,TDS Settings"

  # Save report to file:
  bench --site <site> app-migrator scan-donor-residue \\
    --donor amb_w_tds --receiver amb_w_spc --output /tmp/residue.txt
"""
import json
from pathlib import Path

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f


@click.command("app-migrator-scan-donor-residue")
@click.option("--site", required=True, help="Site name")
@click.option("--donor", required=True, help="Donor app name (where to scan for residue)")
@click.option("--receiver", help="Receiver app name (where DocTypes now live; "
                                   "used to auto-detect moved DocTypes)")
@click.option("--doctypes", help="Comma-separated explicit list of moved DocTypes "
                                  "(alternative to --receiver auto-detection)")
@click.option("--output", help="Write report to file (default: stdout)")
@click.option("--bench-root", default="/home/frappe/frappe-bench",
              help="Bench root directory")
@pass_context
def app_migrator_scan_donor_residue(context, site, donor, receiver, doctypes,
                                     output, bench_root):
    """Scan a donor app for vestiges of DocTypes migrated to a receiver app.

    Reports filesystem shadow folders, hooks.py references, utility modules,
    fixture entries, and layout anomalies. Read-only — no changes made.
    """
    if not receiver and not doctypes:
        click.secho("Error: must specify --receiver or --doctypes", fg="red")
        raise click.Abort()

    bench_root = Path(bench_root)
    donor_root = bench_root / "apps" / donor
    if not donor_root.exists():
        click.secho(f"Error: donor app not found at {donor_root}", fg="red")
        raise click.Abort()

    frappe.init(site=site)
    frappe.connect()

    # Determine the moved DocType set
    if doctypes:
        moved = {d.strip() for d in doctypes.split(",") if d.strip()}
        moved_source = "explicit --doctypes"
    else:
        receiver_root = bench_root / "apps" / receiver
        if not receiver_root.exists():
            click.secho(f"Error: receiver app not found at {receiver_root}", fg="red")
            raise click.Abort()
        moved = _find_moved_doctypes(donor_root, receiver_root)
        moved_source = (f"auto-detected: {receiver} JSON + {donor} filesystem evidence")

    moved_slugs = {dt.lower().replace(" ", "_") for dt in moved}

    # Build the report
    lines = []
    def emit(s=""):
        lines.append(s)

    emit("=" * 95)
    emit(f"  DONOR RESIDUE SCAN — {donor} (looking for {len(moved)} moved DocTypes from {moved_source})")
    emit("=" * 95)
    emit(f"\nDonor:    {donor_root.relative_to(bench_root)}")
    if receiver:
        emit(f"Receiver: apps/{receiver}/{receiver}/")
    emit(f"\nMoved DocTypes ({len(moved)}):")
    for dt in sorted(moved):
        emit(f"  • {dt}")

    # Section 1: Filesystem shadow folders
    emit(f"\n{'─' * 95}")
    emit("  [1] FILESYSTEM: shadow doctype folders")
    emit(f"{'─' * 95}")
    shadow_count = _scan_filesystem(donor_root, moved_slugs, bench_root, emit)

    # Section 2: hooks.py references
    emit(f"\n{'─' * 95}")
    emit("  [2] HOOKS.PY: references in donor's hooks.py files")
    emit(f"{'─' * 95}")
    hooks_count = _scan_hooks(donor_root, moved, bench_root, emit)

    # Section 3: Utility modules
    emit(f"\n{'─' * 95}")
    emit("  [3] UTILS: doctype-related Python modules")
    emit(f"{'─' * 95}")
    utils_count = _scan_utils(donor_root, moved_slugs, bench_root, emit)

    # Section 4: Fixture entries
    emit(f"\n{'─' * 95}")
    emit("  [4] FIXTURES: entries in donor's fixture files")
    emit(f"{'─' * 95}")
    fixtures_count = _scan_fixtures(donor_root, moved, bench_root, emit)

    # Section 5: modules.txt declarations
    emit(f"\n{'─' * 95}")
    emit("  [5] MODULES.TXT: module declarations")
    emit(f"{'─' * 95}")
    _scan_modules_txt(donor_root, bench_root, emit)

    # Section 6: Layout anomalies
    emit(f"\n{'─' * 95}")
    emit("  [6] LAYOUT ANOMALIES: nested + shallow shadow paths")
    emit(f"{'─' * 95}")
    _scan_layout(donor_root, donor, moved_slugs, emit)

    # Summary
    emit(f"\n{'=' * 95}")
    emit("  SUMMARY")
    emit(f"{'=' * 95}")
    emit(f"  Shadow folders:    {shadow_count}")
    emit(f"  hooks.py refs:     {hooks_count}")
    emit(f"  Utility files:     {utils_count}")
    emit(f"  Fixture entries:   {fixtures_count}")
    emit("")
    if shadow_count + hooks_count + utils_count + fixtures_count == 0:
        emit("  ✓ Donor is CLEAN — no residue from migrated DocTypes")
    else:
        emit("  ⚠  Residue found. Cleanup recommended (Phase 1B).")
    emit("=" * 95)

    report = "\n".join(lines)
    if output:
        Path(output).write_text(report)
        click.echo(f"Report written to {output}")
        click.echo(f"\nSummary: {shadow_count} shadow / {hooks_count} hooks / "
                   f"{utils_count} utils / {fixtures_count} fixture entries")
    else:
        click.echo(report)


# ─── Scanners ───

def _find_doctypes_in_app(app_root):
    """Auto-detect DocTypes by scanning <app>/<app>/**/doctype/<slug>/<slug>.json"""
    found = set()
    for json_path in app_root.rglob("doctype/*/*.json"):
        if json_path.parent.name != json_path.stem:
            continue
        try:
            with open(json_path) as f:
                j = json.load(f)
            name = j.get("name")
            if name:
                found.add(name)
        except Exception:
            pass
    return found


def _find_moved_doctypes(donor_root, receiver_root):
    """A doctype is 'moved' if it has receiver JSON AND donor filesystem evidence.
    
    The donor evidence: any directory named <slug> under any 'doctype/' parent
    in the donor tree. This filters out:
      - Frappe core doctypes that both apps customize (Stock Entry, Item Group, Uom)
      - Receiver-native doctypes that were never on donor
    Only doctypes with shadow/canonical folders on donor count.
    """
    receiver_doctypes = _find_doctypes_in_app(receiver_root)
    moved = set()
    for name in receiver_doctypes:
        slug = name.lower().replace(" ", "_")
        for cand in donor_root.rglob(f"doctype/{slug}"):
            if cand.is_dir():
                moved.add(name)
                break
    return moved


def _scan_filesystem(donor_root, moved_slugs, bench_root, emit):
    """Find shadow doctype folders in donor."""
    count = 0
    for slug in sorted(moved_slugs):
        for path in donor_root.rglob(f"doctype/{slug}"):
            if not path.is_dir():
                continue
            files = sorted(path.iterdir())
            has_init = (path / "__init__.py").exists()
            has_canonical_py = (path / f"{slug}.py").exists()
            has_canonical_json = (path / f"{slug}.json").exists()
            count += 1
            emit(f"\n  📁 {path.relative_to(bench_root)}")
            emit(f"     __init__.py: {'YES' if has_init else 'no'}  "
                 f"canonical .py: {'YES' if has_canonical_py else 'no'}  "
                 f"canonical .json: {'YES' if has_canonical_json else 'no'}  "
                 f"({len(files)} entries)")
            if not has_canonical_py and not has_canonical_json:
                emit(f"     → SAFE TO DELETE (no canonical files, only backups)")
            else:
                emit(f"     ⚠  HAS CANONICAL FILES — review before deleting")
    if count == 0:
        emit("  (no shadow folders found — clean)")
    return count


def _scan_hooks(donor_root, moved, bench_root, emit):
    """Find hooks.py lines mentioning moved DocTypes."""
    hooks_paths = list(donor_root.rglob("hooks.py"))
    emit(f"\nFound {len(hooks_paths)} hooks.py file(s):")
    for h in hooks_paths:
        emit(f"  • {h.relative_to(bench_root)}")

    total = 0
    for h in hooks_paths:
        try:
            content = h.read_text()
        except Exception:
            continue
        emit(f"\n  ── {h.relative_to(bench_root)} ──")
        found = []
        for i, line in enumerate(content.splitlines(), 1):
            for dt in moved:
                if dt in line:
                    found.append((i, dt, line.rstrip()))
                    break
        if found:
            for i, dt, line in found:
                # Classify: comment vs real reference
                stripped = line.lstrip()
                tag = "COMMENT" if stripped.startswith("#") else "ACTIVE"
                marker = "  " if tag == "COMMENT" else "⚠ "
                emit(f"   {marker}line {i:3} [{tag}] ({dt}): {line[:130]}")
                if tag == "ACTIVE":
                    total += 1
        else:
            emit("   (no references)")
    return total


def _scan_utils(donor_root, moved_slugs, bench_root, emit):
    """Find utility .py files whose names suggest moved DocTypes."""
    hits = []
    for py_path in donor_root.rglob("*.py"):
        if "__pycache__" in str(py_path) or ".bak" in str(py_path):
            continue
        name_lower = py_path.name.lower()
        # Match if filename contains any moved slug fragment
        # Require the full slug (or a multi-word prefix of it) to appear in filename.
        # Single-word fragments like "batch" or "stock" are too noisy.
        for slug in moved_slugs:
            if slug in name_lower:
                hits.append((py_path, slug))
                break
    emit(f"\nFound {len(hits)} potentially-relevant .py files:")
    for p, slug in hits:
        rel = p.relative_to(bench_root)
        size = p.stat().st_size
        emit(f"  📄 {rel}  ({size} bytes)  matches: {slug}")
    return len(hits)


def _scan_fixtures(donor_root, moved, bench_root, emit):
    """Find fixture file entries for moved DocTypes."""
    fixture_files = list(donor_root.rglob("fixtures/*.json"))
    emit(f"\nFound {len(fixture_files)} fixture file(s)")
    total = 0
    for fxf in fixture_files:
        try:
            data = json.loads(fxf.read_text())
        except Exception as e:
            emit(f"  ⚠ {fxf.relative_to(bench_root)}: cannot parse ({e})")
            continue
        if not isinstance(data, list):
            continue

        hits = []
        for item in data:
            for key in ("dt", "doc_type", "document_type", "name"):
                v = item.get(key)
                if v in moved:
                    hits.append((key, v, item))
                    break
            else:
                # Check filters within Workflow / Custom Field fixtures
                filters = item.get("filters") or []
                for fl in filters if isinstance(filters, list) else []:
                    if isinstance(fl, list) and len(fl) >= 3:
                        v = fl[2]
                        if isinstance(v, list):
                            for vi in v:
                                if vi in moved:
                                    hits.append(("filter", vi, item))
                                    break
        if hits:
            total += len(hits)
            emit(f"\n  📄 {fxf.relative_to(bench_root)} — {len(hits)} hit(s)")
            for key, dt, item in hits[:8]:
                extra = (item.get("fieldname") or item.get("property")
                         or item.get("name") or "")
                emit(f"     {key}={dt!r:35}  {extra!r}")
            if len(hits) > 8:
                emit(f"     ... and {len(hits) - 8} more")
    if total == 0:
        emit("  (no fixture entries found — clean)")
    return total


def _scan_modules_txt(donor_root, bench_root, emit):
    for mt in donor_root.rglob("modules.txt"):
        rel = mt.relative_to(bench_root)
        try:
            content = mt.read_text().strip()
        except Exception:
            continue
        emit(f"\n  📄 {rel}")
        for line in content.splitlines():
            emit(f"     {line}")


def _scan_layout(donor_root, donor, moved_slugs, emit):
    """Detect triple-nested + shallow shadow paths."""
    deep_3 = donor_root / donor / donor / donor
    shallow_2 = donor_root / donor / donor

    emit(f"\n  Triple-nested path: apps/{donor}/{donor}/{donor}/{donor}")
    emit(f"     exists: {deep_3.exists()}")

    if shallow_2.exists():
        shallow_doctype = shallow_2 / "doctype"
        emit(f"\n  Shallow doctype dir: apps/{donor}/{donor}/{donor}/doctype/")
        emit(f"     exists: {shallow_doctype.exists()}")
        if shallow_doctype.exists():
            sub = sorted(p.name for p in shallow_doctype.iterdir() if p.is_dir())
            relevant = [s for s in sub if s in moved_slugs]
            emit(f"     {len(sub)} subdirs total, {len(relevant)} matching moved DocTypes")
            if relevant:
                emit(f"     matching: {relevant}")
