"""app-migrator clean-donor-residue command — final donor cleanup pass.

After migrate-module has moved DocTypes from donor → receiver, the donor's
hooks.py often retains stale entries that still reference the moved DocTypes:
  - Dict-style hook sections (doctype_class, override_doctype_class, etc.)
  - fixtures = [...] entries with filters listing moved DocTypes

This command uses verify-donor-cleanup-readiness as the gate: ONLY entries
marked SAFE_TO_REMOVE are touched. MIGRATE_FIRST entries (donor still has
canonical) and RECEIVER_OK_VERIFIED entries (already done) are left alone.

Edit strategy: ast.parse hooks.py to identify exact line ranges of each
removable item, then text-edit those positions surgically. Preserves
comments, blank lines, and surrounding formatting.

Default --dry-run. --apply required for changes. Snapshot before any edits.

Usage:
  bench app-migrator clean-donor-residue \
    --site <site> \
    --donor <donor-app> \
    --receiver <receiver-app>

  # Apply after reviewing dry-run:
  bench app-migrator clean-donor-residue \
    --site <site> \
    --donor <donor-app> \
    --receiver <receiver-app> \
    --apply

Real-data validation (v1.0 + v1.1):
  Tested end-to-end against rogerboy38/crm_host (donor) -> frappe/crm (receiver)
  with 43 overlapping DocTypes (full overlap confirmed via comm -12). Planted
  controlled stale residue: 2 dict_class entries with phantom targets, 4 fixture
  filter values across list_item and whole_filter_line shapes. Both --dry-run
  (correct plan output) and --apply (surgical edits + snapshot + export-fixtures
  + bench migrate) succeeded. v1.1 post-pass additionally cleaned empty stubs
  left by v1.0 (empty doctype_class = {}, empty ["dt", "in", []] filter rows).
  Snapshots: clean_donor_residue_crm_host_20260506_215210.json (v1.0),
  clean_donor_residue_crm_host_20260506_220722.json (v1.1).
"""
import ast
import json
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

# Reuse verify's helpers — these contain the SAFE_TO_REMOVE detection logic
from app_migrator.commands.verify_donor_cleanup_readiness import (
    DICT_HOOK_SECTIONS,
    _find_moved_doctypes,
    _verify_dict_entry,
    _verify_fixtures,
)


