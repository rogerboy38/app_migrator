import click
import os
import sys
from pathlib import Path
import subprocess
import json
import requests
from ..base_command import BaseCommand

@click.command()
@click.option('--api-key', help='Frappe Cloud API key')
@click.option('--ssh-key', help='Path to SSH key (default: ~/.ssh/id_ed25519)')
@click.option('--auto-approve', is_flag=True, help='Skip confirmation prompts')
@click.option('--sync', is_flag=True, help='Sync from source bench')
@click.pass_context
def setup_wizard(ctx, api_key, ssh_key, auto_approve, sync):
    """Interactive setup wizard for App Migrator"""
    
    from app_migrator.utils.security import APIManager
    from app_migrator.utils.ssh_manager import SSHManager
    
    click.clear()
    
    # Banner
    click.echo("=" * 60)
    click.echo("🚀 APP MIGRATOR ENTERPRISE - SETUP WIZARD")
    click.echo("=" * 60)
    click.echo()
    
    # Check if this is target bench syncing from source
    bench_name = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    if sync:
        click.echo(f"📡 SYNC MODE: Syncing configuration to this bench ({bench_name})")
        return sync_from_source(ctx)
    
    click.echo(f"📍 CURRENT BENCH: {bench_name}")
    click.echo(f"📁 Bench path: {os.getcwd()}")
    click.echo()
    
    # Step 1: API Key Setup
    click.echo("🔐 STEP 1: FRAPPE CLOUD IDENTITY VERIFICATION")
    click.echo("-" * 50)
    
    api_manager = APIManager()
    if api_key:
        click.echo("✓ Using provided API key")
        api_manager.set_api_key(api_key, store=True)
    else:
        api_key = api_manager.get_api_key()
    
    if not api_key:
        api_key = prompt_api_key()
    
    # Validate API key
    user_info = api_manager.validate_api_key(api_key)
    
    if user_info:
        click.echo(f"✅ Verified: {user_info.get('email', 'Unknown')}")
        click.echo(f"✅ Account: {user_info.get('account', 'Unknown')}")
    else:
        click.echo("⚠️  API key validation failed")
        if click.confirm("Continue as Guest? (limited functionality)"):
            user_info = {"role": "guest"}
        else:
            click.echo("❌ Setup cancelled")
            return
    
    # Step 2: SSH Key Setup
    click.echo()
    click.echo("🔑 STEP 2: SSH KEY SETUP FOR GITHUB")
    click.echo("-" * 50)
    
    ssh_manager = SSHManager()
    ssh_status = ssh_manager.check_ssh_status()
    
    if ssh_status["has_ssh_keys"]:
        click.echo("✓ SSH keys detected")
        if ssh_status["github_connected"]:
            click.echo("✅ Connected to GitHub")
        else:
            click.echo("⚠️  SSH keys exist but GitHub connection failed")
    else:
        click.echo("❌ No SSH keys detected")
    
    if not ssh_status["github_connected"]:
        setup_ssh_wizard(ssh_manager, auto_approve)
    
    # Step 3: Repository Analysis
    click.echo()
    click.echo("📊 STEP 3: REPOSITORY DISCOVERY")
    click.echo("-" * 50)
    
    analyze_repositories(ctx)
    
    # Step 4: Change Management
    click.echo()
    click.echo("📝 STEP 4: PENDING CHANGES MANAGEMENT")
    click.echo("-" * 50)
    
    manage_pending_changes(ctx)
    
    # Step 5: Summary
    click.echo()
    click.echo("🎯 STEP 5: SETUP COMPLETE")
    click.echo("-" * 50)
    
    show_summary(api_manager, ssh_manager, bench_name)
    
    click.echo()
    click.echo("✅ Setup wizard completed successfully!")
    click.echo()
    click.echo("Next steps:")
    click.echo("1. Switch to target bench: cd ~/frappe-bench-0003")
    click.echo("2. Run: bench app-migrator setup-wizard --sync")
    click.echo("3. Then: bench app-migrator migrate --plan")

