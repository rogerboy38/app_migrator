import click
import json
from tabulate import tabulate
from .api_keys import load_keys
from .cloud_api import FrappeCloudAPIClient
from .site_api import SiteAPIClient

@click.command("analyze-all")
@click.option("--output", type=click.Choice(["table", "json", "csv"]), default="table")
def analyze_all(output):
    """Complete analysis of all sites and their apps."""
    data = load_keys()
    
    # Check Frappe Cloud API
    fc_data = data.get("frappe_cloud", {})
    if not fc_data.get("api_key"):
        click.secho("Frappe Cloud API not configured. Run 'setup-frappe-cloud' first.", fg="red")
        return
    
    # Initialize Frappe Cloud client
    fc_client = FrappeCloudAPIClient(
        fc_data["api_key"],
        fc_data["api_secret"],
        fc_data.get("team_name")
    )
    
    click.echo("Fetching sites from Frappe Cloud...")
    sites = fc_client.list_sites()
    
    if not sites:
        click.secho("No sites found.", fg="yellow")
        return
    
    all_results = []
    
    for site in sites[:10]:  # Limit to first 10 sites for demo
        site_name = site.get("name")
        click.echo(f"\nAnalyzing: {site_name}")
        
        result = {
            "site_name": site_name,
            "frappe_version": site.get("frappe_version"),
            "status": site.get("status"),
            "plan": site.get("plan", {}).get("plan_title"),
            "apps": [],
            "site_api_configured": False,
            "site_api_accessible": False
        }
        
        # Check if we have site API credentials
        site_api_data = data.get("sites", {}).get(site_name)
        
        if site_api_data and site_api_data.get("api_key"):
            result["site_api_configured"] = True
            
            # Try to get apps
            try:
                site_client = SiteAPIClient(
                    site_name,
                    site_api_data["api_key"],
                    site_api_data["api_secret"]
                )
                
                if site_client.ping():
                    result["site_api_accessible"] = True
                    
                    # Get installed apps
                    apps = site_client.get_installed_apps()
                    if apps:
                        result["apps"] = sorted(apps)
                    else:
                        # Try alternative
                        versions = site_client.get_app_versions()
                        if versions:
                            result["apps"] = list(versions.keys())
            except Exception as e:
                result["error"] = str(e)
        
        all_results.append(result)
    
    # Output results
    if output == "json":
        click.echo(json.dumps(all_results, indent=2))
    elif output == "csv":
        # Simple CSV output
        click.echo("site_name,frappe_version,status,plan,apps_count,site_api_configured,site_api_accessible")
        for result in all_results:
            click.echo(f"{result['site_name']},{result['frappe_version']},{result['status']},{result['plan']},{len(result['apps'])},{result['site_api_configured']},{result['site_api_accessible']}")
    else:  # table
        table_data = []
        for result in all_results:
            table_data.append([
                result["site_name"],
                result["frappe_version"] or "N/A",
                result["status"],
                result["plan"] or "N/A",
                len(result["apps"]),
                "✅" if result["site_api_configured"] else "❌",
                "✅" if result["site_api_accessible"] else "❌"
            ])
        
        headers = ["Site", "Frappe Version", "Status", "Plan", "Apps", "API Config", "API Access"]
        click.echo("\n" + tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # Show detailed app info for first accessible site
        accessible_sites = [r for r in all_results if r["site_api_accessible"]]
        if accessible_sites:
            first_site = accessible_sites[0]
            click.echo(f"\n📦 Apps on {first_site['site_name']}:")
            for app in first_site["apps"]:
                click.echo(f"  • {app}")
