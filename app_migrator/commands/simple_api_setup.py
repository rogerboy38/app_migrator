"""
Simple API key setup - no keyring issues
"""
import click
import os

@click.command()
@click.option('--api-key', help='Frappe Cloud API key')
@click.option('--test', is_flag=True, help='Test mode')
@click.pass_context
def simple_api_setup(ctx, api_key, test):
    """Simple API key setup (no keyring)"""
    
    click.echo("🔐 SIMPLE API KEY SETUP")
    click.echo("=" * 50)
    
    if test:
        click.echo("🧪 TEST MODE")
        click.echo()
    
    # Get API key
    if not api_key:
        if test:
            api_key = "fc_test_key_12345"
            click.echo("🧪 TEST: Using test API key")
        else:
            api_key = click.prompt(
                "Enter Frappe Cloud API key (or 'skip' for guest mode)",
                default="skip"
            )
            
            if api_key.lower() == "skip":
                click.echo("✅ Skipped API key setup (guest mode)")
                return
    
    # Store in environment variable
    os.environ["FRAPPE_CLOUD_API_KEY"] = api_key
    click.echo("✅ API key set as environment variable")
    click.echo(f"   Key: {api_key[:10]}...{api_key[-5:] if len(api_key) > 15 else ''}")
    
    # Test validation
    from app_migrator.utils.security import APIManager
    api_manager = APIManager()
    
    click.echo("⏳ Validating key...")
    result = api_manager.validate_api_key(api_key, test_mode=test)
    
    if result:
        click.echo(f"✅ Validated: {result.get('email')}")
        click.echo(f"✅ Access: {result.get('role', 'guest').upper()}")
    else:
        click.echo("❌ Validation failed (will use guest mode)")
    
    click.echo()
    click.echo("💡 Note: Key is stored in environment only")
    click.echo("   It will be lost when terminal closes")
    click.echo("   For permanent storage, use the full api-key-setup command")

@click.command()
@click.pass_context
def quick_setup(ctx):
    """Quick setup with fc_ key for development"""
    
    click.echo("⚡ QUICK DEVELOPMENT SETUP")
    click.echo("=" * 50)
    
    # Generate a fc_ key
    import hashlib
    import time
    
    timestamp = str(int(time.time()))
    key_hash = hashlib.md5(timestamp.encode()).hexdigest()[:10]
    dev_key = f"fc_dev_key_{key_hash}_migration"
    
    click.echo(f"🔑 Generated development key:")
    click.echo(f"   {dev_key}")
    click.echo()
    
    # Set as environment variable
    os.environ["FRAPPE_CLOUD_API_KEY"] = dev_key
    click.echo("✅ Development key set")
    click.echo("✅ FULL access enabled")
    click.echo()
    click.echo("🚀 Ready for development!")
    click.echo()
    click.echo("Run: bench app-migrator setup-wizard")
