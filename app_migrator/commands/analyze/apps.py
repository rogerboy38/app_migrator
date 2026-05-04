"""
Analyze apps in current bench
"""
import json
import os
from pathlib import Path

import click


@click.command()
@click.option('--output', '-o', help='Output file (JSON format)')
@click.option('--detailed', '-d', is_flag=True, help='Show detailed analysis')
@click.option('--test', is_flag=True, help='Test mode')
@click.pass_context
def analyze_apps(ctx, output, detailed, test):
    """Analyze all apps in current bench"""

    click.echo("📊 APP ANALYSIS")
    click.echo("=" * 50)

    if test:
        click.echo("🧪 TEST MODE")
        click.echo()

    # Get bench path
    current_path = os.getcwd()
    bench_root = current_path

    # If we're in sites directory, go up one level
    if current_path.endswith('/sites'):
        bench_root = os.path.dirname(current_path)

    apps_path = os.path.join(bench_root, "apps")

    if not os.path.exists(apps_path):
        click.echo(f"❌ Could not find apps directory at: {apps_path}")
        return

    click.echo(f"📁 Bench: {os.path.basename(bench_root)}")
    click.echo(f"📍 Path: {apps_path}")
    click.echo()

    # Core apps list (these come with Frappe/ERPNext)
    core_apps = {"frappe", "erpnext"}

    try:
        # Get all app directories
        app_dirs = []
        for item in os.listdir(apps_path):
            item_path = os.path.join(apps_path, item)
            if os.path.isdir(item_path):
                app_dirs.append(item)

        total_apps = len(app_dirs)

        # Analyze each app
        analysis_results = {
            "bench": os.path.basename(bench_root),
            "path": apps_path,
            "total_apps": total_apps,
            "apps": []
        }

        click.echo(f"🔍 Found {total_apps} apps")
        click.echo()

        for app in sorted(app_dirs):
            app_path = os.path.join(apps_path, app)
            app_info = {
                "name": app,
                "path": app_path,
                "is_core": app in core_apps,
                "has_git": os.path.exists(os.path.join(app_path, ".git")),
                "has_setup_py": os.path.exists(os.path.join(app_path, "setup.py")),
                "has_pyproject": os.path.exists(os.path.join(app_path, "pyproject.toml")),
                "has_requirements": os.path.exists(os.path.join(app_path, "requirements.txt")),
            }

            # Try to get version from setup.py or pyproject.toml
            version = "unknown"
            setup_py = os.path.join(app_path, "setup.py")
            if os.path.exists(setup_py):
                try:
                    with open(setup_py) as f:
                        content = f.read()
                        import re
                        version_match = re.search(r"version\s*=\s*['\"]([^'\"]+)['\"]", content)
                        if version_match:
                            version = version_match.group(1)
                except:
                    pass

            app_info["version"] = version

            # Check for git info
            if app_info["has_git"]:
                try:
                    import subprocess
                    # Get git remote
                    result = subprocess.run(
                        ["git", "remote", "-v"],
                        cwd=app_path,
                        capture_output=True,
                        text=True
                    )
                    if result.stdout:
                        app_info["git_remote"] = result.stdout.strip().split('\n')[0] if result.stdout else "no remote"
                except:
                    app_info["git_remote"] = "error"

            analysis_results["apps"].append(app_info)

            # Display
            icon = "🔵" if app in core_apps else "🟢"
            git_icon = "✓" if app_info["has_git"] else "✗"
            click.echo(f"{icon} {app:<30} {git_icon} Git  v{version}")

            if detailed and app_info.get("git_remote"):
                click.echo(f"   📍 Remote: {app_info['git_remote']}")

        # Summary
        click.echo()
        click.echo("📋 SUMMARY:")
        core_count = sum(1 for app in analysis_results["apps"] if app["is_core"])
        custom_count = total_apps - core_count
        git_count = sum(1 for app in analysis_results["apps"] if app["has_git"])

        click.echo(f"   • Core apps: {core_count}")
        click.echo(f"   • Custom apps: {custom_count}")
        click.echo(f"   • Git repositories: {git_count}")
        click.echo(f"   • Non-git apps: {total_apps - git_count}")

        # Save to file if requested
        if output:
            with open(output, 'w') as f:
                json.dump(analysis_results, f, indent=2)
            click.echo(f"✅ Analysis saved to: {output}")

        # Recommendations
        click.echo()
        click.echo("💡 RECOMMENDATIONS:")

        non_git_apps = [app["name"] for app in analysis_results["apps"]
                       if not app["is_core"] and not app["has_git"]]

        if non_git_apps:
            click.echo(f"   ⚠️  {len(non_git_apps)} custom apps without Git:")
            for app in non_git_apps[:5]:  # Show first 5
                click.echo(f"     - {app}")
            if len(non_git_apps) > 5:
                click.echo(f"     ... and {len(non_git_apps) - 5} more")
            click.echo("   💡 Consider initializing Git repositories for these apps")

        click.echo()
        click.echo("✅ Analysis complete!")
        click.echo()
        click.echo("🚀 Next: bench app-migrator generate-plan")

    except Exception as e:
        click.echo(f"❌ Analysis error: {e}")
        import traceback
        traceback.print_exc()
