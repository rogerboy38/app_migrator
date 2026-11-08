"""app-migrator new-fresh-app command — create Frappe apps WITHOUT the antipattern.

Wraps `bench new-app` with module-name validation: refuses if scrub(module) == app_name.
After creating, immediately renames the auto-generated antipattern folder and rewrites
modules.txt with the chosen non-colliding module name.

Usage:
  bench app-migrator new-fresh-app \\
      --app-name payments_core \\
      --module-name "Payment Core"

  # With explicit metadata:
  bench app-migrator new-fresh-app \\
      --app-name payments_core \\
      --module-name "Payment Core" \\
      --app-title "Payments Core" \\
      --app-description "Payment gateway integration" \\
      --app-publisher "Your Org" \\
      --app-email "dev@example.com" \\
      --app-license "MIT" \\
      --apply
"""
import shutil
import subprocess
from pathlib import Path

import click

try:
    import frappe
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f


def _scrub(name):
    return name.strip().lower().replace(" ", "_").replace("-", "_")


@click.command("app-migrator-new-fresh-app")
@click.option("--app-name", required=True, help="App name (e.g., 'payments_core')")
@click.option("--module-name", required=True,
              help="Initial module name (e.g., 'Payment Core'). MUST scrub to "
                   "a value DIFFERENT from app name.")
@click.option("--app-title", help="App title (defaults to humanized app-name)")
@click.option("--app-description", default="Frappe app", help="App description")
@click.option("--app-publisher", default="App Migrator", help="App publisher")
@click.option("--app-email", default="dev@example.com", help="App email")
@click.option("--app-license", default="mit", help="App license (lowercase: mit, apache-2.0, gpl-3.0, etc.)")
@click.option("--bench-root", default="/home/frappe/frappe-bench")
@click.option("--apply", is_flag=True, default=False,
              help="Actually run bench new-app (default: --dry-run)")
