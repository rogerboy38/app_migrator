"""app-migrator audit-app-for-antipattern command — fleet-wide same-name-module audit.

THE RULE: for every entry in <app>/<app>/modules.txt, scrub(entry) must NOT
equal the app name. When it does, the third-level folder collides with the
package name, creating <app>/<app>/<app>/ — the antipattern.
"""
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


@click.command("app-migrator-audit-app-for-antipattern")
@click.option("--app", help="Specific app (default: all installed)")
@click.option("--bench-root", default="/home/frappe/frappe-bench")
@click.option("--output", help="Write report to file (default: stdout)")
@pass_context
def app_migrator_audit_app_for_antipattern(context, app, bench_root, output):
    """Audit installed apps for the same-name-module antipattern."""
    bench_root = Path(bench_root)
    apps_dir = bench_root / "apps"

    if app:
        target_apps = [app]
    else:
        target_apps = sorted(p.name for p in apps_dir.iterdir()
                             if p.is_dir() and not p.name.startswith("."))

    lines = []
    def emit(s=""):
        lines.append(s)

    emit("=" * 95)
    emit("  ANTIPATTERN AUDIT — same-name-module across installed apps")
    emit("=" * 95)
    emit("\n  Rule: scrub(modules.txt entry) MUST NOT equal app name\n")
    emit(f"  {'App':25} {'Module':30} {'AP?':6} {'Folder DTs':>12}")
    emit("-" * 95)

    affected_apps = set()
    total_affected_dts = 0
    all_results = []

    for app_name in target_apps:
        app_path = apps_dir / app_name
        if not app_path.is_dir():
            continue
        pkg = app_path / app_name
        modules_txt = pkg / "modules.txt"
        if not modules_txt.exists():
            continue
        try:
            modules = [m.strip() for m in modules_txt.read_text().splitlines()
                       if m.strip() and not m.startswith("#")]
        except Exception:
            continue

        for module_name in modules:
            scrubbed = _scrub(module_name)
            is_ap = (scrubbed == app_name)
            marker = "⚠ YES" if is_ap else "✓ no"
            dt_count = 0
            if is_ap:
                module_dir = pkg / scrubbed / "doctype"
                if module_dir.exists():
                    for d in module_dir.iterdir():
                        if d.is_dir() and (d / f"{d.name}.json").exists():
                            dt_count += 1
                affected_apps.add(app_name)
                total_affected_dts += dt_count
            all_results.append((app_name, module_name, is_ap, dt_count))
            emit(f"  {app_name:25} {module_name:30} {marker:6} "
                 f"{(dt_count if is_ap else ''):>12}")

    emit("\n" + "=" * 95)
    emit("  FLEET SUMMARY")
    emit("=" * 95)
    total = len({r[0] for r in all_results})
    emit(f"  Apps with at least one module:        {total}")
    emit(f"  Apps with antipattern:                {len(affected_apps)} "
         f"({100*len(affected_apps)//max(total,1)}%)")
    emit(f"  Total DocTypes in antipattern folders: {total_affected_dts}")
    if affected_apps:
        emit(f"\n  Affected apps: {sorted(affected_apps)}")
        emit(f"\n  Fix: bench app-migrator denest-app --app <name> "
             f"--to-module \"<New Module>\" --apply")
    emit("=" * 95)

    text = "\n".join(lines)
    if output:
        Path(output).write_text(text)
        click.echo(f"Report written to {output}")
    else:
        click.echo(text)
