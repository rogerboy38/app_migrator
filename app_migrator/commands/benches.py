"""app-migrator-benches command (T1.8.2 — extracted from __init__.py;
T1.9 switched to discover_all_benches for proper apps.txt + sites/ +
Procfile detection, with legacy ~/frappe-bench* glob as a fallback)."""

import os

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f
from ._shared import (
    detect_available_benches,
    discover_all_benches,
    get_bench_apps,
)


@click.command('app-migrator-benches')
@pass_context
def app_migrator_benches(context):
    """List all available benches and their apps"""
    print("🏗️ MULTI-BENCH ANALYSIS")
    print("=" * 60)

    # T1.9: prefer discover_all_benches (proper apps.txt + sites/ + Procfile
    # detection — catches benches with non-conventional names). Fall back
    # to the legacy ~/frappe-bench* glob if discovery returns nothing,
    # so we don't silently regress on machines where benches don't yet
    # have a Procfile (rare, but seen on broken setups).
    bench_paths = discover_all_benches()
    if not bench_paths:
        bench_paths = [
            os.path.expanduser(f"~/{name}")
            for name in detect_available_benches()
        ]

    print(f"Found {len(bench_paths)} benches:\n")

    for bench_path in bench_paths:
        bench_name = os.path.basename(bench_path)
        apps = get_bench_apps(bench_path)
        print(f"📦 {bench_name}: {len(apps)} apps")
        for app in apps:
            print(f"   • {app}")
        print()
