"""
Git Pull Helper for Frappe Apps
Pulls latest changes from GitHub for one or all apps
"""

import click
import os
import subprocess
import sys
from pathlib import Path
import shlex
from typing import List, Dict, Tuple, Optional
from .git_utils import get_app_info, FrappeCloudAPI, clone_app_from_git, convert_to_git_repo
from .api_key_manager import APISessionManager


def get_apps_to_process(app_filter: Optional[str] = None) -> List[str]:
    """Get list of apps to process based on filter"""
    bench_path = Path(os.getenv('BENCH_PATH', '/home/frappe/frappe-bench'))
    apps_path = bench_path / 'apps'
    
    all_apps = [d.name for d in apps_path.iterdir() 
                if d.is_dir() and not d.name.startswith('.')]
    
    if app_filter:
        if app_filter in all_apps:
            return [app_filter]
        else:
            click.echo(f"❌ App '{app_filter}' not found in {apps_path}")
            click.echo(f"Available apps: {', '.join(sorted(all_apps))}")
            return []
    
    return sorted(all_apps)


def check_ssh_connection() -> bool:
    """Check SSH connection to GitHub"""
    try:
        click.echo("🔗 Checking SSH connection to GitHub...")
        result = subprocess.run(
            ['ssh', '-T', 'git@github.com'],
            capture_output=True,
            text=True,
            check=False
        )
        
        # GitHub returns "successfully authenticated" even with exit code 1
        if "successfully authenticated" in result.stderr.lower():
            click.echo("✅ SSH connection working")
            return True
        else:
            click.echo(f"❌ SSH connection failed: {result.stderr.strip()}")
            return False
    except Exception as e:
        click.echo(f"❌ SSH check error: {str(e)}")
        return False


def get_api_key(api_key_option: str) -> Optional[str]:
    """Get API key based on option"""
    if api_key_option == 'auto':
        # Try to load from session
        manager = APISessionManager()
        api_key = manager.load_api_key()
        if api_key:
            click.echo("🔑 Using API key from session")
        return api_key
    elif api_key_option and api_key_option != 'none':
        return api_key_option
    else:
        return None


