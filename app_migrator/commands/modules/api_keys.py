# app_migrator/commands/modules/api_keys.py
import click
import json
import os
from pathlib import Path

API_KEY_STORE = Path.home() / ".frappe_migrator_keys.json"

class APIKeyManager:
    """Manage API keys for Frappe Cloud and sites."""
    
    def __init__(self):
        self.data = self._load_data()
    
    def _load_data(self):
        if API_KEY_STORE.exists():
            with open(API_KEY_STORE) as f:
                return json.load(f)
        return {"frappe_cloud": {}, "sites": {}, "teams": {}}
    
    def save(self):
        with open(API_KEY_STORE, 'w') as f:
            json.dump(self.data, f, indent=2)

@click.command("api-key-status")
def api_key_status():
    """Show stored API keys."""
    manager = APIKeyManager()
    click.echo("\n📊 API Key Status")
    click.echo("-" * 40)
    
    fc = manager.data.get("frappe_cloud", {})
    if fc.get("api_key"):
        click.echo(f"Frappe Cloud: ✅ Configured")
        click.echo(f"  Team: {fc.get('team_name', 'Unknown')}")
    else:
        click.echo("Frappe Cloud: ❌ Not configured")
    
    sites = manager.data.get("sites", {})
    click.echo(f"Configured Sites: {len(sites)}")
    for site, config in sites.items():
        status = "✅" if config.get("api_key") else "❌"
        click.echo(f"  {status} {site}")

@click.command("api-key-add")
@click.option("--type", type=click.Choice(["frappe-cloud", "site"]), required=True)
@click.option("--name", required=True, help="Team name or site URL")
@click.option("--key", prompt=True, hide_input=True)
@click.option("--secret", prompt=True, hide_input=True)
def api_key_add(type, name, key, secret):
    """Add an API key."""
    manager = APIKeyManager()
    
    if type == "frappe-cloud":
        manager.data["frappe_cloud"] = {
            "api_key": key,
            "api_secret": secret,
            "team_name": name,
            "added_at": "2024-01-15"
        }
    else:
        if "sites" not in manager.data:
            manager.data["sites"] = {}
        manager.data["sites"][name] = {
            "api_key": key,
            "api_secret": secret,
            "added_at": "2024-01-15"
        }
    
    manager.save()
    click.secho(f"✅ {type} key added for {name}", fg="green")