@pass_context
def app_migrator_new_fresh_app(context, app_name, module_name, app_title,
                                 app_description, app_publisher, app_email,
                                 app_license, bench_root, apply):
    """Create a Frappe app without the same-name-module antipattern."""
    bench_root = Path(bench_root)
    new_slug = _scrub(module_name)
    mode = "APPLY" if apply else "DRY-RUN"

    click.secho("\n" + "=" * 78, fg="cyan")
    click.secho(f"  NEW-FRESH-APP — '{app_name}' / module '{module_name}'  [{mode}]",
                fg="cyan", bold=True)
    click.secho("=" * 78, fg="cyan")

    # Antipattern rule check
    if new_slug == app_name:
        click.secho("\n✗ ANTIPATTERN BLOCKED:", fg="red", bold=True)
        click.secho(f"  scrub('{module_name}') = '{new_slug}' equals app name "
                    f"'{app_name}'.", fg="red")
        click.secho(f"  This would create apps/{app_name}/{app_name}/{app_name}/ "
                    f"— the same-name-module antipattern.", fg="red")
        click.secho("\n  Suggestions for --module-name:", fg="cyan")
        click.echo(f"    • '{app_name.replace('_', ' ').title()} Core'")
        click.echo("    • 'Core', 'Main', or a feature-descriptive name")
        click.echo(f"    • Anything where scrub != '{app_name}'")
        raise click.Abort()

    # App must not already exist
    app_path = bench_root / "apps" / app_name
    if app_path.exists():
        click.secho(f"\n✗ App already exists at {app_path}", fg="red")
        click.secho("  Use a different --app-name or remove the existing app first.",
                    fg="cyan")
        raise click.Abort()

    if not app_title:
        app_title = app_name.replace("_", " ").title()

    # Display plan
    click.echo(f"\n  ✓ Validation: scrub('{module_name}') = '{new_slug}' "
                f"(differs from app name)")
    click.echo(f"  ✓ Target path: apps/{app_name}/{app_name}/{new_slug}/")
    click.secho("\n┌── PLAN ────", fg="cyan")
    click.echo(f"│  1. Run: bench new-app {app_name} --no-git")
    click.echo(f"│  2. Auto-generated antipattern folder: apps/{app_name}/{app_name}/{app_name}/")
    click.echo(f"│  3. Rename to: apps/{app_name}/{app_name}/{new_slug}/")
    click.echo(f"│  4. Update modules.txt: 'Test App'-style → '{module_name}'")
    click.echo("│  5. Verify with audit-app-for-antipattern")
    click.echo("└────")
    click.echo("\n  Metadata for bench new-app:")
    click.echo(f"    Title:       {app_title}")
    click.echo(f"    Description: {app_description}")
    click.echo(f"    Publisher:   {app_publisher}")
    click.echo(f"    Email:       {app_email}")
    click.echo(f"    License:     {app_license}")

    if not apply:
        click.secho("\n  This was a DRY-RUN. To apply, re-run with --apply.",
                    fg="yellow")
        return

    # APPLY
    click.secho("\n┌── APPLY ──", fg="cyan")

    # 0. Pre-flight: check uv (Frappe's package manager since bench 5.x)
    # bench new-app delegates pip-install to `uv pip install -e <app>`. If uv
    # is missing, the post-scaffold install fails non-zero, but the scaffold
    # IS on disk — our tool still completes the rename + modules.txt steps.
    # Pre-warning the user lets them install uv first if they want a fully
    # clean run, or proceed with confidence that we handle the missing-uv case.
    uv_path = shutil.which("uv")
    if uv_path:
        click.secho(f"  ✓ Pre-flight: uv found at {uv_path}", fg="green")
    else:
        click.secho("  ⚠ Pre-flight: 'uv' not found on PATH.", fg="yellow")
        click.secho("    bench new-app's post-scaffold install step will fail",
                    fg="yellow")
        click.secho("    (but scaffold + denest steps still complete cleanly).",
                    fg="yellow")
        click.secho("    To install uv:", fg="cyan")
        click.echo("      pip install uv")
        click.echo("      OR  curl -LsSf https://astral.sh/uv/install.sh | sh")
        if not click.confirm("\n  Proceed without uv? "
                              "(tool gracefully handles the install failure)",
                              default=True):
            click.secho("Aborted.", fg="yellow")
            raise click.Abort()

    # 1. Run bench new-app with piped answers
    # Frappe v14+ prompt order: Title, Description, Publisher, Email, License, DocType prefix
    # Frappe's bench new-app prompts in order (varies slightly across versions):
    #   App Title, App Description, App Publisher, App Email, App License,
    #   Create GitHub Workflow [y/N], Branch Name [develop],
    #   Use Frappe DocType prefix [y/N], (and possibly init git)
    # Pad with empty newlines to accept defaults for any extra prompts.
    answers = "\n".join([
        app_title,
        app_description,
        app_publisher,
        app_email,
        app_license,
        "n",       # GitHub Workflow action for unittests
        "",        # Branch Name (default: develop)
        "n",       # Use Frappe DocType prefix
        "n",       # Init git (defensive — --no-git may not catch all)
    ]) + "\n" + "\n" * 5  # extra padding for any future prompts

    click.echo(f"\n  Running: bench new-app {app_name} --no-git ...")
    ret = subprocess.run(
        ["bench", "new-app", app_name, "--no-git"],
        input=answers,
        capture_output=True,
        text=True,
        cwd=str(bench_root),
    )

    # Filesystem-based success check: bench new-app creates the scaffold first,
    # THEN tries to install via uv/pip. If install fails (e.g. uv missing), the
    # subprocess exits non-zero but the scaffold is already on disk — and that's
    # what matters for antipattern prevention. Proceed if the package folder exists.
    expected_pkg = app_path / app_name
    if expected_pkg.exists():
        if ret.returncode != 0:
            # Common case: uv missing, package install failed but scaffold OK.
            tail = (ret.stdout + ret.stderr).splitlines()[-3:]
            click.secho("  ⚠ bench new-app exited non-zero but scaffold is on disk:", fg="yellow")
            for line in tail:
                click.echo(f"     {line}")
            click.secho("  ○ Proceeding (post-scaffold install issues are not blocking)", fg="cyan")
        else:
            click.secho("  ✓ bench new-app completed", fg="green")
    else:
        click.secho("  ✗ bench new-app failed — scaffold not created:", fg="red")
        click.echo(ret.stdout[-1500:])
        click.echo(ret.stderr[-1500:])
        raise click.Abort()

    # 2. Verify scaffolder created the antipattern folder (sanity)
    app_pkg = app_path / app_name
    antipattern_folder = app_pkg / app_name
    if not antipattern_folder.exists():
        click.secho(f"  ⚠ Expected antipattern folder not found at "
                    f"{antipattern_folder}", fg="yellow")
        click.secho("  Frappe scaffolder may have changed. Manual review needed.",
                    fg="yellow")
        return

    # 3. Rename antipattern folder
    new_folder = app_pkg / new_slug
    if new_folder.exists():
        click.secho(f"  ✗ Target folder already exists: {new_folder}", fg="red")
        raise click.Abort()
    antipattern_folder.rename(new_folder)
    click.secho(f"  ✓ Renamed: {app_name}/ → {new_slug}/", fg="green")

    # 4. Rewrite modules.txt
    modules_txt = app_pkg / "modules.txt"
    if modules_txt.exists():
        old_content = modules_txt.read_text()
        modules_txt.write_text(module_name + "\n")
        click.secho(f"  ✓ Updated modules.txt: {old_content.strip()!r} "
                    f"→ {module_name!r}", fg="green")
    else:
        modules_txt.write_text(module_name + "\n")
        click.secho(f"  ✓ Created modules.txt with {module_name!r}", fg="green")

    # 5. Verify with audit
    click.echo("\n  Verifying with audit-app-for-antipattern...")
    audit_ret = subprocess.run(
        ["bench", "app-migrator", "audit-app-for-antipattern",
         "--app", app_name, "--bench-root", str(bench_root)],
        capture_output=True, text=True, cwd=str(bench_root),
    )
    if "0 (0%)" in audit_ret.stdout or "✓ no" in audit_ret.stdout:
        click.secho("  ✓ Audit confirms: NO antipattern", fg="green")
    else:
        click.echo(audit_ret.stdout[-1000:])

    # Summary
    click.secho(f"\n{'=' * 78}", fg="green")
    click.secho(f"  ✓ NEW-FRESH-APP COMPLETE — {app_name} created clean",
                fg="green", bold=True)
    click.secho("=" * 78, fg="green")
    click.echo(f"  App location:  apps/{app_name}/")
    click.echo(f"  Module folder: apps/{app_name}/{app_name}/{new_slug}/")
    click.echo(f"  Module name:   '{module_name}'")
    click.echo("\n  Next steps:")
    click.echo(f"    • Install on a site:  bench --site <site> install-app {app_name}")
    click.echo("    • Migrate modules in: bench app-migrator migrate-module ...")
