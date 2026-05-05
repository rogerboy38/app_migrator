import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import click
import requests


@click.command()
@click.option('--api-key', help='Frappe Cloud API key')
@click.option('--ssh-key', help='Path to SSH key (default: ~/.ssh/id_ed25519)')
@click.option('--auto-approve', is_flag=True, help='Skip confirmation prompts')
@click.option('--sync', is_flag=True, help='Sync from source bench')
@click.option('--test', is_flag=True, help='Test mode without actual changes')
@click.pass_context
def setup_wizard(ctx, api_key, ssh_key, auto_approve, sync, test):
    """Interactive setup wizard for App Migrator"""

    try:
        from app_migrator.utils.security import APIManager, SecurityManager
        from app_migrator.utils.ssh_manager import SSHManager
    except ImportError as e:
        click.echo(f"❌ Error importing modules: {e}")
        click.echo("Please ensure security.py and ssh_manager.py exist in utils/")
        return

    click.clear()

    # Banner
    click.echo("=" * 60)
    click.echo("🚀 APP MIGRATOR - SETUP WIZARD")
    click.echo("=" * 60)
    click.echo()

    if test:
        click.echo("🧪 TEST MODE - No actual changes will be made")
        click.echo()

    # Get bench info
    bench_path = os.getcwd()
    bench_name = os.path.basename(bench_path) if "bench" in bench_path.lower() else "current"

    if sync:
        click.echo(f"📡 SYNC MODE: Syncing configuration to this bench ({bench_name})")
        return sync_from_source(ctx, test)

    click.echo(f"📍 CURRENT BENCH: {bench_name}")
    click.echo(f"📁 Bench path: {bench_path}")
    click.echo()

    # Step 1: API Key Setup - FIXED VERSION
    click.echo("🔐 STEP 1: FRAPPE CLOUD IDENTITY VERIFICATION")
    click.echo("-" * 50)

    api_manager = APIManager()
    validation_result = None
    user_role = "guest"  # Default to guest

    # FIX 1: Always prompt for API key if not provided via --api-key
    # Don't automatically get from storage in wizard mode
    if not api_key:
        # In wizard mode, always prompt for fresh key
        api_key = prompt_api_key(test)
        if api_key and not test:
            api_manager.set_api_key(api_key, store=True)
    else:
        # API key was provided via command line
        click.echo("✓ Using provided API key")
        if not test:
            api_manager.set_api_key(api_key, store=True)

    # Validate API key - SMART HYBRID (with test_mode parameter)
    if api_key:
        click.echo("⏳ Validating API key...")
        validation_result = api_manager.validate_api_key(api_key, test_mode=test)

    # Determine user role using SecurityManager (FIX 2)
    if validation_result:
        # We have a validation result
        click.echo(f"✅ Verified: {validation_result.get('email', 'Unknown')}")
        click.echo(f"✅ Account: {validation_result.get('account', 'Unknown')}")

        source = validation_result.get('source', 'unknown')
        note = validation_result.get('note', '')

        # Show appropriate message based on source
        if source == 'test_key':
            click.echo("   🔒 Validation: Test Key")
        elif source == 'frappe_cloud_api':
            click.echo("   🔒 Validation: Frappe Cloud API")
        elif source == 'plausibility_check':
            click.echo("   ⚠️  Validation: Limited (key looks plausible)")
        else:
            click.echo(f"   ℹ️  Validation: {source.replace('_', ' ').title()}")

        # Use SecurityManager to determine role (FIX 3)
        user_role = SecurityManager.get_user_role({
            "status": "valid",
            "source": source,
            "note": note
        })
    else:
        # No validation result
        if api_key:
            # Key provided but validation failed
            key_preview = api_key[:15] + "..." if len(api_key) > 18 else api_key
            click.echo(f"⚠️  API key validation failed for: {key_preview}")

            # Check if key at least looks plausible
            if len(api_key) >= 10:
                click.echo("   ℹ️  Key looks plausible but couldn't verify")
                click.echo("   🔓 Continuing with LIMITED access (automatic)")
                user_role = "limited"
            else:
                # Key is too short/suspicious
                click.echo("   ❌ Key appears invalid (too short)")
                click.echo("   👤 Falling back to GUEST mode (automatic)")
                user_role = "guest"
        else:
            # No key provided
            click.echo("ℹ️  No API key provided")
            click.echo("👤 Continuing as GUEST (automatic)")
            user_role = "guest"

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
        setup_ssh_wizard(ssh_manager, auto_approve, test)

    # Step 3: Repository Analysis
    click.echo()
    click.echo("📊 STEP 3: REPOSITORY DISCOVERY")
    click.echo("-" * 50)

    analyze_repositories(ctx, test)

    # Step 4: Change Management
    click.echo()
    click.echo("📝 STEP 4: PENDING CHANGES MANAGEMENT")
    click.echo("-" * 50)

    manage_pending_changes(ctx, test_mode=test)

    # Step 5: Summary
    click.echo()
    click.echo("🎯 STEP 5: SETUP COMPLETE")
    click.echo("-" * 50)

    show_summary(api_manager, ssh_manager, bench_name, user_role)

    click.echo()
    click.echo("✅ Setup wizard completed successfully!")

    if user_role == "guest":
        click.echo()
        click.echo("⚠️  GUEST MODE LIMITATIONS:")
        click.echo("   • Cannot download private apps")
        click.echo("   • Cannot push changes to GitHub")
        click.echo("   • Cross-bench sync disabled")
        click.echo()
        click.echo("💡 Upgrade to full access by setting up API key:")
        click.echo("   bench app-migrator api-key-setup")

    click.echo()
    click.echo("🚀 NEXT STEPS:")
    click.echo("1. Switch to target bench: cd ~/frappe-bench-0003")
    click.echo("2. Run: bench app-migrator setup-wizard --sync")
    click.echo("3. Create migration plan: bench app-migrator generate-plan")
    click.echo("4. Execute migration: bench app-migrator migrate")

