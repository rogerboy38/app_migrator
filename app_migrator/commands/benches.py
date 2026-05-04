"""app-migrator-benches command (T1.8.2 — extracted from __init__.py)"""

import os

import click

try:
    import frappe  # noqa: F401
    from frappe.commands import pass_context
except ImportError:
    pass_context = lambda f: f

from ._shared import detect_available_benches, get_bench_apps


@click.command('app-migrator-benches')
@pass_context
def app_migrator_benches(context):
    """List all available benches and their apps"""
    print("🏗️ MULTI-BENCH ANALYSIS")
    print("=" * 60)

    benches = detect_available_benches()
    print(f"Found {len(benches)} benches:\n")

    for bench in benches:
        bench_path = os.path.expanduser(f"~/{bench}")
        apps = get_bench_apps(bench_path)
        print(f"📦 {bench}: {len(apps)} apps")
        for app in apps:
            print(f"   • {app}")
        print()