def pull_single_app(app_name: str, dry_run: bool = False, force: bool = False, 
                   api_key: Optional[str] = None) -> Dict:
    """Pull latest changes for a single app, returns detailed status"""
    bench_path = Path(os.getenv('BENCH_PATH', '/home/frappe/frappe-bench'))
    app_path = bench_path / 'apps' / app_name
    
    if not app_path.exists():
        return {
            'app': app_name,
            'success': False,
            'status': 'not_found',
            'message': f'App directory not found'
        }
    
    # Get comprehensive app info
    app_info = get_app_info(app_name, api_key)
    
    if not app_info['is_git_repo']:
        # Not a git repo - check if we can get git info
        message = 'Not a git repository'
        if app_info['public_git_url']:
            message = f'Not a git repo (public git available: {app_info["public_git_url"]})'
        elif app_info['frappe_cloud_info'] and app_info['frappe_cloud_info'].get('git_url'):
            message = f'Not a git repo (Frappe Cloud git: {app_info["frappe_cloud_info"]["git_url"]})'
        
        return {
            'app': app_name,
            'success': False,
            'status': 'not_git_repo',
            'message': message,
            'public_git_url': app_info['public_git_url'],
            'frappe_cloud_git_url': app_info['frappe_cloud_info'].get('git_url') if app_info['frappe_cloud_info'] else None
        }
    
    if not app_info['has_remote']:
        return {
            'app': app_name,
            'success': False,
            'status': 'no_remote',
            'message': 'No git remote configured'
        }
    
    # It's a git repo with remote - proceed with pull
    try:
        click.echo(f"\n📦 Processing {app_name}...")
        click.echo(f"  🌿 Branch: {app_info['branch'] or 'unknown'}")
        click.echo(f"  🔗 Remote: {app_info['remote_url']}")
        
        # First, fetch latest changes
        if dry_run:
            click.echo(f"  📥 Would run: git fetch origin {app_info['branch'] or ''}")
        else:
            click.echo(f"  📥 Fetching latest changes...")
            fetch_cmd = ['git', 'fetch', 'origin']
            if app_info['branch']:
                fetch_cmd.append(app_info['branch'])
            
            fetch_result = subprocess.run(
                fetch_cmd,
                cwd=app_path,
                capture_output=True,
                text=True
            )
            
            if fetch_result.returncode != 0:
                return {
                    'app': app_name,
                    'success': False,
                    'status': 'fetch_failed',
                    'message': f'Fetch failed: {fetch_result.stderr.strip()}'
                }
        
        # Check for uncommitted changes
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=app_path,
            capture_output=True,
            text=True,
            check=False
        )
        
        has_uncommitted = bool(status_result.stdout.strip())
        
        if has_uncommitted:
            if force:
                click.echo(f"  ⚠️  Uncommitted changes found, stashing...")
                if not dry_run:
                    stash_result = subprocess.run(
                        ['git', 'stash'],
                        cwd=app_path,
                        capture_output=True,
                        text=True
                    )
                    if stash_result.returncode != 0:
                        return {
                            'app': app_name,
                            'success': False,
                            'status': 'stash_failed',
                            'message': f'Stash failed: {stash_result.stderr.strip()}'
                        }
            else:
                return {
                    'app': app_name,
                    'success': False,
                    'status': 'has_uncommitted',
                    'message': 'Uncommitted changes found, use --force to stash and pull'
                }
        
        # Pull changes
        if dry_run:
            click.echo(f"  📥 Would run: git pull origin {app_info['branch'] or ''}")
            success = True
            pull_output = "Dry run - would pull"
        else:
            click.echo(f"  📥 Pulling changes...")
            pull_cmd = ['git', 'pull', 'origin']
            if app_info['branch']:
                pull_cmd.append(app_info['branch'])
            
            pull_result = subprocess.run(
                pull_cmd,
                cwd=app_path,
                capture_output=True,
                text=True
            )
            
            success = pull_result.returncode == 0
            pull_output = pull_result.stdout + pull_result.stderr
            
            if success:
                click.echo(f"  ✅ Successfully pulled {app_name}")
                # Show what changed
                log_result = subprocess.run(
                    ['git', 'log', '--oneline', 'HEAD@{1}..HEAD'],
                    cwd=app_path,
                    capture_output=True,
                    text=True,
                    check=False
                )
                if log_result.stdout.strip():
                    click.echo(f"  📝 Changes pulled:")
                    for line in log_result.stdout.strip().split('\n'):
                        click.echo(f"    • {line}")
            else:
                click.echo(f"  ❌ Pull failed: {pull_result.stderr.strip()}")
                
                # Check for merge conflicts
                if 'CONFLICT' in pull_result.stdout or 'CONFLICT' in pull_result.stderr:
                    click.echo(f"  ⚠️  Merge conflicts detected!")
                    click.echo(f"  💡 Resolve conflicts in: {app_path}")
        
        # Restore stashed changes if any
        if has_uncommitted and force and success and not dry_run:
            click.echo(f"  🔄 Restoring stashed changes...")
            pop_result = subprocess.run(
                ['git', 'stash', 'pop'],
                cwd=app_path,
                capture_output=True,
                text=True
            )
            if pop_result.returncode != 0:
                click.echo(f"  ⚠️  Could not restore stashed changes: {pop_result.stderr.strip()}")
        
        return {
            'app': app_name,
            'success': success,
            'status': 'pulled' if success else 'pull_failed',
            'message': 'Successfully pulled' if success else f'Pull failed: {pull_output}',
            'branch': app_info['branch'],
            'remote': app_info['remote_url'],
            'has_uncommitted': has_uncommitted
        }
        
    except Exception as e:
        return {
            'app': app_name,
            'success': False,
            'status': 'error',
            'message': f'Error: {str(e)}'
        }