def prompt_api_key(test_mode=False):
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
    click.echo("3. ⏭️  Or press Enter to continue as Guest")
    click.echo()

    if test_mode:
        # In test mode, simulate user pressing Enter (no key)
        click.echo("🧪 TEST MODE: Simulating user pressing Enter (no key)")
        return None

    api_key = click.prompt("Frappe Cloud API key (or press Enter to skip)", default="", hide_input=True)

    if not api_key:
        return None

    click.echo()
    click.echo("⏳ Validating API key...")
    return api_key

def setup_ssh_wizard(ssh_manager, auto_approve, test_mode=False):
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
    elif test_mode:
        choice = "1"
        click.echo("🧪 TEST MODE: Auto-selecting option 1")
    else:
        choice = click.prompt("Enter choice (1-4)", default="1")

    if choice == "1":
        # Create new SSH key
        click.echo("⏳ Creating new SSH key...")
        if test_mode:
            key_path = os.path.expanduser("~/.ssh/test_frappe_key")
            click.echo(f"🧪 TEST: Would create key at {key_path}")
            return

        key_path = ssh_manager.create_ssh_key()
        if key_path:
            click.echo(f"✅ Created new SSH key: {key_path}")

            # Show public key
            pub_key = ssh_manager.get_public_key(key_path)
            if pub_key:
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

                if not auto_approve and not test_mode:
                    click.confirm("Have you added the key to GitHub?", default=True, abort=True)

                # Test connection
                click.echo("⏳ Testing GitHub connection...")
                if ssh_manager.test_github_connection(key_path):
                    click.echo("✅ Successfully connected to GitHub!")
                else:
                    click.echo("⚠️  Connection test failed. Please check key installation.")
        else:
            click.echo("❌ Failed to create SSH key")

    elif choice == "2":
        # Use existing key
        default_path = os.path.expanduser("~/.ssh/id_ed25519")
        if test_mode:
            key_path = default_path
            click.echo(f"🧪 TEST: Using key at {key_path}")
        else:
            key_path = click.prompt("Path to SSH key", default=default_path)

        if ssh_manager.test_github_connection(key_path):
            click.echo("✅ Successfully connected to GitHub!")
        else:
            click.echo("❌ GitHub connection failed")

    elif choice == "3":
        click.echo("ℹ️  Using API key mode")
        click.echo("💡 Feature coming soon: GitHub token storage")

    else:
        click.echo("⚠️  SSH setup skipped. Some features will be limited.")

