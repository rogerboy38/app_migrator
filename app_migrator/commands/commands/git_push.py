import click
import os
import subprocess
import sys
from pathlib import Path

@click.command('git-push')
@click.option('--app', '-a', help='Specific app to push (default: all apps)')
@click.option('--message', '-m', help='Commit message')
@click.option('--force', '-f', is_flag=True, help='Force push')
@click.option('--dry-run', is_flag=True, help='Show what would happen')
@click.option('--safe', '-s', is_flag=True, help='Use safe confirmation')
def git_push(app=None, message=None, force=False, dry_run=False, safe=False):
    """
    Git Push Helper for Frappe Apps
    
    Push one or all apps to GitHub with proper configuration.
    
    Examples:
        bench app-migrator git-push                     # Push all apps
        bench app-migrator git-push --app rnd_nutrition # Push specific app
        bench app-migrator git-push --safe              # Use safe confirmation
        bench app-migrator git-push --dry-run           # Show what would happen
    """
    from frappe import _
    
    bench_path = Path(os.getenv('BENCH_PATH', '/home/frappe/frappe-bench'))
    apps_path = bench_path / 'apps'
    
    # GitHub configuration for rogerboy38
    github_config = {
        'rnd_nutrition': 'git@github.com:rogerboy38/rnd_nutrition2.git',
        'rnd_warehouse_management': 'git@github.com:rogerboy38/rnd_warehouse_management.git',
        'amb_w_tds': 'git@github.com:rogerboy38/amb_w_tds.git',
        'app_migrator': 'git@github.com:rogerboy38/app_migrator.git'
    }
    
    def run_cmd(cmd, cwd=None):
        """Run command and return output"""
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, '', str(e)
    
    def check_ssh():
        """Check SSH connection to GitHub"""
        click.echo("🔗 Checking SSH connection to GitHub...")
        code, out, err = run_cmd("ssh -T git@github.com")
        if "successfully authenticated" in out or "successfully authenticated" in err:
            click.echo("✅ SSH connection working")
            return True
        else:
            click.echo("❌ SSH connection failed")
            return False
    
    def push_single_app(app_name):
        """Push a single app to GitHub"""
        app_dir = apps_path / app_name
        
        if not app_dir.exists():
            click.echo(f"❌ App '{app_name}' not found at {app_dir}")
            return False
        
        click.echo(f"\n📦 Processing {app_name}...")
        
        # Check if it's a git repo
        git_dir = app_dir / '.git'
        if not git_dir.exists():
            click.echo(f"  ⚠️  Not a git repository")
            return False
        
        # Check remote
        code, remote_out, remote_err = run_cmd("git remote get-url origin", cwd=app_dir)
        current_remote = remote_out.strip() if code == 0 else None
        
        # Set remote if not configured
        if not current_remote and app_name in github_config:
            click.echo(f"  🔧 Setting remote to GitHub...")
            run_cmd(f"git remote add origin {github_config[app_name]}", cwd=app_dir)
            current_remote = github_config[app_name]
        
        if not current_remote:
            click.echo(f"  ❌ No remote configured for {app_name}")
            return False
        
        # Get current branch
        code, branch_out, _ = run_cmd("git branch --show-current", cwd=app_dir)
        current_branch = branch_out.strip() if code == 0 else "main"
        
        click.echo(f"  🌿 Branch: {current_branch}")
        click.echo(f"  🔗 Remote: {current_remote}")
        
        # Check for changes
        code, status_out, _ = run_cmd("git status --porcelain", cwd=app_dir)
        changes = len([line for line in status_out.split('\n') if line.strip()])
        
        if changes > 0:
            click.echo(f"  📝 Found {changes} uncommitted change(s)")
            if not dry_run:
                # Add all changes
                run_cmd("git add .", cwd=app_dir)
                
                # Create commit message
                commit_msg = message or f"Auto-commit from bench: {app_name} - {os.popen('date').read().strip()}"
                run_cmd(f'git commit -m "{commit_msg}"', cwd=app_dir)
        
        # Push
        if dry_run:
            click.echo(f"  📤 Would push to: {current_remote}")
            return True
        
        push_cmd = f"git push origin {current_branch}"
        if force:
            push_cmd += " --force-with-lease"
        
        click.echo(f"  📤 Pushing to GitHub...")
        code, push_out, push_err = run_cmd(push_cmd, cwd=app_dir)
        
        if code == 0:
            click.echo(f"  ✅ Successfully pushed {app_name}")
            return True
        else:
            click.echo(f"  ❌ Failed to push {app_name}")
            click.echo(f"    Error: {push_err}")
            return False
    
    # Main execution
    click.echo("🚀 App Migrator Git Push Helper")
    click.echo("================================")
    
    # Check SSH first
    if not check_ssh():
        if not safe:
            click.confirm("⚠️  SSH connection failed. Continue anyway?", abort=True)
    
    # Determine which apps to push
    apps_to_push = []
    if app:
        if app in github_config:
            apps_to_push = [app]
        else:
            click.echo(f"❌ App '{app}' not in configured GitHub list")
            click.echo(f"   Available: {', '.join(github_config.keys())}")
            return
    else:
        apps_to_push = list(github_config.keys())
    
    if safe:
        click.echo(f"\n📋 Apps to push: {', '.join(apps_to_push)}")
        click.confirm("\n🚀 Proceed with pushing all apps?", abort=True)
    
    if dry_run:
        click.echo("\n🔍 DRY RUN - No changes will be made")
    
    # Push each app
    success_count = 0
    for app_name in apps_to_push:
        if push_single_app(app_name):
            success_count += 1
    
    # Summary
    click.echo(f"\n{'='*50}")
    click.echo("📊 Push Summary:")
    click.echo(f"  • Total apps: {len(apps_to_push)}")
    click.echo(f"  • Successful: {success_count}")
    click.echo(f"  • Failed: {len(apps_to_push) - success_count}")
    
    if success_count == len(apps_to_push):
        click.echo("\n✅ All apps pushed successfully!")
    else:
        click.echo(f"\n⚠️  {len(apps_to_push) - success_count} app(s) failed")

# Add to commands list
commands = [git_push]
