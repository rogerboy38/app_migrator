import click
import os
import json
from pathlib import Path
import hashlib

API_KEY_STORE = Path.home() / ".frappe_migrator_keys.json"

def load_keys():
    """Load stored API keys."""
    if API_KEY_STORE.exists():
        with open(API_KEY_STORE) as f:
            return json.load(f)
    return {
        "frappe_cloud": {
            "api_key": None,
            "api_secret": None,
            "team_name": None,
            "team_id": None
        },
        "sites": {}
    }

def save_keys(data):
    """Save API keys to file."""
    with open(API_KEY_STORE, "w") as f:
        json.dump(data, f, indent=2)

def mask_key(key):
    """Mask key for display."""
    if not key:
        return "None"
    if len(key) <= 8:
        return key
    return f"{key[:4]}...{key[-4:]}"

@click.command("api-key-status")
def api_key_status():
    """Show stored API keys and their status."""
    data = load_keys()
    
    click.echo("\n" + "="*60)
    click.echo("API Key Status")
    click.echo("="*60)
    
    # Frappe Cloud API
    fc = data.get("frappe_cloud", {})
    click.echo("\n📊 Frappe Cloud Dashboard API:")
    if fc.get("api_key"):
        click.echo(f"  Key: {mask_key(fc['api_key'])}")
        click.echo(f"  Team: {fc.get('team_name', 'Not set')}")
        click.echo(f"  Team ID: {fc.get('team_id', 'Not set')}")
    else:
        click.echo("  ❌ Not configured")
    
    # Site APIs
    sites = data.get("sites", {})
    click.echo(f"\n🌐 Configured Sites ({len(sites)}):")
    if sites:
        for site_name, site_data in sites.items():
            click.echo(f"  - {site_name}")
            if site_data.get("api_key"):
                click.echo(f"    Key: {mask_key(site_data['api_key'])}")
            else:
                click.echo("    ❌ No API key")
    else:
        click.echo("  No sites configured")
    
    click.echo("\n" + "="*60)
