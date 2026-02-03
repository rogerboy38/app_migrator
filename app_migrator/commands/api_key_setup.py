"""
Command to setup Frappe Cloud API key
"""
import click
import os
from pathlib import Path

@click.command()
@click.option('--api-key', help='Frappe Cloud API key (if not provided, will prompt)')
@click.option('--test', is_flag=True, help='Test mode')
@click.pass_context
def api_key_setup(ctx, api_key, test):
    """Setup Frappe Cloud API key for App Migrator"""
    
    try:
        from app_migrator.utils.security import APIManager
    except ImportError:
        click.echo("❌ Error: Could not import security module")
        return
    
    click.echo("🔐 FRAPPE CLOUD API KEY SETUP")
    click.echo("=" * 50)
    
    if test:
        click.echo("🧪 TEST MODE")
        click.echo()
    
    # Show help information
    click.echo("To use App Migrator's full features, you need a Frappe Cloud API key.")
    click.echo()
    click.echo("HOW TO GET YOUR API KEY:")
    click.echo("1. Go to: https://cloud.frappe.io/dashboard/settings/developer")
    click.echo("2. Generate a new key")
    click.echo("3. Copy it (won't be shown again!)")
    click.echo()
    click.echo("The key will be encrypted and stored securely.")
    click.echo()
    
    # Get API key if not provided
    if not api_key:
        if test:
            api_key = "fc_test_key_12345"
            click.echo("🧪 TEST: Using test API key")
        else:
            api_key = click.prompt(
                "Enter your Frappe Cloud API key", 
                hide_input=True,
                confirmation_prompt=True
            )
    
    if not api_key:
        click.echo("❌ No API key provided. Setup cancelled.")
        return
    
    # Initialize API manager
    api_manager = APIManager()
    
    # Store the key
    if not test:
        success = api_manager.set_api_key(api_key, store=True)
        if success:
            click.echo("✅ API key stored securely")
        else:
            click.echo("❌ Failed to store API key")
            return
    else:
        click.echo("🧪 TEST: Would store API key")
        api_manager.set_api_key(api_key, store=False)
    
    # Validate the key
    click.echo("⏳ Validating API key...")
    validation = api_manager.validate_api_key(api_key, test_mode=test)
    
    if validation:
        click.echo(f"✅ Validated: {validation.get('email', 'Unknown user')}")
        click.echo(f"✅ Account: {validation.get('account', 'Unknown account')}")
        
        source = validation.get('source', 'unknown')
        if source == 'test_key':
            click.echo("   🔒 Validation: Test Key")
        elif source == 'frappe_cloud_api':
            click.echo("   🔒 Validation: Frappe Cloud API")
        elif source == 'plausibility_check':
            click.echo("   ⚠️  Validation: Limited (key looks plausible)")
        else:
            click.echo(f"   ℹ️  Validation: {source}")
        
        # Show permissions
        from app_migrator.utils.security import SecurityManager
        role = validation.get('role', 'guest')
        permissions = SecurityManager.get_permissions(role)
        
        click.echo()
        click.echo("🎯 ACCESS GRANTED:")
        click.echo(f"   Level: {role.upper()} access")
        click.echo(f"   Description: {permissions.get('description', '')}")
        
        if role == 'full':
            click.echo("   ✅ All migration features enabled")
        elif role == 'limited':
            click.echo("   ⚠️  Limited features (cannot push to GitHub)")
        else:
            click.echo("   ❌ Basic features only")
            
    else:
        click.echo("❌ API key validation failed")
        click.echo("   You can still use basic features in guest mode")
    
    click.echo()
    click.echo("✅ API key setup completed!")
    click.echo()
    click.echo("To check status anytime: bench app-migrator api-key-status")
    click.echo("To remove key: bench app-migrator api-key-remove")

@click.command()
@click.pass_context
def api_key_status(ctx):
    """Check Frappe Cloud API key status"""
    try:
        from app_migrator.utils.security import APIManager, SecurityManager
    except ImportError:
        click.echo("❌ Error: Could not import security module")
        return
    
    api_manager = APIManager()
    status = api_manager.get_status()
    
    click.echo("🔐 FRAPPE CLOUD API KEY STATUS")
    click.echo("=" * 50)
    
    click.echo(f"Status: {status.get('status', 'unknown').upper()}")
    
    if status.get('user'):
        click.echo(f"User: {status['user']}")
    
    if status.get('storage'):
        click.echo(f"Storage: {status['storage']}")
    
    if status.get('role'):
        permissions = SecurityManager.get_permissions(status['role'])
        click.echo(f"Access Level: {status['role'].upper()}")
        click.echo(f"Permissions: {permissions.get('description', '')}")
    
    # Check validation
    api_key = api_manager.get_api_key()
    if api_key:
        click.echo()
        click.echo("⏳ Re-validating key...")
        validation = api_manager.validate_api_key(api_key)
        if validation:
            click.echo(f"✅ Key is valid: {validation.get('source', 'unknown')}")
        else:
            click.echo("❌ Key validation failed")
    
    click.echo()
    click.echo("💡 Commands:")
    click.echo("   bench app-migrator api-key-setup  - Setup new key")
    click.echo("   bench app-migrator api-key-remove - Remove stored key")

@click.command()
@click.option('--confirm', is_flag=True, help='Skip confirmation')
@click.pass_context  
def api_key_remove(ctx, confirm):
    """Remove stored Frappe Cloud API key"""
    import keyring
    import shutil
    import os
    
    if not confirm:
        if not click.confirm("Are you sure you want to remove the stored API key?"):
            click.echo("Cancelled")
            return
    
    # Remove from keyring
    try:
        keyring.delete_password("frappe_cloud", "api_key")
        click.echo("✅ Removed from keyring")
    except:
        click.echo("ℹ️  No key in keyring")
    
    # Remove fallback file
    fallback_dir = os.path.expanduser("~/.frappe_migrator")
    if os.path.exists(fallback_dir):
        shutil.rmtree(fallback_dir)
        click.echo("✅ Removed fallback storage")
    
    click.echo("✅ API key removed")
    click.echo("You will have guest access until you setup a new key.")
