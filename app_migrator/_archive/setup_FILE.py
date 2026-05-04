import click
import json
from .api_keys import load_keys, save_keys
from .cloud_api import FrappeCloudAPIClient

@click.command("setup-frappe-cloud")
def setup_frappe_cloud():
    """Setup Frappe Cloud Dashboard API credentials."""
    data = load_keys()
    
    click.echo("\n" + "="*60)
    click.echo("Frappe Cloud Dashboard API Setup")
    click.echo("="*60)
    
    click.echo("\nYou need to create an API key from:")
    click.echo("Frappe Cloud Dashboard → Settings → Profile & Team → API Access")
    click.echo("\nThis gives access to press.api.* endpoints.")
    
    api_key = click.prompt("\nEnter Frappe Cloud API Key", hide_input=True)
    api_secret = click.prompt("Enter Frappe Cloud API Secret", hide_input=True)
    team_name = click.prompt("Enter Team Name (optional, from Frappe Cloud)", default="", show_default=False)
    
    # Test the credentials
    click.echo("\nTesting credentials...")
    client = FrappeCloudAPIClient(api_key, api_secret, team_name)
    account_info = client.get_account_info()
    
    if account_info:
        team_info = account_info.get("team", {})
        actual_team_name = team_info.get("name")
        team_id = team_info.get("team_id")
        
        click.secho("✅ Credentials validated!", fg="green")
        click.echo(f"Team: {actual_team_name}")
        click.echo(f"Team ID: {team_id}")
        
        # Update with actual team info if different
        if actual_team_name and (not team_name or team_name != actual_team_name):
            click.echo(f"Using team name from API: {actual_team_name}")
            team_name = actual_team_name
        
        # Save credentials
        data["frappe_cloud"] = {
            "api_key": api_key,
            "api_secret": api_secret,
            "team_name": team_name,
            "team_id": team_id
        }
        save_keys(data)
        
        click.secho("\n✅ Frappe Cloud API configured successfully!", fg="green")
    else:
        click.secho("❌ Failed to validate credentials. Please check your key/secret.", fg="red")

@click.command("setup-site-api")
@click.option("--site-url", prompt="Site URL (e.g., sysmayal.frappe.cloud)", help="The site to configure")
def setup_site_api(site_url):
    """Setup site-specific REST API credentials."""
    data = load_keys()
    
    click.echo("\n" + "="*60)
    click.echo(f"Site API Setup for: {site_url}")
    click.echo("="*60)
    
    click.echo("\nYou need to generate API keys from WITHIN the site:")
    click.echo(f"1. Login to {site_url}")
    click.echo("2. Go to Users → Select your user")
    click.echo("3. In API Access section, click 'Generate Keys'")
    click.echo("4. Copy the API Key and Secret")
    
    api_key = click.prompt("\nEnter Site API Key", hide_input=True)
    api_secret = click.prompt("Enter Site API Secret", hide_input=True)
    
    # Test the credentials
    from .site_api import SiteAPIClient
    
    click.echo(f"\nTesting connection to {site_url}...")
    client = SiteAPIClient(site_url, api_key, api_secret)
    
    if client.ping():
        click.secho("✅ Connection successful!", fg="green")
        
        # Get site info
        site_info = client.get_site_info()
        if site_info:
            click.echo(f"Site Name: {site_info.get('site_name')}")
        
        # Save credentials
        if "sites" not in data:
            data["sites"] = {}
        
        data["sites"][site_url] = {
            "api_key": api_key,
            "api_secret": api_secret,
            "configured_at": "2024-01-15"  # You might want to use actual date
        }
        save_keys(data)
        
        click.secho(f"\n✅ Site API for {site_url} configured successfully!", fg="green")
    else:
        click.secho("❌ Connection failed. Please check:", fg="red")
        click.echo("1. API key/secret is correct")
        click.echo("2. User has API access enabled")
        click.echo("3. Site is accessible")

@click.command("setup-wizard")
def setup_wizard():
    """Interactive wizard to setup both APIs."""
    click.echo("\n" + "="*60)
    click.echo("Frappe Cloud App Migrator Setup Wizard")
    click.echo("="*60)
    
    data = load_keys()
    
    # Step 1: Frappe Cloud API
    if data.get("frappe_cloud", {}).get("api_key"):
        click.echo("\nFrappe Cloud API is already configured.")
        if not click.confirm("Do you want to reconfigure it?"):
            click.echo("Using existing Frappe Cloud credentials.")
        else:
            ctx = click.get_current_context()
            ctx.invoke(setup_frappe_cloud)
    else:
        click.echo("\nStep 1: Frappe Cloud Dashboard API")
        click.echo("-" * 40)
        ctx = click.get_current_context()
        ctx.invoke(setup_frappe_cloud)
    
    # Step 2: Site API
    click.echo("\nStep 2: Site REST API")
    click.echo("-" * 40)
    
    # List sites from Frappe Cloud if available
    fc_data = data.get("frappe_cloud", {})
    if fc_data.get("api_key"):
        from .cloud_api import FrappeCloudAPIClient
        client = FrappeCloudAPIClient(
            fc_data["api_key"],
            fc_data["api_secret"],
            fc_data.get("team_name")
        )
        sites = client.list_sites()
        
        if sites:
            click.echo("\nYour sites from Frappe Cloud:")
            site_names = [site["name"] for site in sites[:10]]
            for i, name in enumerate(site_names, 1):
                click.echo(f"  {i}. {name}")
            
            if click.confirm("\nDo you want to configure API access for any of these sites?"):
                site_choice = click.prompt("Enter site number or full URL", type=str)
                
                # Try to parse as number
                try:
                    idx = int(site_choice) - 1
                    if 0 <= idx < len(site_names):
                        site_url = site_names[idx]
                    else:
                        site_url = site_choice
                except:
                    site_url = site_choice
                
                ctx.invoke(setup_site_api, site_url=site_url)
    
    click.secho("\n✅ Setup complete! Use 'bench app-migrator api-key-status' to view your configuration.", fg="green")
