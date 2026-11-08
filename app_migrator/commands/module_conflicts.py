"""app-migrator-module-conflicts: detect cross-app Python symbol collisions (L394).

W2 (d): replaces the Phase-4 envelope stub with real cross-app collision
detection. It walks every installed app's Python package, collects top-level
symbols (functions, classes, module-level constants) via the ``ast`` module,
and flags any symbol name declared in two or more distinct apps — the L394
``l394_symbol_collision`` radar pattern (severity: high per L380).

Findings are emitted through the v0.5 envelope contract (``_envelope.py``):
schema_version=1.0.0, with stable finding ids (``l394-collision-<symbol>``) so
runs diff cleanly. Status is ``warn`` when collisions exist (advisory, not a
hard block) and ``ok`` when the symbol space is clean.

The detection core (``scan_collisions``) is import-safe and bench-free so it can
be unit-tested in-process; only the click wrapper touches the envelope/exit path.
"""
from __future__ import annotations

import ast
import os
import re
import time
from typing import Any, Dict, List, Optional

import click

try:
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f

from ._envelope import emit_envelope, make_envelope

DEFAULT_APPS_ROOT = os.environ.get("BENCH_APPS_ROOT", "/home/frappe/frappe-bench/apps")

# Dirs we never treat as source (vendored / build / vcs noise).
_SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "env", "dist", "build",
    ".eggs", "test", "tests", "fixtures", ".tox", "migrations",
}

# Frappe's hooks.py is a declarative registration module: its top-level names
# (app_name, app_title, app_publisher, after_install, doc_events, ...) are
# framework-convention metadata/callbacks, identical across apps BY DESIGN, and
# never cause an import-time collision (each is <app>.hooks.<name>). Excluding it
# from the default scan removes ~framework noise; --all-symbols restores it.
_FRAMEWORK_CONFIG_FILES = {"hooks.py"}

# Cap on findings carried in the envelope (full count always reported in evidence).
DEFAULT_FINDING_LIMIT = 200


def _iter_app_names(apps_root: str) -> List[str]:
    """Return installed app names.

    Prefer apps.txt (the canonical install manifest); fall back to listing
    top-level dirs under apps_root that contain an inner same-named package.
    """
    apps_txt = os.path.join(apps_root, "apps.txt")
    if os.path.isfile(apps_txt):
        try:
            with open(apps_txt) as fh:
                names = [ln.strip() for ln in fh if ln.strip()]
            if names:
                return names
        except OSError:
            pass
    names = []
    if os.path.isdir(apps_root):
        for entry in sorted(os.listdir(apps_root)):
            if os.path.isdir(os.path.join(apps_root, entry)):
                names.append(entry)
    return names


def _package_dir(apps_root: str, app: str) -> Optional[str]:
    """Resolve the inner Python package dir for an app (apps/<app>/<app>)."""
    inner = os.path.join(apps_root, app, app)
    if os.path.isdir(inner):
        return inner
    # Fallback: some apps keep their package directly under apps/<app>.
    outer = os.path.join(apps_root, app)
    if os.path.isdir(outer):
        return outer
    return None