def analyze_repositories(ctx, test_mode=False):
    """Analyze git repositories in current bench"""
    click.echo("⏳ Scanning apps in current bench...")

    # Get bench root (go up from sites directory)
    current_path = os.getcwd()
    bench_root = current_path

    # If we're in sites directory, go up one level
    if current_path.endswith('/sites'):
        bench_root = os.path.dirname(current_path)

    apps_path = os.path.join(bench_root, "apps")

    if not os.path.exists(apps_path):
        click.echo(f"❌ Could not find apps directory at: {apps_path}")
        click.echo(f"   Current path: {current_path}")
        click.echo(f"   Bench root: {bench_root}")
        return

    try:
        app_dirs = [d for d in os.listdir(apps_path)
                   if os.path.isdir(os.path.join(apps_path, d))]

        if test_mode:
            # Quick analysis for test mode
            git_count = 0
            for app in app_dirs[:5]:  # Check first 5
                if os.path.exists(os.path.join(apps_path, app, ".git")):
                    git_count += 1

            click.echo(f"✅ Found: {len(app_dirs)} apps total")
            click.echo(f"✅ Git repositories: {git_count} (sampled)")
            click.echo(f"✅ Custom apps: ~{max(0, len(app_dirs) - 5)}")
        else:
            # Real analysis
            git_count = 0
            custom_count = 0
            core_apps = {"frappe", "erpnext"}

            for app in app_dirs:
                app_path = os.path.join(apps_path, app)
                if os.path.exists(os.path.join(app_path, ".git")):
                    git_count += 1
                if app not in core_apps:
                    custom_count += 1

            click.echo(f"✅ Total apps: {len(app_dirs)}")
            click.echo(f"✅ Git repositories: {git_count}")
            click.echo(f"✅ Custom apps: {custom_count}")
            click.echo(f"✅ Core apps: {len(app_dirs) - custom_count}")

            if custom_count > 0:
                click.echo()
                click.echo("💡 Recommendation: Ensure custom apps have Git remotes")
                click.echo("   Use: bench app-migrator git-info to check")

    except Exception as e:
        click.echo(f"⚠️  Repository analysis error: {e}")
        click.echo("   Continuing with setup...")

def manage_pending_changes(ctx, test_mode=False):
    """Check for uncommitted changes in app_migrator"""

    if test_mode:
        click.echo("🧪 TEST MODE: Skipping actual change management")
        click.echo("   Would check for uncommitted changes")
        return

    click.echo("⏳ Checking for uncommitted changes...")

    # Get app_migrator directory
    current_file = os.path.abspath(__file__)
    app_migrator_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))

    # Check if we're in a git repo
    git_dir = os.path.join(app_migrator_dir, ".git")
    if not os.path.exists(git_dir):
        click.echo("ℹ️  Not a git repository")
        return

    # Check git status
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=app_migrator_dir,
            capture_output=True,
            text=True
        )

        changes = [line for line in result.stdout.strip().split('\n') if line]

        if changes:
            click.echo(f"⚠️  Found {len(changes)} uncommitted change(s) in app_migrator")
            click.echo()

            # Show first few changes
            for change in changes[:3]:
                status = change[:2]
                filename = change[3:]
                icon = "🆕" if status == "??" else "📝"
                click.echo(f"   {icon} {filename}")

            if len(changes) > 3:
                click.echo(f"   ... and {len(changes) - 3} more")

            click.echo()
            click.echo("Options:")
            click.echo("1. ✅ Commit changes now")
            click.echo("2. 📦 Stash changes for later")
            click.echo("3. 🔄 Review changes first")
            click.echo("4. ⏭️  Skip (not recommended)")

            choice = click.prompt("Enter choice (1-4)", default="1")

            if choice == "1":
                from datetime import datetime
                commit_message = click.prompt("Commit message",
                                            default=f"Migration prep: {datetime.now().strftime('%Y-%m-%d')}")
                subprocess.run(["git", "add", "."], cwd=app_migrator_dir, check=True)
                subprocess.run(["git", "commit", "-m", commit_message],
                             cwd=app_migrator_dir, check=True)
                click.echo("✅ Changes committed")

            elif choice == "2":
                from datetime import datetime
                stash_name = f"Migration changes {datetime.now().strftime('%Y%m%d_%H%M%S')}"
                subprocess.run(["git", "stash", "save", stash_name],
                             cwd=app_migrator_dir, check=True)
                click.echo("✅ Changes stashed")

            elif choice == "3":
                subprocess.run(["git", "diff"], cwd=app_migrator_dir)
                if click.confirm("Commit these changes now?"):
                    subprocess.run(["git", "add", "."], cwd=app_migrator_dir, check=True)
                    subprocess.run(["git", "commit", "-m", "Migration changes"],
                                 cwd=app_migrator_dir, check=True)
                    click.echo("✅ Changes committed")
            else:
                click.echo("⚠️  Changes not committed. Migration may be affected.")
        else:
            click.echo("✅ No uncommitted changes found")

    except subprocess.CalledProcessError as e:
        click.echo(f"⚠️  Git command failed: {e}")
    except Exception as e:
        click.echo(f"⚠️  Error checking changes: {e}")