def _load_hooks_module(app_root, app_name):
    """Import donor or receiver hooks.py as a module without polluting sys.modules."""
    import importlib.util
    hooks_py = app_root / app_name / "hooks.py"
    if not hooks_py.exists():
        return None, None
    spec = importlib.util.spec_from_file_location(
        f"_cdr_{app_name}_hooks", str(hooks_py)
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, hooks_py


def _find_dict_key_lines(tree, section_name, key_to_find):
    """Locate a key in a top-level dict assignment. Returns (start_line, end_line)
    1-indexed inclusive, or None if not found."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not (isinstance(target, ast.Name) and target.id == section_name):
                continue
            if not isinstance(node.value, ast.Dict):
                return None
            for k, v in zip(node.value.keys, node.value.values, strict=False):
                if isinstance(k, ast.Constant) and k.value == key_to_find:
                    start = k.lineno
                    end = v.end_lineno or k.lineno
                    return (start, end)
    return None


def _delete_lines(text, line_ranges):
    """Delete the given (start, end) inclusive 1-indexed line ranges from text."""
    if not line_ranges:
        return text, 0
    lines = text.split("\n")
    line_ranges = sorted(set(line_ranges), reverse=True)
    deletions = 0
    for start, end in line_ranges:
        i_start = start - 1
        i_end = end
        if 0 <= i_start < len(lines) and i_end <= len(lines):
            del lines[i_start:i_end]
            deletions += (i_end - i_start)
    return "\n".join(lines), deletions


def _find_fixture_value_positions(tree, values_to_remove):
    """For each occurrence of a value-string in a fixtures filter list,
    return position dicts so we can text-edit."""
    positions = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "fixtures" for t in node.targets):
            continue
        if not isinstance(node.value, ast.List):
            continue
        for entry in node.value.elts:
            if not isinstance(entry, ast.Dict):
                continue
            for k, v in zip(entry.keys, entry.values, strict=False):
                if not (isinstance(k, ast.Constant) and k.value == "filters"):
                    continue
                if not isinstance(v, ast.List):
                    continue
                for filter_item in v.elts:
                    if not (isinstance(filter_item, ast.List) and len(filter_item.elts) >= 3):
                        continue
                    third = filter_item.elts[2]
                    if isinstance(third, ast.List):
                        for s in third.elts:
                            if isinstance(s, ast.Constant) and s.value in values_to_remove:
                                positions.append({
                                    "kind": "list_item",
                                    "line": s.lineno,
                                    "col": s.col_offset,
                                    "end_col": s.end_col_offset,
                                    "value": s.value,
                                })
                    elif isinstance(third, ast.Constant) and third.value in values_to_remove:
                        positions.append({
                            "kind": "whole_filter_line",
                            "line": filter_item.lineno,
                            "end_line": filter_item.end_lineno or filter_item.lineno,
                            "value": third.value,
                        })
    return positions


def _strip_value_from_text(text, position):
    """Surgically remove a single string-literal value from the source text."""
    lines = text.split("\n")
    line_idx = position["line"] - 1
    if not (0 <= line_idx < len(lines)):
        return text, False
    line = lines[line_idx]
    col = position["col"]
    end_col = position["end_col"]
    if end_col > len(line) or col < 0:
        return text, False
    after = line[end_col:]
    trail_strip = 0
    if after.startswith(", "):
        trail_strip = 2
    elif after.startswith(","):
        trail_strip = 1
    elif after.startswith(" ,"):
        trail_strip = 2
    new_line = line[:col] + line[end_col + trail_strip:]
    if new_line.strip() == "":
        del lines[line_idx]
    else:
        lines[line_idx] = new_line
    return "\n".join(lines), True


def _strip_whole_filter_line(text, position):
    """Remove a single filter row like `["name", "=", "Foo"],` (line range)."""
    lines = text.split("\n")
    start = position["line"] - 1
    end = position["end_line"]
    if not (0 <= start < len(lines) and end <= len(lines)):
        return text, False
    del lines[start:end]
    return "\n".join(lines), True


@click.command("app-migrator-clean-donor-residue")
@click.option("--site", required=True, help="Site name")
@click.option("--donor", required=True, help="Donor app name")
@click.option("--receiver", required=True, help="Receiver app name")
@click.option("--apply", is_flag=True, help="Apply cleanup (default: dry-run)")
@click.option("--bench-root", default="/home/frappe/frappe-bench")
@click.option("--snapshot-dir",
              default="/home/frappe/frappe-bench/sites/snapshots")
@pass_context
def app_migrator_clean_donor_residue(context, site, donor, receiver, apply,
                                       bench_root, snapshot_dir):
    """Remove stale donor references after a migrate-module transfer.

    Gated by verify-donor-cleanup-readiness: only SAFE_TO_REMOVE items
    are touched. MIGRATE_FIRST items abort the cleanup with guidance.
    """
    bench_root = Path(bench_root)
    donor_root = bench_root / "apps" / donor
    receiver_root = bench_root / "apps" / receiver
    dry_run = not apply
    mode = "DRY-RUN" if dry_run else "APPLY"

    click.secho("\n" + "=" * 78, fg="cyan")
    click.secho(f"  CLEAN-DONOR-RESIDUE — {donor} → {receiver}  [{mode}]",
                fg="cyan", bold=True)
    click.secho("=" * 78, fg="cyan")

    if not donor_root.exists():
        click.secho(f"\n✗ Donor app not found: {donor_root}", fg="red")
        raise click.Abort()
    if not receiver_root.exists():
        click.secho(f"\n✗ Receiver app not found: {receiver_root}", fg="red")
        raise click.Abort()

    donor_hooks, donor_hooks_py = _load_hooks_module(donor_root, donor)
    if donor_hooks is None:
        click.secho(f"\n✗ Donor hooks.py not found: {donor_root}/{donor}/hooks.py",
                    fg="red")
        raise click.Abort()
    receiver_hooks, _ = _load_hooks_module(receiver_root, receiver)
    if receiver_hooks is None:
        click.secho(f"\n✗ Receiver hooks.py not found: {receiver_root}/{receiver}/hooks.py",
                    fg="red")
        raise click.Abort()

    moved = _find_moved_doctypes(donor_root, receiver_root)
    if not moved:
        click.secho("\n  ✓ No moved DocTypes detected — donor cleanup not needed",
                    fg="green")
        return

    click.secho(f"\n  Moved DocTypes ({len(moved)}):", fg="cyan")
    for dt in sorted(moved):
        click.echo(f"    • {dt}")

    dict_removals = []
    blocked_migrate_first = []

    for section in DICT_HOOK_SECTIONS:
        donor_val = getattr(donor_hooks, section, {}) or {}
        receiver_val = getattr(receiver_hooks, section, {}) or {}
        if not isinstance(donor_val, dict):
            continue
        for dt_name in list(donor_val.keys()):
            if dt_name not in moved:
                continue
            donor_target = donor_val[dt_name]
            recv_target = receiver_val.get(dt_name)
            verdict, reason = _verify_dict_entry(donor_target, recv_target)
            if verdict == "SAFE_TO_REMOVE":
                dict_removals.append((section, dt_name, reason))
            elif verdict == "MIGRATE_FIRST":
                blocked_migrate_first.append((section, dt_name, reason))

    donor_fixtures = getattr(donor_hooks, "fixtures", []) or []
    receiver_fixtures = getattr(receiver_hooks, "fixtures", []) or []
    fixture_decisions = _verify_fixtures(donor_fixtures, receiver_fixtures, moved)
    fixture_safe_to_remove = [d for d in fixture_decisions if d[2] == "SAFE_TO_REMOVE"]
    fixture_blocked = [d for d in fixture_decisions if d[2] == "MIGRATE_FIRST"]

    if blocked_migrate_first or fixture_blocked:
        click.secho("\n  ✗ Cleanup BLOCKED — these entries are MIGRATE_FIRST:",
                    fg="red", bold=True)
        for section, key, reason in blocked_migrate_first:
            click.secho(f"    • {section}['{key}']: {reason}", fg="red")
        for section, val, _v, reason in fixture_blocked:
            click.secho(f"    • {section} value '{val}': {reason}", fg="red")
        click.secho("\n  Run migrate-module on these DocTypes first, then re-run.",
                    fg="cyan")
        raise click.Abort()

    if not dict_removals and not fixture_safe_to_remove:
        click.secho("\n  ✓ No residue detected — donor is already clean",
                    fg="green")
        return

    click.secho("\n┌── PLAN ────", fg="cyan")
    if dict_removals:
        click.echo(f"│  Hook section entries to remove: {len(dict_removals)}")
        for section, key, _reason in dict_removals:
            click.echo(f"│    • {section}['{key}']")
    if fixture_safe_to_remove:
        click.echo(f"│  Fixture filter values to remove: {len(fixture_safe_to_remove)}")
        for section, val, _v, _reason in fixture_safe_to_remove:
            click.echo(f"│    • {section} value '{val}'")
    click.echo("│  Snapshot donor hooks.py")
    click.echo("│  Edit donor hooks.py (surgical text edits)")
    click.echo("│  Run bench export-fixtures --app <donor>")
    click.echo("│  Clear pycache + bench migrate")
    click.echo("└────")

    if dry_run:
        click.secho("\n  This was a DRY-RUN. To apply, re-run with --apply.",
                    fg="yellow")
        return

    snap_dir = Path(snapshot_dir)
    snap_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_file = snap_dir / f"clean_donor_residue_{donor}_{ts}.json"
    snap_file.write_text(json.dumps({
        "donor": donor,
        "receiver": receiver,
        "donor_hooks_py": str(donor_hooks_py),
        "donor_hooks_py_before": donor_hooks_py.read_text(),
        "dict_removals": dict_removals,
        "fixture_removals": [list(d) for d in fixture_safe_to_remove],
        "moved_doctypes": sorted(moved),
        "timestamp": ts,
    }, indent=2))
    click.secho(f"\n  📦 Snapshot: {snap_file}", fg="green")

    hooks_text = donor_hooks_py.read_text()
    tree = ast.parse(hooks_text)

    line_ranges_to_delete = []
    for section, key, _reason in dict_removals:
        rng = _find_dict_key_lines(tree, section, key)
        if rng is not None:
            line_ranges_to_delete.append(rng)
        else:
            click.secho(f"  ⚠ Could not locate {section}['{key}'] in hooks.py — "
                        "skipping this entry", fg="yellow")

    values_to_remove = set(d[1] for d in fixture_safe_to_remove)
    fixture_positions = _find_fixture_value_positions(tree, values_to_remove)

    edited_text = hooks_text

    fixture_positions_sorted = sorted(
        fixture_positions,
        key=lambda p: (p["line"], p.get("col", 0)),
        reverse=True,
    )
    fix_count = 0
    for pos in fixture_positions_sorted:
        if pos["kind"] == "list_item":
            edited_text, ok = _strip_value_from_text(edited_text, pos)
        else:
            edited_text, ok = _strip_whole_filter_line(edited_text, pos)
        if ok:
            fix_count += 1

    if line_ranges_to_delete:
        try:
            tree2 = ast.parse(edited_text)
            line_ranges_fresh = []
            for section, key, _reason in dict_removals:
                rng = _find_dict_key_lines(tree2, section, key)
                if rng is not None:
                    line_ranges_fresh.append(rng)
            edited_text, deleted = _delete_lines(edited_text, line_ranges_fresh)
        except SyntaxError as e:
            click.secho(f"  ⚠ hooks.py no longer parses after fixture edits: {e}",
                        fg="yellow")
            click.secho("  → Restoring snapshot and aborting.", fg="red")
            donor_hooks_py.write_text(hooks_text)
            raise click.Abort()
    else:
        deleted = 0

    # ----- v1.1: empty container post-pass --------------------------------
    # After the surgical removals above, top-level dict sections may now be
    # empty (e.g. doctype_class = {}) and filter rows may have empty inner
    # lists (e.g. ["dt", "in", []]). Remove those empty stubs entirely.
    try:
        tree3 = ast.parse(edited_text)
        empty_lines = []

        for n in tree3.body:
            if not isinstance(n, ast.Assign):
                continue
            target_names = [t.id for t in n.targets if isinstance(t, ast.Name)]
            section_name = target_names[0] if target_names else None

            # Empty top-level dict sections (doctype_class = {} etc.)
            if (section_name in DICT_HOOK_SECTIONS
                and isinstance(n.value, ast.Dict) and not n.value.keys):
                empty_lines.append((n.lineno, n.end_lineno or n.lineno))

            # Empty fixture filter rows (["dt", "in", []])
            if section_name == "fixtures" and isinstance(n.value, ast.List):
                for entry in n.value.elts:
                    if not isinstance(entry, ast.Dict):
                        continue
                    for k, v in zip(entry.keys, entry.values, strict=False):
                        if not (isinstance(k, ast.Constant) and k.value == "filters"):
                            continue
                        if not isinstance(v, ast.List):
                            continue
                        for filter_item in v.elts:
                            if not (isinstance(filter_item, ast.List) and len(filter_item.elts) >= 3):
                                continue
                            third = filter_item.elts[2]
                            if isinstance(third, ast.List) and not third.elts:
                                empty_lines.append((filter_item.lineno, filter_item.end_lineno or filter_item.lineno))

        if empty_lines:
            edited_text, _n_removed = _delete_lines(edited_text, empty_lines)
            click.secho(f"  ✓ Post-pass: removed {len(empty_lines)} empty container(s)/filter row(s)", fg="cyan")
    except SyntaxError as e:
        click.secho(f"  ⚠ Post-pass skipped (parse failed): {e}", fg="yellow")

    donor_hooks_py.write_text(edited_text)
    click.secho(f"  ✓ hooks.py edited: removed {deleted} dict line(s), "
                f"{fix_count} fixture value(s)", fg="green")

    try:
        ast.parse(edited_text)
    except SyntaxError as e:
        click.secho(f"\n  ⚠ Edited hooks.py FAILED to parse: {e}", fg="red")
        click.secho("  → Restoring snapshot.", fg="red")
        donor_hooks_py.write_text(hooks_text)
        raise click.Abort()

    click.secho("\n  Running bench export-fixtures...", fg="cyan")
    ret = subprocess.run(
        ["bench", "--site", site, "export-fixtures", "--app", donor],
        capture_output=True, text=True, cwd=str(bench_root),
    )
    if ret.returncode == 0:
        click.secho(f"  ✓ Exported fixtures for {donor}", fg="green")
    else:
        click.secho(f"  ⚠ export-fixtures returned non-zero (continuing): "
                    f"{ret.stderr[:200]}", fg="yellow")

    cleared = 0
    for cache_dir in bench_root.rglob("__pycache__"):
        shutil.rmtree(cache_dir, ignore_errors=True)
        cleared += 1
    if cleared:
        click.echo(f"  ✓ Cleared {cleared} __pycache__ dir(s)")

    click.secho("\n  Running bench migrate...", fg="cyan")
    ret = subprocess.run(
        ["bench", "--site", site, "migrate"],
        capture_output=True, text=True, cwd=str(bench_root),
    )
    if ret.returncode != 0:
        click.secho(f"\n  ⚠ bench migrate failed (snapshot at {snap_file}):",
                    fg="yellow")
        click.echo(ret.stderr[-1500:])
        return

    click.secho(f"\n{'=' * 78}", fg="green")
    click.secho("  ✓ CLEAN-DONOR-RESIDUE COMPLETE", fg="green", bold=True)
    click.secho("=" * 78, fg="green")
    click.echo(f"  Donor:               {donor}")
    click.echo(f"  Receiver:            {receiver}")
    click.echo(f"  Hook entries removed: {len(dict_removals)}")
    click.echo(f"  Fixture values removed: {len(fixture_safe_to_remove)}")
    click.echo(f"  Snapshot:            {snap_file.name}")

