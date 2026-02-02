import click
import json
from tabulate import tabulate
from .api_keys import load_keys
from .cloud_api import FrappeCloudAPI, SiteAPI

@click.command("test-connection")
def test_connection():
    """Test connections to both Frappe Cloud and Site APIs."""
    data = load_keys()
    
    click.echo("\n" + "="*60)
    click.echo("Connection Test")
    click.echo("="*60)
    
    # Test Frappe Cloud
    if data.get("frappe_cloud_key") and data.get("frappe_cloud_secret"):
        click.echo("\n1. Testing Frappe Cloud API...")
        api = FrappeCloudAPI(data["frappe_cloud_key"], data["frappe_cloud_secret"])
        sites = api.get_sites()
        
        if sites:
            click.secho(f"   ✅ Connected! Found {len(sites)} sites", fg="green")
        else:
            click.secho("   ❌ Connection failed", fg="red")
    else:
        click.echo("\n1. Frappe Cloud API: ❌ Not configured")
    
    # Test Site
    if all([data.get("site_url"), data.get("site_api_key"), data.get("site_api_secret")]):
        click.echo("\n2. Testing Site API...")
        site_api = SiteAPI(data["site_url"], data["site_api_key"], data["site_api_secret"])
        
        if site_api.ping():
            click.secho(f"   ✅ Connected to {data['site_url']}", fg="green")
        else:
            click.secho(f"   ❌ Failed to connect to {data['site_url']}", fg="red")
    else:
        click.echo("\n2. Site API: ❌ Not configured")
    
    click.echo("\n" + "="*60)

@click.command("get-site-info")
@click.option("--site-name", help="Specific site name (defaults to configured site)")
def get_site_info(site_name):
    """Get detailed information about a site."""
    data = load_keys()
    
    if not data.get("frappe_cloud_key") or not data.get("frappe_cloud_secret"):
        click.secho("Frappe Cloud API not configured. Run 'setup-wizard' first.", fg="red")
        return
    
    api = FrappeCloudAPI(data["frappe_cloud_key"], data["frappe_cloud_secret"])
    
    if not site_name:
        site_name = data.get("site_url")
        if not site_name:
            click.secho("No site specified. Use --site-name or configure site URL.", fg="red")
            return
    
    click.echo(f"\nFetching info for site: {site_name}")
    site_info = api.get_site_info(site_name)
    
    if site_info:
        click.echo("\nSite Information:")
        click.echo("-" * 40)
        
        info_table = []
        for key, value in site_info.items():
            if key not in ["_id", "_rev"]:  # Skip internal fields
                info_table.append([key, str(value)])
        
        click.echo(tabulate(info_table, headers=["Property", "Value"], tablefmt="grid"))
    else:
        click.secho("Failed to fetch site information.", fg="red")

@click.command("analyze-apps")
@click.option("--site-url", help="Site URL to analyze (overrides configured site)")
@click.option("--output-format", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format")
@click.option("--detailed", is_flag=True, help="Show detailed version information")
def analyze_apps(site_url, output_format, detailed):
    """Analyze installed applications and their versions."""
    data = load_keys()
    
    # Determine which site to analyze
    target_site = site_url or data.get("site_url")
    if not target_site:
        click.secho("No site specified. Use --site-url or configure site URL.", fg="red")
        return
    
    # Check if we have site API credentials
    site_key = data.get("site_api_key")
    site_secret = data.get("site_api_secret")
    
    if not site_key or not site_secret:
        click.secho(f"Site API credentials not configured for {target_site}", fg="red")
        if click.confirm("Do you want to enter credentials now?"):
            site_key = click.prompt("Site API Key", hide_input=True)
            site_secret = click.prompt("Site API Secret", hide_input=True)
            data["site_api_key"] = site_key
            data["site_api_secret"] = site_secret
            from api_keys import save_keys
            save_keys(data)
        else:
            return
    
    click.echo(f"\nAnalyzing apps on: {target_site}")
    click.echo("-" * 60)
    
    # Get app information
    site_api = SiteAPI(target_site, site_key, site_secret)
    
    # Get installed apps
    installed_apps = site_api.get_installed_apps()
    app_versions = site_api.get_app_versions()
    
    if not installed_apps and not app_versions:
        click.secho("No app information found.", fg="yellow")
        return
    
    # Prepare data
    apps_data = []
    
    if installed_apps and "data" in installed_apps:
        for app in installed_apps["data"]:
            app_name = app.get("app_name")
            app_version = app.get("app_version", "Unknown")
            apps_data.append({
                "app": app_name,
                "version": app_version,
                "source": "Installed Applications"
            })
    
    # Add version info
    for app_name, version_info in app_versions.items():
        if isinstance(version_info, dict) and "version" in version_info:
            # Check if app already in list
            existing = next((a for a in apps_data if a["app"] == app_name), None)
            if existing:
                existing["detailed_version"] = version_info["version"]
            else:
                apps_data.append({
                    "app": app_name,
                    "version": version_info["version"],
                    "source": "Version API"
                })
    
    # Output results
    if output_format == "json":
        click.echo(json.dumps(apps_data, indent=2))
    elif output_format == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["app", "version", "source", "detailed_version"])
        writer.writeheader()
        for app in apps_data:
            writer.writerow(app)
        click.echo(output.getvalue())
    else:  # table format
        table_data = []
        for app in apps_data:
            table_data.append([
                app["app"],
                app["version"],
                app.get("detailed_version", ""),
                app["source"]
            ])
        
        headers = ["Application", "Version", "Detailed Version", "Source"]
        click.echo(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    click.echo(f"\nTotal apps found: {len(apps_data)}")
