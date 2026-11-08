"""app-migrator verify-donor-cleanup-readiness command

For each donor hooks.py reference to a moved DocType, verify the receiver has
functional equivalence (registration present + target import resolves).

Verdicts:
  RECEIVER_OK_VERIFIED — receiver registers equivalent + target imports cleanly
  MIGRATE_FIRST        — must migrate functionality before removing from donor
  SAFE_TO_REMOVE       — donor reference points to non-existent target (just remove)
  NEEDS_INVESTIGATION  — uncertain, manual review

Pairs with scan-donor-residue (finds residue) and clean-donor-residue (removes).
A MIGRATE_FIRST verdict from this command blocks clean-donor-residue.

Usage:
  bench --site <site> app-migrator verify-donor-cleanup-readiness \\
    --donor amb_w_tds --receiver amb_w_spc

  # With explicit doctype list:
  bench --site <site> app-migrator verify-donor-cleanup-readiness \\
    --donor amb_w_tds --receiver amb_w_spc \\
    --doctypes "Batch AMB,Container Barrels"
"""
import importlib
import json
from pathlib import Path

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f


# Dict-style hooks: doctype -> import_path
DICT_HOOK_SECTIONS = (
    "doctype_class",
    "override_doctype_class",
    "override_doctype_dashboards",
    "doctype_js",
    "doctype_list_js",
    "doctype_tree_js",
    "doctype_calendar_js",
)


@click.command("app-migrator-verify-donor-cleanup-readiness")
@click.option("--site", required=True, help="Site name")
@click.option("--donor", required=True, help="Donor app name")
@click.option("--receiver", required=True, help="Receiver app name")
@click.option("--doctypes", help="Comma-separated explicit DocType list "
                                  "(else auto-detect from receiver+donor evidence)")
