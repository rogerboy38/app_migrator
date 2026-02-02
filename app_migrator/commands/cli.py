# app_migrator/commands/cli.py
import click

@click.group(help="Frappe Cloud App Migration Tools")
def app_migrator():
    pass

# ==================== API KEY COMMANDS ====================
@app_migrator.command("api-key-setup")
def api_key_setup_cmd():
    from .api_key_manager import api_key_setup
    return api_key_setup()

@app_migrator.command("api-key-status")
def api_key_status_cmd():
    from .api_key_manager import api_key_status
    return api_key_status()

@app_migrator.command("api-key-cleanup")
def api_key_cleanup_cmd():
    from .api_key_manager import api_key_cleanup
    return api_key_cleanup()

# ==================== SETUP COMMANDS ====================
@app_migrator.command("quick-setup")
@click.option("--fc-key", prompt=True, hide_input=True)
@click.option("--fc-secret", prompt=True, hide_input=True)
def quick_setup_cmd(fc_key, fc_secret):
    from .setup import quick_setup
    return quick_setup(fc_key, fc_secret)

@app_migrator.command("simple-api-setup")
@click.option("--site-url", prompt=True)
@click.option("--site-key", prompt=True, hide_input=True)
@click.option("--site-secret", prompt=True, hide_input=True)
def simple_api_setup_cmd(site_url, site_key, site_secret):
    from .setup import simple_api_setup
    return simple_api_setup(site_url, site_key, site_secret)

@app_migrator.command("setup-wizard")
def setup_wizard_cmd():
    from .setup import setup_wizard
    return setup_wizard()

# ==================== ANALYSIS COMMANDS ====================
@app_migrator.command("test-connection")
@click.option("--site", help="Site to test")
def test_connection_cmd(site):
    from .analyze import test_connection
    return test_connection(site)

@app_migrator.command("get-site-info")
@click.option("--site-name", help="Site name")
def get_site_info_cmd(site_name):
    from .analyze import get_site_info
    return get_site_info(site_name)

@app_migrator.command("analyze-apps")
@click.option("--site-url", help="Site URL")
@click.option("--output-format", default="table")
@click.option("--detailed", is_flag=True)
def analyze_apps_cmd(site_url, output_format, detailed):
    from .analyze import analyze_apps
    return analyze_apps(site_url, output_format, detailed)

if __name__ == "__main__":
    app_migrator()