def prompt_api_key():
    """Interactive API key prompt"""
    click.echo()
    click.echo("To ensure secure migration, we need to verify your Frappe Cloud identity.")
    click.echo()
    click.echo("1. 🔑 Get your API key:")
    click.echo("   • Open: https://frappecloud.com/dashboard/api-keys")
    click.echo("   • Generate new key or use existing")
    click.echo()
    click.echo("2. 📋 Enter your API key:")
    click.echo("   (It will be encrypted and stored securely)")
    click.echo()
    
    api_key = click.prompt("Frappe Cloud API key", hide_input=True)
    
    click.echo()
    click.echo("⏳ Validating API key...")
    return api_key

def setup_ssh_wizard(ssh_manager, auto_approve):
    """Interactive SSH setup"""
    click.echo()
    click.echo("Choose SSH setup option:")
    click.echo("1. 🆕 Create new SSH key pair (recommended)")
    click.echo("2. 🔑 Use existing SSH key")
    click.echo("3. 📋 Use API key for GitHub access")
    click.echo("4. ⏭️  Skip for now")
    click.echo()
    
    if auto_approve:
        choice = "1"
    else:
        choice = click.prompt("Enter choice (1-4)", default="1")
    
    if choice == "1":
        # Create new SSH key
        key_path = ssh_manager.create_ssh_key()
        click.echo(f"✅ Created new SSH key: {key_path}")
        
        # Show public key
        pub_key = ssh_manager.get_public_key(key_path)
        click.echo()
        click.echo("📋 Add this key to GitHub:")
        click.echo("-" * 40)
        click.echo(pub_key)
        click.echo("-" * 40)
        click.echo()
        click.echo("Instructions:")
        click.echo("1. Go to https://github.com/settings/keys")
        click.echo("2. Click 'New SSH key'")
        click.echo("3. Paste the key above")
        click.echo("4. Title: frappe-cloud-migration")
        click.echo()
        
        if not auto_approve:
            click.confirm("Have you added the key to GitHub?", default=True, abort=True)
        
        # Test connection
        click.echo("⏳ Testing GitHub connection...")
        if ssh_manager.test_github_connection():
            click.echo("✅ Successfully connected to GitHub!")
        else:
            click.echo("⚠️  Connection test failed. Please check key installation.")
    
    elif choice == "2":
        # Use existing key
        default_path = os.path.expanduser("~/.ssh/id_ed25519")
        key_path = click.prompt("Path to SSH key", default=default_path)
        ssh_manager.test_github_connection(key_path)
    
    elif choice == "3":
        click.echo("ℹ️  Using API key mode (GitHub token coming soon)")
        # TODO: Implement GitHub token storage
    
    else:
        click.echo("⚠️  SSH setup skipped. Some features will be limited.")

def analyze_repositories(ctx):
    """Analyze git repositories in current bench"""
    from app_migrator.commands.git_info import get_git_info
    
    click.echo("⏳ Scanning apps in current bench...")
    
    # Use existing git-info functionality
    apps_info = get_git_info()
    
    git_repos = sum(1 for app in apps_info if app.get("is_git"))
    custom_apps = sum(1 for app in apps_info if "custom" in app.get("app_type", ""))
    no_remote = sum(1 for app in apps_info if app.get("is_git") and not app.get("remote"))
    
    click.echo(f"✅ Found: {len(apps_info)} apps total")
    click.echo(f"✅ Git repositories: {git_repos}")
    click.echo(f"✅ Custom apps: {custom_apps}")
    click.echo(f"⚠️  Apps without remote: {no_remote}")
    
    if no_remote > 0:
        click.echo()
        click.echo("💡 Recommendation: Setup Git remotes for local apps")
        click.echo("   Use: bench app-migrator git-setup-remotes")