def _top_level_symbols(source: str) -> List[str]:
    """Extract module-level def/class/constant names from Python source.

    Returns names declared at module scope only — the symbols that participate
    in import-time binding. Syntax errors yield an empty list (best-effort scan).
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    names: List[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.append(target.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                names.append(node.target.id)
    return names


def scan_collisions(
    apps_root: str = DEFAULT_APPS_ROOT,
    app_names: Optional[List[str]] = None,
    symbol_filter: Optional[str] = None,
    all_symbols: bool = False,
) -> Dict[str, Any]:
    """Scan installed apps for cross-app top-level symbol collisions (L394).

    Args:
        apps_root: bench apps/ directory.
        app_names: explicit app subset (default: all installed).
        symbol_filter: optional regex; only symbols matching are considered.
        all_symbols: when False (default), dunder/private names (``_x``,
            ``__x__``) are excluded to cut import-machinery noise; when True,
            every module-level symbol is inventoried.

    Returns a dict with: symbol -> sorted list of apps declaring it (collisions
    only, i.e. >= 2 distinct apps), plus scan counters under ``_stats``.
    """
    apps = app_names if app_names is not None else _iter_app_names(apps_root)
    flt = re.compile(symbol_filter) if symbol_filter else None

    # symbol -> {app -> count of files declaring it}
    symbol_apps: Dict[str, Dict[str, int]] = {}
    files_scanned = 0
    apps_scanned = 0

    for app in apps:
        pkg = _package_dir(apps_root, app)
        if not pkg:
            continue
        apps_scanned += 1
        for dirpath, dirnames, filenames in os.walk(pkg):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            for fn in filenames:
                if not fn.endswith(".py"):
                    continue
                if not all_symbols and fn in _FRAMEWORK_CONFIG_FILES:
                    continue
                fpath = os.path.join(dirpath, fn)
                try:
                    with open(fpath, encoding="utf-8", errors="replace") as fh:
                        source = fh.read()
                except OSError:
                    continue
                files_scanned += 1
                for sym in _top_level_symbols(source):
                    if not all_symbols and sym.startswith("_"):
                        continue
                    if flt and not flt.search(sym):
                        continue
                    symbol_apps.setdefault(sym, {})
                    symbol_apps[sym][app] = symbol_apps[sym].get(app, 0) + 1

    collisions = {
        sym: sorted(app_map.keys())
        for sym, app_map in symbol_apps.items()
        if len(app_map) >= 2
    }
    return {
        "collisions": collisions,
        "_stats": {
            "apps_scanned": apps_scanned,
            "files_scanned": files_scanned,
            "distinct_symbols": len(symbol_apps),
            "collision_count": len(collisions),
        },
    }


def build_findings(collisions: Dict[str, List[str]], limit: int = DEFAULT_FINDING_LIMIT) -> List[Dict[str, Any]]:
    """Turn a collisions map into envelope findings (severity: high per L380)."""
    findings: List[Dict[str, Any]] = []
    # Deterministic order: most-shared symbols first, then alphabetical.
    ordered = sorted(collisions.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    for sym, apps in ordered[:limit]:
        findings.append({
            "id": f"l394-collision-{sym}",
            "title": f"cross-app symbol collision: {sym}",
            "severity": "high",
            "description": (
                f"Top-level symbol '{sym}' is declared in {len(apps)} apps "
                f"({', '.join(apps)}). At module load this risks silent override "
                f"or intermittent ImportError (L394 l394_symbol_collision)."
            ),
            "symbol": sym,
            "apps": apps,
        })
    return findings


@click.command('app-migrator-module-conflicts')
@click.option('--site', default=None, help='Site name (informational; not required)')
@click.option('--json', 'as_json', is_flag=True, help='Emit v0.5 envelope JSON')
@click.option('--all-symbols', 'all_symbols', is_flag=True,
              help='Inventory every module-level symbol (include _private/__dunder__)')
@click.option('--filter', 'symbol_filter', default=None,
              help='Only consider symbols matching this regex')
@click.option('--apps-root', default=DEFAULT_APPS_ROOT, show_default=True,
              help='bench apps/ directory to scan')
@click.option('--limit', default=DEFAULT_FINDING_LIMIT, show_default=True, type=int,
              help='Max collision findings carried in the envelope')
@pass_context
def app_migrator_module_conflicts(context, site, as_json, all_symbols, symbol_filter, apps_root, limit):
    """Detect cross-app Python symbol collisions (L394 radar pattern)."""
    start = time.time()
    result = scan_collisions(
        apps_root=apps_root,
        symbol_filter=symbol_filter,
        all_symbols=all_symbols,
    )
    collisions = result["collisions"]
    stats = result["_stats"]
    findings = build_findings(collisions, limit=limit)
    truncated = stats["collision_count"] - len(findings)

    if as_json:
        status = "warn" if collisions else "ok"
        summary = (
            f"module-conflicts: {stats['collision_count']} cross-app symbol "
            f"collision(s) across {stats['apps_scanned']} apps / "
            f"{stats['files_scanned']} files"
            + (f" (showing first {len(findings)})" if truncated > 0 else "")
        )
        envelope = make_envelope(
            command="module-conflicts",
            status=status,
            summary=summary,
            findings=findings,
            evidence=[
                {"kind": "scan_stats", **stats},
                {"kind": "scan_params",
                 "apps_root": apps_root,
                 "all_symbols": all_symbols,
                 "symbol_filter": symbol_filter,
                 "findings_truncated": max(truncated, 0)},
            ],
            suggested_next_commands=[
                {
                    "command": "bench app-migrator audit-modules-disk-vs-db --site <site>",
                    "approval_required": False,
                    "description": "Audit modules disk-vs-db for canonical module map.",
                },
            ],
            site=site,
            start_time=start,
        )
        emit_envelope(envelope)

    # Human-readable fallback (no --json).
    click.echo("Module-Conflicts: L394 cross-app Python symbol collision detector")
    click.echo(
        f"Scanned {stats['apps_scanned']} apps / {stats['files_scanned']} files; "
        f"{stats['distinct_symbols']} distinct symbols; "
        f"{stats['collision_count']} collision(s)."
    )
    for f in findings:
        click.echo(f"  [high] {f['symbol']}: {', '.join(f['apps'])}")
    if truncated > 0:
        click.echo(f"  ... {truncated} more collision(s) not shown (use --limit).")
    click.echo("Use --json for v0.5 envelope output.")
