import click
import os
import json
from pathlib import Path

API_KEY_STORE = Path.home() / ".frappe_migrator_keys.json"

def load_keys():
    """Load stored API keys."""
    if API_KEY_STORE.exists():
        with open(API_KEY_STORE) as f:
            return json.load(f)
    return {
        "frappe_cloud_key": None,
        "frappe_cloud_secret": None,
        "site_api_key": None,
        "site_api_secret": None,
        "site_url": None
    }

def save_keys(data):
    """Save API keys to file."""
    with open(API_KEY_STORE, "w") as f:
        json.dump(data, f, indent=2)

def classify_key(key: str) -> str:
    """Classify API key based on format."""
    if not key:
        return "EMPTY"
    
    # Frappe Cloud API keys are usually 36+ chars
    if len(key) >= 36:
        return "FRAPPE_CLOUD"
    # Site API keys are usually 32 chars
    elif len(key) == 32:
        return "SITE_API"
    else:
        return "UNKNOWN"

@click.command("api-key-status")
def api_key_status():
    """Show stored API keys and their status."""
    data = load_keys()
    
    click.echo("\n" + "="*60)
    click.echo("API Key Status")
    click.echo("="*60)
    
    # Frappe Cloud Keys
    fc_key = data.get("frappe_cloud_key")
    if fc_key:
        masked = fc_key[:8] + "..." + fc_key[-4:] if len(fc_key) > 12 else fc_key
        click.echo(f"Frappe Cloud Key: {masked}")
        click.echo(f"  Type: {classify_key(fc_key)}")
    else:
        click.echo("Frappe Cloud Key: ❌ NOT SET")
    
    # Site API Keys
    site_key = data.get("site_api_key")
    if site_key:
        masked = site_key[:8] + "..." + site_key[-4:] if len(site_key) > 12 else site_key
        click.echo(f"\nSite API Key: {masked}")
        click.echo(f"  Type: {classify_key(site_key)}")
        click.echo(f"  Site URL: {data.get('site_url', 'Not set')}")
    else:
        click.echo("\nSite API Key: ❌ NOT SET")
    
    click.echo("\n" + "="*60)