def manage_pending_changes(ctx):
    """Check for uncommitted changes"""
    import subprocess
    
    click.echo("⏳ Checking for uncommitted changes...")
    
    # Get current directory (app_migrator)
    app_dir = os.path.dirname(os.path.dirname(__file__))
    
    # Check git status
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=app_dir,
        capture_output=True,
        text=True
    )
    
    changes = [line for line in result.stdout.strip().split('\n') if line]
    
    if changes:
        click.echo(f"⚠️  Found {len(changes)} uncommitted change(s) in app_migrator")
        click.echo()
        
        # Show changes
        for change in changes[:5]:  # Show first 5
            status, filename = change[:2], change[3:]
            icon = "🆕" if status == "??" else "📝"
            click.echo(f"   {icon} {filename}")
        
        if len(changes) > 5:
            click.echo(f"   ... and {len(changes) - 5} more")
        
        click.echo()
        click.echo("Options:")
        click.echo("1. ✅ Commit changes now")
        click.echo("2. 📦 Stash changes for later")
        click.echo("3. 🔄 Review changes first")
        click.echo("4. ⏭️  Skip (not recommended)")
        
        choice = click.prompt("Enter choice (1-4)", default="1")
        
        if choice == "1":
            commit_message = click.prompt("Commit message", 
                                         default=f"Migration prep: {subprocess.getoutput('date')}")
            subprocess.run(["git", "add", "."], cwd=app_dir)
            subprocess.run(["git", "commit", "-m", commit_message], cwd=app_dir)
            click.echo("✅ Changes committed")
        
        elif choice == "2":
            subprocess.run(["git", "stash", "save", f"Migration changes {subprocess.getoutput('date')}"], 
                          cwd=app_dir)
            click.echo("✅ Changes stashed")
        
        elif choice == "3":
            subprocess.run(["git", "diff"], cwd=app_dir)
            if click.confirm("Commit these changes now?"):
                subprocess.run(["git", "add", "."], cwd=app_dir)
                subprocess.run(["git", "commit", "-m", "Migration changes"], cwd=app_dir)
    else:
        click.echo("✅ No uncommitted changes found")

def show_summary(api_manager, ssh_manager, bench_name):
    """Show setup summary"""
    click.echo("📋 SETUP SUMMARY")
    click.echo("-" * 30)
    
    # API Status
    api_status = api_manager.get_status()
    click.echo(f"🔐 API Key: {api_status.get('status', 'Not set')}")
    if api_status.get('user'):
        click.echo(f"   User: {api_status['user']}")
    
    # SSH Status
    ssh_status = ssh_manager.check_ssh_status()
    click.echo(f"🔑 SSH Keys: {'✅' if ssh_status['has_ssh_keys'] else '❌'}")
    if ssh_status['github_connected']:
        click.echo(f"   GitHub: ✅ Connected")
    
    # Bench info
    click.echo(f"📍 Bench: {bench_name}")
    
    # Next steps
    click.echo()
    click.echo("🚀 READY FOR MIGRATION")

def sync_from_source(ctx):
    """Sync configuration from source bench"""
    click.echo("⏳ Looking for source bench configuration...")
    
    # Look for common bench patterns
    possible_benches = [
        os.path.expanduser("~/frappe-bench"),
        os.path.expanduser("~/frappe-bench-0025"),
        os.path.expanduser("~/bench-0025"),
    ]
    
    source_bench = None
    for bench in possible_benches:
        if os.path.exists(bench):
            source_bench = bench
            break
    
    if not source_bench:
        click.echo("❌ Could not find source bench")
        click.echo("Please run setup on source bench first:")
        click.echo("bench app-migrator setup-wizard")
        return
    
    click.echo(f"✅ Found source bench: {source_bench}")
    
    # TODO: Implement actual sync logic
    click.echo("📡 Syncing configuration...")
    click.echo("(Sync implementation coming in next phase)")
    
    return True