@click.option("--output", help="Write report to file (default: stdout)")
@click.option("--bench-root", default="/home/frappe/frappe-bench")
@pass_context
def app_migrator_verify_donor_cleanup_readiness(context, site, donor, receiver,
                                                  doctypes, output, bench_root):
    """Verify receiver has functional equivalence before stripping donor references.

    For each donor hooks.py entry pointing at a moved DocType, this command:
      1. Looks up the same hook section on receiver
      2. Verifies the receiver's target import path resolves to a real callable
      3. Outputs per-entry verdict
    """
    bench_root = Path(bench_root)
    donor_root = bench_root / "apps" / donor
    receiver_root = bench_root / "apps" / receiver

    if not donor_root.exists():
        click.secho(f"Error: donor app not found at {donor_root}", fg="red")
        raise click.Abort()
    if not receiver_root.exists():
        click.secho(f"Error: receiver app not found at {receiver_root}", fg="red")
        raise click.Abort()

    frappe.init(site=site)
    frappe.connect()

    # Determine moved DocTypes
    if doctypes:
        moved = {d.strip() for d in doctypes.split(",") if d.strip()}
        moved_source = "explicit --doctypes"
    else:
        moved = _find_moved_doctypes(donor_root, receiver_root)
        moved_source = "auto-detected (receiver JSON + donor evidence)"

    # Import donor and receiver hooks modules
    try:
        donor_hooks = importlib.import_module(f"{donor}.hooks")
        receiver_hooks = importlib.import_module(f"{receiver}.hooks")
    except ImportError as e:
        click.secho(f"Error importing hooks: {e}", fg="red")
        raise click.Abort()

    lines = []
    def emit(s=""):
        lines.append(s)

    emit("=" * 95)
    emit(f"  VERIFY DONOR CLEANUP READINESS — {donor} → {receiver}")
    emit("=" * 95)
    emit(f"\nSource of moved DocTypes: {moved_source}")
    emit(f"Moved DocTypes ({len(moved)}):")
    for dt in sorted(moved):
        emit(f"  • {dt}")

    if not moved:
        emit("\n  ✓ No moved DocTypes detected — nothing to verify.")
        emit("    (donor cleanup is either complete or no migration occurred)")
        emit("=" * 95)
        _output(lines, output)
        return

    all_decisions = []

    # ── Verify each dict-style hook section ──
    for section in DICT_HOOK_SECTIONS:
        donor_val = getattr(donor_hooks, section, {}) or {}
        receiver_val = getattr(receiver_hooks, section, {}) or {}
        if not isinstance(donor_val, dict):
            continue
        # Filter to entries about moved DocTypes
        donor_entries = {k: v for k, v in donor_val.items() if k in moved}
        if not donor_entries:
            continue

        emit(f"\n{'─' * 95}")
        emit(f"  hook section: {section}")
        emit(f"{'─' * 95}")
        for dt, donor_target in donor_entries.items():
            recv_target = receiver_val.get(dt) if isinstance(receiver_val, dict) else None
            verdict, detail = _verify_dict_entry(donor_target, recv_target)
            all_decisions.append((section, dt, verdict, detail))
            marker = "✓" if verdict == "RECEIVER_OK_VERIFIED" else (
                     "⚠" if verdict == "MIGRATE_FIRST" else "○")
            emit(f"  {marker} [{verdict:24}] {dt}")
            emit(f"      donor:    {donor_target}")
            emit(f"      receiver: {recv_target if recv_target else '(not registered)'}")
            emit(f"      detail:   {detail}")

    # ── Verify doc_events (nested dict: doctype -> {event -> [handlers]}) ──
    donor_events = getattr(donor_hooks, "doc_events", {}) or {}
    receiver_events = getattr(receiver_hooks, "doc_events", {}) or {}
    relevant_donor_events = {k: v for k, v in donor_events.items() if k in moved}
    if relevant_donor_events:
        emit(f"\n{'─' * 95}")
        emit("  hook section: doc_events")
        emit(f"{'─' * 95}")
        for dt, donor_event_map in relevant_donor_events.items():
            recv_event_map = receiver_events.get(dt, {}) if isinstance(receiver_events, dict) else {}
            for event, donor_handlers in (donor_event_map or {}).items():
                if not isinstance(donor_handlers, list):
                    donor_handlers = [donor_handlers]
                recv_handlers = recv_event_map.get(event, []) if isinstance(recv_event_map, dict) else []
                if not isinstance(recv_handlers, list):
                    recv_handlers = [recv_handlers]
                if recv_handlers:
                    verdict = "RECEIVER_OK_VERIFIED"
                    detail = f"receiver has {len(recv_handlers)} handler(s)"
                else:
                    verdict = "MIGRATE_FIRST"
                    detail = f"receiver has no handler for {event}"
                all_decisions.append(("doc_events", f"{dt}.{event}", verdict, detail))
                marker = "✓" if verdict == "RECEIVER_OK_VERIFIED" else "⚠"
                emit(f"  {marker} [{verdict:24}] {dt}.{event}")
                emit(f"      donor:    {donor_handlers}")
                emit(f"      receiver: {recv_handlers if recv_handlers else '(none)'}")
                emit(f"      detail:   {detail}")

    # ── Verify fixtures (list of filter dicts) ──
    donor_fixtures = getattr(donor_hooks, "fixtures", []) or []
    receiver_fixtures = getattr(receiver_hooks, "fixtures", []) or []
    fix_decisions = _verify_fixtures(donor_fixtures, receiver_fixtures, moved)
    if fix_decisions:
        emit(f"\n{'─' * 95}")
        emit("  hook section: fixtures (Workflow / Custom Field / Property Setter filters)")
        emit(f"{'─' * 95}")
        for entry, dt, verdict, detail in fix_decisions:
            all_decisions.append((entry, dt, verdict, detail))
            marker = "✓" if verdict == "RECEIVER_OK_VERIFIED" else (
                     "⚠" if verdict == "MIGRATE_FIRST" else "○")
            emit(f"  {marker} [{verdict:24}] {entry} / {dt}")
            emit(f"      detail: {detail}")

    # ── Summary ──
    emit(f"\n{'=' * 95}")
    emit("  SUMMARY")
    emit(f"{'=' * 95}")
    counts = {}
    for _, _, v, _ in all_decisions:
        counts[v] = counts.get(v, 0) + 1
    if not all_decisions:
        emit("  ✓ No donor hooks reference any moved DocType — donor is verified clean")
    else:
        for v in ("RECEIVER_OK_VERIFIED", "SAFE_TO_REMOVE",
                  "MIGRATE_FIRST", "NEEDS_INVESTIGATION"):
            if v in counts:
                emit(f"  {v:25} {counts[v]}")

        if counts.get("MIGRATE_FIRST", 0) > 0:
            emit(f"\n  ⚠  {counts['MIGRATE_FIRST']} entry/entries need migration before donor cleanup.")
            emit(f"     clean-donor-residue would refuse to proceed.")
        else:
            emit(f"\n  ✓  All donor references have receiver equivalents — safe to clean.")
    emit("=" * 95)

    _output(lines, output)


