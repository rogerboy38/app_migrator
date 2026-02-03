import click
import requests
import json
from .api_keys import load_keys, save_keys

class FrappeCloudAPIClient:
    """Client for Frappe Cloud Dashboard API (press.api.*)"""
    
    BASE_URL = "https://frappecloud.com/api/method"
    
    def __init__(self, api_key, api_secret, team_name=None, team_id=None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.team_name = team_name
        self.team_id = team_id
        self.headers = self._create_headers()
    
    def _create_headers(self):
        """Create headers for Frappe Cloud API."""
        headers = {
            "Authorization": f"Token {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json"
        }
        if self.team_name:
            headers["X-Press-Team"] = self.team_name
        if self.team_id:
            headers["X-Press-Team-ID"] = self.team_id
        return headers
    
    def _make_request(self, method, endpoint, data=None):
        """Make authenticated request to Frappe Cloud API."""
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get("message")
            else:
                click.echo(f"Error {response.status_code}: {response.text}")
                return None
        except Exception as e:
            click.echo(f"Request failed: {e}")
            return None
    
    def get_account_info(self):
        """Get account/team information."""
        return self._make_request("GET", "press.api.account.me")
    
    def list_sites(self):
        """List all sites in the team."""
        return self._make_request("GET", "press.api.site.all")
    
    def get_site_info(self, site_name):
        """Get detailed information about a site."""
        return self._make_request("POST", "press.api.site.get", {"name": site_name})
    
    def list_benches(self):
        """List all benches."""
        return self._make_request("GET", "press.api.bench.all")

@click.command("list-sites")
def list_sites():
    """List all sites from Frappe Cloud API."""
    data = load_keys()
    fc = data.get("frappe_cloud", {})
    
    if not fc.get("api_key") or not fc.get("api_secret"):
        click.secho("Frappe Cloud API not configured. Run 'setup-frappe-cloud' first.", fg="red")
        return
    
    client = FrappeCloudAPIClient(
        api_key=fc["api_key"],
        api_secret=fc["api_secret"],
        team_name=fc.get("team_name"),
        team_id=fc.get("team_id")
    )
    
    click.echo("Fetching sites from Frappe Cloud...")
    sites = client.list_sites()
    
    if sites:
        click.echo(f"\nFound {len(sites)} sites:")
        click.echo("-" * 80)
        for site in sites:
            click.echo(f"• {site.get('name')}")
            click.echo(f"  Status: {site.get('status')}")
            click.echo(f"  Version: {site.get('frappe_version', 'Unknown')}")
            click.echo(f"  Plan: {site.get('plan', {}).get('plan_title', 'Unknown')}")
            click.echo()
    else:
        click.secho("No sites found or error fetching sites.", fg="yellow")

@click.command("get-account-info")
def get_account_info():
    """Get account information from Frappe Cloud."""
    data = load_keys()
    fc = data.get("frappe_cloud", {})
    
    if not fc.get("api_key") or not fc.get("api_secret"):
        click.secho("Frappe Cloud API not configured. Run 'setup-frappe-cloud' first.", fg="red")
        return
    
    client = FrappeCloudAPIClient(
        api_key=fc["api_key"],
        api_secret=fc["api_secret"],
        team_name=fc.get("team_name"),
        team_id=fc.get("team_id")
    )
    
    click.echo("Fetching account information...")
    account = client.get_account_info()
    
    if account:
        click.echo("\nAccount Information:")
        click.echo("-" * 40)
        click.echo(f"Team: {account.get('team', {}).get('name')}")
        click.echo(f"Email: {account.get('user', {}).get('email')}")
        click.echo(f"First Name: {account.get('user', {}).get('first_name')}")
        click.echo(f"Last Name: {account.get('user', {}).get('last_name')}")
    else:
        click.secho("Failed to fetch account information.", fg="red")
