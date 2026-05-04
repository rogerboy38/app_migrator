import os
import subprocess
from pathlib import Path

import click
from frappe.commands import pass_context

# Import the GitHelper
try:
    from app_migrator.utils.git_helper import GitHelper
except ImportError:
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from app_migrator.utils.git_helper import GitHelper

@click.command('git-push')
@click.option('--app', help='Specific app to push (default: all apps)')
@click.option('--message', '-m', help='Commit message for uncommitted changes')
@click.option('--dry-run', is_flag=True, help='Show what would be pushed without actually pushing')
@click.option('--force', '-f', is_flag=True, help='Force push (use with caution)')
@click.option('--pull-first', is_flag=True, help='Pull from remote before pushing')
@click.option('--skip-diverged', is_flag=True, help='Skip apps with diverged branches')
@pass_context
def git_push(ctx, app, message, dry_run, force, pull_first, skip_diverged):
    """Enhanced Git Push Helper with multi-remote support"""

    click.secho("🚀 App Migrator Git Push Helper", fg="cyan", bold=True)
    click.secho("================================\n", fg="cyan")

    # Check SSH connection - simplified version
    click.echo("🔗 Checking SSH connection to GitHub...")
    try:
        # Simple SSH test
        result = subprocess.run(
            "ssh -o BatchMode=yes -o ConnectTimeout=5 git@github.com 2>&1",
            shell=True,
            capture_output=True,
            text=True
        )

        # Check for any response (even permission denied means SSH works)
        if result.returncode in [0, 1] or "Permission denied" in result.stderr:
            click.secho("✅ SSH connection working\n", fg="green")
        else:
            click.secho("⚠️  SSH connection may have issues", fg="yellow")
            if not dry_run:
                if click.confirm("Continue anyway?"):
                    click.secho("⚠️  Continuing without SSH verification\n", fg="yellow")
                else:
                    click.secho("❌ Aborting", fg="red")
                    return
    except Exception as e:
        click.secho(f"⚠️  SSH check error: {e}", fg="yellow")
        click.secho("⚠️  Continuing anyway\n", fg="yellow")

    if dry_run:
        click.secho("🔍 DRY RUN - No changes will be made\n", fg="yellow")

    # Get bench path correctly
    # Try multiple methods to find the bench root
    bench_path = None

    # Method 1: Use ctx.bench_path if available
    if hasattr(ctx, 'bench_path') and ctx.bench_path:
        bench_path = Path(ctx.bench_path)
    else:
        # Method 2: Try to find bench from current directory
        current = Path.cwd()
        # Look for bench directory by checking parent directories
        for parent in [current, *list(current.parents)]:
            if (parent / "apps").exists() and (parent / "sites").exists():
                bench_path = parent
                break

        # Method 3: Default to common location
        if not bench_path:
            bench_path = Path("/home/frappe/frappe-bench")

    if not bench_path or not bench_path.exists():
        click.secho(f"❌ Cannot find bench directory: {bench_path}", fg="red")
        return

    apps_dir = bench_path / "apps"

    if not apps_dir.exists():
        click.secho(f"❌ Apps directory not found: {apps_dir}", fg="red")
        return

    if app:
        apps = [app]
    else:
        # Find all git repos in apps directory
        apps = []
        for item in apps_dir.iterdir():
            if item.is_dir():
                git_dir = item / ".git"
                if git_dir.exists():
                    apps.append(item.name)

    click.echo(f"📋 Found {len(apps)} app(s) with git repositories")

    successful = []
    failed = []

    for app_name in apps:
        app_path = apps_dir / app_name

        if not app_path.exists():
            click.echo(f"  ⚠️  App directory not found: {app_path}")
            continue

        click.echo(f"📦 Processing {app_name}...")

        # Change to app directory
        original_cwd = os.getcwd()
        try:
            os.chdir(app_path)
        except Exception as e:
            click.secho(f"  ❌ Cannot change to app directory: {e}", fg="red")
            failed.append(app_name)
            continue

        try:
            # Get current branch
            current_branch = GitHelper.get_current_branch()
            click.echo(f"  🌿 Branch: {current_branch}")

            # Get all remotes
            remotes = GitHelper.get_remotes()

            if not remotes:
                click.echo(f"  ❌ No push remotes found for {app_name}")
                failed.append(app_name)
                continue

            # Check for uncommitted changes
            status_result = subprocess.run(
                "git status --porcelain",
                shell=True,
                capture_output=True,
                text=True
            )

            uncommitted_changes = [line for line in status_result.stdout.strip().split('\n') if line]

            if uncommitted_changes and message:
                click.echo(f"  📝 Found {len(uncommitted_changes)} uncommitted change(s)")
                if not dry_run:
                    # Stage and commit changes
                    subprocess.run("git add .", shell=True, check=True)
                    subprocess.run(f'git commit -m "{message}"', shell=True, check=True)
                    click.secho(f"  ✅ Committed changes with message: {message}", fg="green")

            # Process each remote
            for remote_name, remote_url in remotes.items():
                click.echo(f"  🔗 Remote: {remote_name} -> {remote_url}")

                # Check branch status
                status = GitHelper.get_branch_status(remote_name, current_branch)

                if status['status'] == 'no_remote':
                    click.echo(f"    ℹ️  Remote branch {current_branch} doesn't exist on {remote_name}")
                    # Create remote branch if force option is enabled
                    if force and not dry_run:
                        subprocess.run(f"git push --set-upstream {remote_name} {current_branch}",
                                      shell=True, check=True)
                        click.secho(f"    ✅ Created remote branch on {remote_name}", fg="green")

                elif status['status'] == 'behind':
                    click.echo(f"    ⬇️  Local branch is {status.get('count', 0)} commit(s) behind {remote_name}")
                    if pull_first and not dry_run:
                        try:
                            subprocess.run(f"git pull {remote_name} {current_branch}",
                                         shell=True, check=True)
                            click.secho(f"    ✅ Pulled from {remote_name}", fg="green")
                        except subprocess.CalledProcessError:
                            click.secho(f"    ❌ Failed to pull from {remote_name}", fg="red")
                            if not force:
                                failed.append(f"{app_name} ({remote_name})")
                                continue

                elif status['status'] == 'diverged':
                    ahead = status.get('ahead', 0)
                    behind = status.get('behind', 0)
                    click.echo(f"    ⚠️  Branch has diverged ({ahead} ahead, {behind} behind)")
                    if skip_diverged:
                        click.echo(f"    ⏭️  Skipping {remote_name} due to divergence")
                        continue
                    elif force and not dry_run:
                        click.secho(f"    ⚡ Force pushing to {remote_name}...", fg="yellow")
                        # Force push for diverged branches
                        push_cmd = f"git push --force {remote_name} {current_branch}"
                    else:
                        click.secho(f"    ❌ Cannot push to {remote_name} (branches have diverged)", fg="red")
                        click.secho("    💡 Use --force to force push or --skip-diverged to skip", fg="yellow")
                        failed.append(f"{app_name} ({remote_name})")
                        continue

                elif status['status'] == 'ahead':
                    count = status.get('count', 0)
                    click.echo(f"    ⬆️  Local branch is {count} commit(s) ahead of {remote_name}")
                    push_cmd = f"git push {remote_name} {current_branch}"

                elif status['status'] == 'same':
                    click.echo(f"    ✅ Already up to date with {remote_name}")
                    continue

                else:  # 'unknown' or other status
                    push_cmd = f"git push {remote_name} {current_branch}"

                # Perform the push if not dry-run
                if not dry_run:
                    try:
                        click.echo(f"    📤 Pushing to {remote_name}...")
                        subprocess.run(push_cmd, shell=True, check=True)
                        click.secho(f"    ✅ Successfully pushed to {remote_name}", fg="green")
                        successful.append(f"{app_name} ({remote_name})")
                    except subprocess.CalledProcessError as e:
                        click.secho(f"    ❌ Failed to push to {remote_name}: {e}", fg="red")
                        failed.append(f"{app_name} ({remote_name})")
                else:
                    click.echo(f"    📤 Would push to: {remote_url}")
                    successful.append(f"{app_name} ({remote_name})")

        except Exception as e:
            click.secho(f"  ❌ Error processing {app_name}: {e!s}", fg="red")
            failed.append(app_name)
        finally:
            os.chdir(original_cwd)

    # Summary
    click.secho("\n" + "="*50, fg="cyan")
    click.secho("📊 Push Summary:", fg="cyan", bold=True)
    click.echo(f"  • Total apps processed: {len(apps)}")
    click.echo(f"  • Successful pushes: {len(successful)}")
    click.echo(f"  • Failed pushes: {len(failed)}")

    if successful:
        click.secho("\n✅ Successful operations:", fg="green")
        for success in successful:
            click.echo(f"  ✓ {success}")

    if failed:
        click.secho("\n❌ Failed operations:", fg="red")
        for fail in failed:
            click.echo(f"  ✗ {fail}")

    if not failed:
        click.secho("\n✅ All operations completed successfully!", fg="green")
    else:
        click.secho(f"\n⚠️  Completed with {len(failed)} failure(s)", fg="yellow")
