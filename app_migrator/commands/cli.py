import click
import os
import sys
from pathlib import Path

# Add app_migrator to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

@click.group(help="Frappe Cloud App Migration Tools")
def app_migrator():
    """Commands for analyzing and migrating Frappe Cloud applications."""
    pass

# Import and register all command modules
from . import api_keys, cloud_api, site_api, setup, analyze

# Register commands
app_migrator.add_command(api_keys.api_key_status)
app_migrator.add_command(cloud_api.list_sites)
app_migrator.add_command(cloud_api.get_account_info)
app_migrator.add_command(site_api.test_connection)
app_migrator.add_command(site_api.get_installed_apps)
app_migrator.add_command(setup.setup_wizard)
app_migrator.add_command(setup.setup_frappe_cloud)
app_migrator.add_command(setup.setup_site_api)
app_migrator.add_command(analyze.analyze_all)

if __name__ == "__main__":
    app_migrator()