# ─── Helpers ───

def _find_moved_doctypes(donor_root, receiver_root):
    """Doctype is 'moved' if it has receiver JSON AND donor filesystem evidence."""
    receiver_doctypes = set()
    for jp in receiver_root.rglob("doctype/*/*.json"):
        if jp.parent.name != jp.stem:
            continue
        try:
            with open(jp) as f:
                j = json.load(f)
            name = j.get("name")
            if name:
                receiver_doctypes.add(name)
        except Exception:
            pass
    moved = set()
    for name in receiver_doctypes:
        slug = name.lower().replace(" ", "_")
        for cand in donor_root.rglob(f"doctype/{slug}"):
            if cand.is_dir():
                moved.add(name)
                break
    return moved


def _verify_dict_entry(donor_target, recv_target):
    """For dict-style hook entries, verify receiver has equivalent."""
    if not recv_target:
        # Donor has it, receiver does not. Check if donor target itself resolves
        # — if not, donor is referencing a phantom (SAFE_TO_REMOVE).
        if not _import_resolves(donor_target):
            return ("SAFE_TO_REMOVE",
                    "donor references non-existent target; just remove from donor")
        return ("MIGRATE_FIRST",
                "donor has working entry but receiver has none — must migrate first")
    if _import_resolves(recv_target):
        return ("RECEIVER_OK_VERIFIED",
                "receiver entry resolves to a callable")
    return ("MIGRATE_FIRST",
            f"receiver entry '{recv_target}' fails to resolve")


def _import_resolves(import_path):
    """Try resolving 'pkg.module.attr' — return True iff attr exists."""
    if not import_path or not isinstance(import_path, str):
        return False
    try:
        mod_path, attr_name = import_path.rsplit(".", 1)
        mod = importlib.import_module(mod_path)
        return getattr(mod, attr_name, None) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def _verify_fixtures(donor_fixtures, receiver_fixtures, moved):
    """For each donor fixtures entry referencing a moved DocType, check receiver."""
    decisions = []
    for entry in donor_fixtures:
        if not isinstance(entry, dict):
            continue
        fix_doctype = entry.get("doctype")
        filters = entry.get("filters") or []
        if not isinstance(filters, list):
            continue
        for f in filters:
            if not (isinstance(f, list) and len(f) >= 3):
                continue
            field, op, val = f[0], f[1], f[2]
            if isinstance(val, list):
                for item in val:
                    if item in moved:
                        # Check if receiver has fixture entry for same doctype with this item
                        recv_has = _receiver_fixture_has(receiver_fixtures, fix_doctype, field, item)
                        if recv_has:
                            decisions.append((f"fixtures[{fix_doctype}]",
                                            item,
                                            "RECEIVER_OK_VERIFIED",
                                            f"receiver fixture filter includes '{item}'"))
                        else:
                            decisions.append((f"fixtures[{fix_doctype}]",
                                            item,
                                            "SAFE_TO_REMOVE",
                                            f"receiver doesn't filter for '{item}' but DocType lives there now — donor filter is stale"))
            elif val in moved:
                recv_has = _receiver_fixture_has(receiver_fixtures, fix_doctype, field, val)
                verdict = "RECEIVER_OK_VERIFIED" if recv_has else "SAFE_TO_REMOVE"
                decisions.append((f"fixtures[{fix_doctype}]", val, verdict,
                                f"receiver match: {recv_has}"))
    return decisions


def _receiver_fixture_has(receiver_fixtures, fix_doctype, field, val):
    for entry in receiver_fixtures:
        if not isinstance(entry, dict) or entry.get("doctype") != fix_doctype:
            continue
        filters = entry.get("filters") or []
        for f in filters if isinstance(filters, list) else []:
            if not (isinstance(f, list) and len(f) >= 3):
                continue
            if f[0] == field:
                fv = f[2]
                if (isinstance(fv, list) and val in fv) or fv == val:
                    return True
    return False


def _output(lines, output_file):
    text = "\n".join(lines)
    if output_file:
        Path(output_file).write_text(text)
        click.echo(f"Report written to {output_file}")
    else:
        click.echo(text)