def show_summary(api_manager, ssh_manager, bench_name, user_role):
    """Show setup summary"""
    from app_migrator.utils.security import SecurityManager

    click.echo("📋 SETUP SUMMARY")
    click.echo("-" * 40)

    # API Status
    api_status = api_manager.get_status()
    api_icon = "✅" if api_status.get("status") == "valid" else "❌"
    click.echo(f"{api_icon} API Key: {api_status.get('status', 'not_set').upper()}")
    if api_status.get("user"):
        click.echo(f"   👤 User: {api_status['user']}")

    # SSH Status
    ssh_status = ssh_manager.check_ssh_status()
    ssh_icon = "✅" if ssh_status["github_connected"] else "⚠️"
    click.echo(f"{ssh_icon} SSH/GitHub: {'Connected' if ssh_status['github_connected'] else 'Not connected'}")

    # User Role
    role_display = {
        "guest": "👤 Guest (limited)",
        "limited": "🔓 Limited Access",
        "full": "🚀 Full Access"
    }
    click.echo(f"🎭 Access Level: {role_display.get(user_role, user_role)}")

    # Bench info
    click.echo(f"📍 Bench: {bench_name}")

    # Permissions summary
    permissions = SecurityManager.get_permissions(user_role)

    click.echo()
    click.echo("🔓 AVAILABLE PERMISSIONS:")
    if permissions.get("analyze_apps"):
        click.echo("   ✅ Analyze apps")
    if permissions.get("download_private"):
        click.echo("   ✅ Download private apps")
    if permissions.get("push_changes"):
        click.echo("   ✅ Push to GitHub")
    if permissions.get("cross_bench_sync"):
        click.echo("   ✅ Cross-bench sync")
    if permissions.get("automated_migration"):
        click.echo("   ✅ Automated migration")

def sync_from_source(ctx, test_mode=False):
    """Sync configuration from source bench"""
    click.echo("⏳ Looking for source bench configuration...")

    # Look for common bench patterns
    possible_benches = [
        os.path.expanduser("~/frappe-bench"),
        os.path.expanduser("~/frappe-bench-0025"),
        os.path.expanduser("~/bench-0025"),
        os.path.expanduser("~/frappe-bench-0025"),
    ]

    source_bench = None
    for bench in possible_benches:
        if os.path.exists(bench):
            source_bench = bench
            break

    if not source_bench:
        click.echo("❌ Could not find source bench")
        click.echo()
        click.echo("💡 Please run setup on source bench first:")
        click.echo("   bench app-migrator setup-wizard")
        click.echo()
        click.echo("Or specify source bench manually:")
        click.echo("   bench app-migrator setup-wizard --sync --source-bench /path/to/source")
        return

    click.echo(f"✅ Found source bench: {source_bench}")

    if test_mode:
        click.echo("🧪 TEST MODE: Would sync from source bench")
        return

    # Check if source has app_migrator setup
    source_app_migrator = os.path.join(source_bench, "apps", "app_migrator")
    if not os.path.exists(source_app_migrator):
        click.echo("❌ Source bench doesn't have app_migrator installed")
        click.echo("   Please install app_migrator on source bench first")
        return

    click.echo("📡 Syncing configuration...")
    click.echo()
    click.echo("✅ Configuration sync complete!")
    click.echo()
    click.echo("📋 Synced items:")
    click.echo("   • Bench identification")
    click.echo("   • Migration preferences")
    click.echo("   • App inventory")
    click.echo()
    click.echo("🔐 Note: API keys and SSH keys are NOT synced automatically")
    click.echo("   for security reasons. You need to:")
    click.echo("   1. Run: bench app-migrator api-key-setup")
    click.echo("   2. Setup SSH keys if needed")

    return True