@click.command('git-pull')
@click.option('--app', '-a', help='Specific app to pull (default: all apps)')
@click.option('--force', '-f', is_flag=True, help='Force pull even with uncommitted changes (stash changes)')
@click.option('--dry-run', is_flag=True, help='Show what would happen without actually pulling')
@click.option('--safe', '-s', is_flag=True, help='Use safe confirmation before each pull')
@click.option('--skip-ssh-check', is_flag=True, help='Skip SSH connection check')
@click.option('--convert-non-git', is_flag=True, help='Convert non-git apps to git repos if git URL available')
@click.option('--api-key', default='auto', help='Frappe Cloud API key: "auto" (from session), "none", or actual key')
@click.option('--show-all', is_flag=True, help='Show all apps including non-git ones')
def git_pull(app=None, force=False, dry_run=False, safe=False, 
            skip_ssh_check=False, convert_non_git=False, api_key='auto', show_all=False):
    """
    Git Pull Helper for Frappe Apps
    
    Pull latest changes from GitHub for one or all apps.
    
    Examples:
        bench app-migrator git-pull                     # Pull all apps
        bench app-migrator git-pull --app rnd_nutrition # Pull specific app
        bench app-migrator git-pull --safe              # Use safe confirmation
        bench app-migrator git-pull --dry-run           # Show what would happen
        bench app-migrator git-pull --force            # Force pull (stash uncommitted changes)
        bench app-migrator git-pull --show-all         # Show all apps including non-git
        bench app-migrator git-pull --api-key auto     # Use API key from session (default)
    """
    from frappe import _
    
    click.echo("🚀 App Migrator Git Pull Helper")
    click.echo("="*32)
    
    # Get API key
    actual_api_key = get_api_key(api_key)
    if api_key == 'auto' and not actual_api_key:
        click.echo("ℹ️  No API key session found. Public git URLs only.")
        click.echo("💡 Setup API key: bench app-migrator api-key-setup")
    
    # Check SSH connection
    if not skip_ssh_check and not check_ssh_connection():
        if not click.confirm("❌ SSH connection failed. Continue anyway?", default=False):
            return
    
    if dry_run:
        click.echo("🔍 DRY RUN - No changes will be made")
    
    # Get apps to process
    apps_to_pull = get_apps_to_process(app)
    
    if not apps_to_pull:
        click.echo("❌ No apps to process")
        return
    
    click.echo(f"📦 Found {len(apps_to_pull)} app(s) to process")
    
    # Show summary
    if not dry_run and not safe and show_all:
        click.echo("\n📋 Summary of all apps:")
        for app_name in apps_to_pull:
            app_info = get_app_info(app_name, actual_api_key)
            status = "✅ Git repo" if app_info['is_git_repo'] else "📦 Non-git"
            remote = app_info['remote_url'] or app_info['public_git_url'] or 'No remote'
            click.echo(f"  • {app_name}: {status} - {remote}")
    
    # Convert non-git apps if requested
    if convert_non_git and not dry_run:
        click.echo("\n🔄 Checking non-git apps for conversion...")
        converted = 0
        for app_name in apps_to_pull:
            app_info = get_app_info(app_name, actual_api_key)
            if not app_info['is_git_repo']:
                git_url = (app_info['frappe_cloud_info'].get('git_url') 
                          if app_info['frappe_cloud_info'] 
                          else app_info['public_git_url'])
                
                if git_url:
                    if click.confirm(f"Convert {app_name} to git repo (remote: {git_url})?", default=False):
                        if convert_to_git_repo(app_name, git_url):
                            converted += 1
    
    # Confirm if safe mode
    if safe and not dry_run:
        if not click.confirm(f"\n⚠️  Pull latest changes for {len(apps_to_pull)} app(s)?", default=False):
            click.echo("❌ Pull cancelled")
            return
    
    # Process each app
    results = []
    for app_name in apps_to_pull:
        if safe and not dry_run:
            app_info = get_app_info(app_name, actual_api_key)
            if not app_info['is_git_repo']:
                if not click.confirm(f"\n⏭️  {app_name} is not a git repo. Skip?", default=True):
                    continue
            else:
                if not click.confirm(f"\n📦 Pull {app_name} from {app_info['remote_url']}?", default=False):
                    click.echo(f"  ⏭️  Skipping {app_name}")
                    continue
        
        result = pull_single_app(app_name, dry_run, force, actual_api_key)
        results.append(result)
    
    # Generate comprehensive summary
    click.echo(f"\n{'='*60}")
    click.echo("📊 PULL ANALYSIS SUMMARY")
    click.echo("="*60)
    
    # Categorize results
    categories = {
        'pulled': [],
        'pull_failed': [],
        'has_uncommitted': [],
        'not_git_repo': [],
        'no_remote': [],
        'fetch_failed': [],
        'stash_failed': [],
        'error': [],
        'not_found': []
    }
    
    for result in results:
        categories[result['status']].append(result)
    
    # Show git repos that were pulled
    if categories['pulled']:
        click.echo(f"\n✅ SUCCESSFULLY PULLED ({len(categories['pulled'])}):")
        for result in categories['pulled']:
            click.echo(f"  • {result['app']} ({result['branch']}) - {result['remote']}")
    
    # Show git repos that failed to pull
    if categories['pull_failed']:
        click.echo(f"\n❌ PULL FAILED ({len(categories['pull_failed'])}):")
        for result in categories['pull_failed']:
            click.echo(f"  • {result['app']}: {result['message']}")
    
    # Show git repos with uncommitted changes
    if categories['has_uncommitted']:
        click.echo(f"\n⚠️  HAS UNCOMMITTED CHANGES ({len(categories['has_uncommitted'])}):")
        click.echo("  Use --force to stash changes and pull")
        for result in categories['has_uncommitted']:
            click.echo(f"  • {result['app']}")
    
    # Show non-git repos
    if categories['not_git_repo']:
        click.echo(f"\n📦 NOT GIT REPOSITORIES ({len(categories['not_git_repo'])}):")
        for result in categories['not_git_repo']:
            message = result['message']
            if result.get('public_git_url'):
                message += f" | Public: {result['public_git_url']}"
            if result.get('frappe_cloud_git_url'):
                message += f" | Frappe Cloud: {result['frappe_cloud_git_url']}"
            click.echo(f"  • {result['app']}: {message}")
    
    # Show other issues
    other_issues = ['no_remote', 'fetch_failed', 'stash_failed', 'error', 'not_found']
    for issue in other_issues:
        if categories[issue]:
            click.echo(f"\n⚡ {issue.upper().replace('_', ' ')} ({len(categories[issue])}):")
            for result in categories[issue]:
                click.echo(f"  • {result['app']}: {result['message']}")
    
    # Final statistics
    total_git_repos = sum(len(categories[cat]) for cat in ['pulled', 'pull_failed', 'has_uncommitted', 'no_remote', 
                                                          'fetch_failed', 'stash_failed'])
    total_non_git = len(categories['not_git_repo'])
    
    click.echo(f"\n{'='*60}")
    click.echo("📈 FINAL STATISTICS:")
    click.echo(f"  • Total apps processed: {len(results)}")
    click.echo(f"  • Git repositories: {total_git_repos}")
    click.echo(f"  • Non-git directories: {total_non_git}")
    click.echo(f"  • Successfully pulled: {len(categories['pulled'])}")
    click.echo(f"  • Failed to pull: {len(categories['pull_failed'])}")
    click.echo(f"  • Need --force (uncommitted): {len(categories['has_uncommitted'])}")
    
    if total_non_git > 0:
        click.echo(f"\n💡 Tip: Use --show-all to see all apps")
        click.echo(f"💡 Tip: Use --convert-non-git to convert non-git apps to git repos")
        click.echo(f"💡 Tip: Setup API key for Frappe Cloud git info:")
        click.echo(f"      bench app-migrator api-key-setup")

# Add to commands list
commands = [git_pull]
