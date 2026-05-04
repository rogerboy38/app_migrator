import click
import requests
import json
from .api_keys import load_keys, save_keys

class SiteAPIClient:
    """Client for individual site REST API (/api/method, /api/resource)"""
    
    def __init__(self, site_url, api_key, api_secret):
        # Ensure site_url doesn't have protocol
        if site_url.startswith("http"):
            self.site_url = site_url
        else:
            self.site_url = f"https://{site_url}"
        self.api_key = api_key
        self.api_secret = api_secret
        self.headers = self._create_headers()
    
    def _create_headers(self):
        """Create headers for site API (token authentication)."""
        return {
            "Authorization": f"token {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method, endpoint, params=None):
        """Make authenticated request to site API."""
        url = f"{self.site_url.rstrip('/')}/api/method/{endpoint}"
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                timeout=30
            )
            if response.status_code == 200:
                return response.json().get("message")
            else:
                click.echo(f"Error {response.status_code}: {response.text[:200]}")
                return None
        except Exception as e:
            click.echo(f"Request failed: {e}")
            return None
    
    def ping(self):
        """Test connection to site."""
        try:
            response = requests.get(
                f"{self.site_url.rstrip('/')}/api/method/frappe.ping",
                headers=self.headers,
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def get_installed_apps(self):
        """Get installed applications."""
        return self._make_request("GET", "frappe.apps.get_installed_apps")
    
    def get_app_versions(self):
        """Get version information for all apps."""
        return self._make_request("GET", "frappe.utils.versions.get_versions")
    
    def get_site_info(self):
        """Get site information."""
        return self._make_request("GET", "frappe.utils.get_site_info")
    
    def get_doc(self, doctype, name, fields=None):
        """Get a specific document."""
        endpoint = f"frappe.client.get"
        params = {"doctype": doctype, "name": name}
        if fields:
            params["fields"] = json.dumps(fields)
        return self._make_request("GET", endpoint, params)

@click.command("test-connection")
@click.option("--site", help="Site URL to test (uses configured site if not specified)")
def test_connection(site):
    """Test connection to a site's REST API."""
    data = load_keys()
    
    if not site:
        # Try to get first configured site
        sites = data.get("sites", {})
        if not sites:
            click.secho("No sites configured. Run 'setup-site-api' first.", fg="red")
            return
        site = next(iter(sites.keys()))
    
    site_data = data["sites"].get(site)
    if not site_data or not site_data.get("api_key") or not site_data.get("api_secret"):
        click.secho(f"No API credentials found for {site}", fg="red")
        return
    
    client = SiteAPIClient(
        site_url=site,
        api_key=site_data["api_key"],
        api_secret=site_data["api_secret"]
    )
    
    click.echo(f"Testing connection to {site}...")
    if client.ping():
        click.secho("✅ Connection successful!", fg="green")
        
        # Get some basic info
        site_info = client.get_site_info()
        if site_info:
            click.echo(f"\nSite Information:")
            click.echo(f"  Site Name: {site_info.get('site_name')}")
            click.echo(f"  Default Language: {site_info.get('default_language')}")
            click.echo(f"  Timezone: {site_info.get('time_zone')}")
    else:
        click.secho("❌ Connection failed", fg="red")

@click.command("get-installed-apps")
@click.option("--site", help="Site URL (uses configured site if not specified)")
@click.option("--format", type=click.Choice(["table", "json", "simple"]), default="table")
def get_installed_apps(site, format):
    """Get installed applications from a site."""
    data = load_keys()
    
    if not site:
        # Try to get first configured site
        sites = data.get("sites", {})
        if not sites:
            click.secho("No sites configured. Run 'setup-site-api' first.", fg="red")
            return
        site = next(iter(sites.keys()))
    
    site_data = data["sites"].get(site)
    if not site_data or not site_data.get("api_key") or not site_data.get("api_secret"):
        click.secho(f"No API credentials found for {site}", fg="red")
        return
    
    client = SiteAPIClient(
        site_url=site,
        api_key=site_data["api_key"],
        api_secret=site_data["api_secret"]
    )
    
    click.echo(f"Fetching installed apps from {site}...")
    apps = client.get_installed_apps()
    
    if not apps:
        # Try alternative method
        click.echo("Trying alternative method...")
        versions = client.get_app_versions()
        if versions:
            apps = list(versions.keys())
    
    if apps:
        if format == "json":
            click.echo(json.dumps(apps, indent=2))
        elif format == "simple":
            for app in apps:
                click.echo(app)
        else:  # table
            click.echo(f"\nInstalled Applications ({len(apps)}):")
            click.echo("-" * 40)
            for i, app in enumerate(sorted(apps), 1):
                click.echo(f"{i:3}. {app}")
    else:
        click.secho("No apps found or failed to fetch.", fg="yellow")
