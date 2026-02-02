"""
Git Information Command - Show detailed git status for all apps
"""

import click
import os
from pathlib import Path
from .git_utils import get_app_info, FrappeCloudAPI


@click.command('git-info')
@click.option('--app', '-a', help='Specific app to check (default: all apps)')
@click.option('--api-key', help='Frappe Cloud API key (for getting git info)')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
def git_info(app=None, api_key=None, verbose=False):
    """
    Show Git Information for Frappe Apps
    
    Display detailed git status, remotes, and available git URLs for all apps.
    
    Examples:
        bench app-migrator git-info              # Show info for all apps
        bench app-migrator git-info --app erpnext # Show info for specific app
        bench app-migrator git-info --verbose    # Show detailed information
        bench app-migrator git-info --api-key [KEY] # Use Frappe Cloud API
    """
    from frappe import _
    
    click.echo("🔍 App Migrator Git Information")
    click.echo("="*32)
    
    # Set API key from environment if not provided
    if not api_key:
        api_key = os.getenv('FRAPPE_CLOUD_API_KEY')
    
    # Get apps
    bench_path = Path(os.getenv('BENCH_PATH', '/home/frappe/frappe-bench'))
    apps_path = bench_path / 'apps'
    
    if app:
        apps_to_check = [app] if (apps_path / app).exists() else []
        if not apps_to_check:
            click.echo(f"❌ App '{app}' not found")
            return
    else:
        apps_to_check = sorted([d.name for d in apps_path.iterdir() 
                               if d.is_dir() and not d.name.startswith('.')])
    
    if not apps_to_check:
        click.echo("❌ No apps found")
        return
    
    click.echo(f"📦 Found {len(apps_to_check)} app(s)")
    
    # Get info for each app
    git_repos = []
    non_git_apps = []
    apps_with_public_git = []
    apps_with_cloud_git = []
    
    for app_name in apps_to_check:
        app_info = get_app_info(app_name, api_key)
        
        if app_info['is_git_repo']:
            git_repos.append(app_info)
        else:
            non_git_apps.append(app_info)
        
        if app_info['public_git_url']:
            apps_with_public_git.append(app_info)
        
        if app_info['frappe_cloud_info'] and app_info['frappe_cloud_info'].get('git_url'):
            apps_with_cloud_git.append(app_info)
    
    # Summary
    click.echo(f"\n📊 SUMMARY:")
    click.echo(f"  • Git repositories: {len(git_repos)}")
    click.echo(f"  • Non-git directories: {len(non_git_apps)}")
    click.echo(f"  • Apps with public git URLs: {len(apps_with_public_git)}")
    click.echo(f"  • Apps with Frappe Cloud git info: {len(apps_with_cloud_git)}")
    
    # Show git repositories
    if git_repos:
        click.echo(f"\n✅ GIT REPOSITORIES ({len(git_repos)}):")
        click.echo("  App Name          Branch          Remote")
        click.echo("  " + "-"*50)
        for info in git_repos:
            branch_display = info['branch'] or 'no branch'
            remote_display = info['remote_url'] or 'no remote'
            if len(remote_display) > 30:
                remote_display = remote_display[:27] + "..."
            click.echo(f"  {info['name']:18} {branch_display:15} {remote_display}")
    
    # Show non-git apps with available git info
    if apps_with_public_git or apps_with_cloud_git:
        click.echo(f"\n🔗 NON-GIT APPS WITH AVAILABLE GIT URLs:")
        for info in non_git_apps:
            if info['public_git_url'] or (info['frappe_cloud_info'] and info['frappe_cloud_info'].get('git_url')):
                click.echo(f"  • {info['name']}:")
                if info['public_git_url']:
                    click.echo(f"      Public: {info['public_git_url']}")
                if info['frappe_cloud_info'] and info['frappe_cloud_info'].get('git_url'):
                    click.echo(f"      Frappe Cloud: {info['frappe_cloud_info']['git_url']}")
    
    # Show pure non-git apps
    pure_non_git = [info for info in non_git_apps 
                   if not info['public_git_url'] and 
                   not (info['frappe_cloud_info'] and info['frappe_cloud_info'].get('git_url'))]
    
    if pure_non_git:
        click.echo(f"\n📦 PURE NON-GIT DIRECTORIES ({len(pure_non_git)}):")
        click.echo(f"  {', '.join([info['name'] for info in pure_non_git])}")
    
    # Verbose mode - show all details
    if verbose:
        click.echo(f"\n🔍 VERBOSE DETAILS:")
        for info in apps_to_check:
            app_info = get_app_info(info, api_key)
            click.echo(f"\n{'='*40}")
            click.echo(f"APP: {app_info['name']}")
            click.echo(f"Path: {app_info['path']}")
            click.echo(f"Exists: {app_info['exists']}")
            click.echo(f"Is Git Repo: {app_info['is_git_repo']}")
            if app_info['is_git_repo']:
                click.echo(f"  Remote: {app_info['remote_url']}")
                click.echo(f"  Branch: {app_info['branch']}")
            if app_info['public_git_url']:
                click.echo(f"Public Git URL: {app_info['public_git_url']}")
            if app_info['frappe_cloud_info']:
                click.echo(f"Frappe Cloud Info: {app_info['frappe_cloud_info']}")
    
    # Recommendations
    if non_git_apps:
        click.echo(f"\n💡 RECOMMENDATIONS:")
        click.echo(f"  1. Use 'bench app-migrator git-pull --show-all' to see all apps")
        click.echo(f"  2. Set FRAPPE_CLOUD_API_KEY env var for more git info:")
        click.echo(f"     export FRAPPE_CLOUD_API_KEY='your-api-key'")
        click.echo(f"  3. Convert non-git apps to git repos:")
        click.echo(f"     bench app-migrator git-pull --convert-non-git")
        click.echo(f"  4. Clone missing git repos:")
        click.echo(f"     bench get-app app_name --branch version-15")

# Add to commands list
commands = [git_info]
