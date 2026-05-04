"""app-migrator-apps command (T1.8.2 — extracted from __init__.py)"""

import os

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    pass_context = lambda f: f


@click.command('app-migrator-apps')
@click.option('--site', help='Site name (optional)')
@pass_context
def app_migrator_apps(context, site):
    """List downloaded apps vs installed apps"""
    print("📦 APP INVENTORY")
    print("=" * 60)

    # Get downloaded apps from apps directory
    apps_dir = os.path.expanduser("~/frappe-bench/apps")
    downloaded = []
    if os.path.exists(apps_dir):
        for item in os.listdir(apps_dir):
            item_path = os.path.join(apps_dir, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                # Check if it's a valid Frappe app
                has_hooks = os.path.exists(os.path.join(item_path, item, "hooks.py")) or \
                           os.path.exists(os.path.join(item_path, "hooks.py"))
                has_pyproject = os.path.exists(os.path.join(item_path, "pyproject.toml"))
                if has_hooks or has_pyproject:
                    downloaded.append(item)

    downloaded = sorted(downloaded)

    # Get installed apps if site provided
    installed = []
    if site:
        try:
            frappe.init(site=site)
            frappe.connect()
            installed = frappe.get_installed_apps()
            frappe.db.close()
        except Exception:
            pass

    print(f"\n📥 DOWNLOADED APPS ({len(downloaded)}):")
    for app in downloaded:
        status = "✅ installed" if app in installed else "⬜ not installed"
        print(f"   {app:30} {status}")

    if site and installed:
        not_downloaded = [a for a in installed if a not in downloaded]
        if not_downloaded:
            print(f"\n⚠️ INSTALLED BUT NOT IN APPS DIR:")
            for app in not_downloaded:
                print(f"   {app}")

    print(f"\n📊 SUMMARY:")
    print(f"   Downloaded: {len(downloaded)}")
    print(f"   Installed:  {len(installed)}")
    print(f"   Available:  {len(downloaded) - len(installed)}")
