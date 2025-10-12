#!/usr/bin/env python3
"""
🔍 DIAGNOSTIC COMMANDS
Standalone diagnostic commands to avoid import conflicts
"""

import os
import click

@click.command('repair-bench-apps')
@click.option('--dry-run', is_flag=True, help='Show what would be fixed without applying changes')
def repair_bench_apps(dry_run):
    """Batch repair all apps in bench"""
    from .app_health_scanner import AppHealthScanner
    from .pre_installation_diagnostics import PreInstallationAnalyzer
    
    scanner = AppHealthScanner()
    
    try:
        results = scanner.scan_bench_apps()
        critical_apps = []
        
        for app_name, health in results['apps_health'].items():
            if "error" not in health and health.get("health_score", 0) < 50:
                critical_apps.append((app_name, health))
        
        if not critical_apps:
            print("🎉 No critical apps found needing repair!")
            return
        
        print(f"\n🔧 FOUND {len(critical_apps)} APPS NEEDING REPAIR:")
        for app_name, health in critical_apps:
            print(f"   • {app_name}: {health['health_score']}% health")
        
        if dry_run:
            print("\n💡 This was a dry run. Use without --dry-run to apply fixes.")
            return
        
        if click.confirm(f"\n🚀 Apply fixes to {len(critical_apps)} apps?"):
            for app_name, health in critical_apps:
                app_path = os.path.join(scanner.bench_path, 'apps', app_name)
                analyzer = PreInstallationAnalyzer()
                fix_results = analyzer.auto_fix_app_structure(app_path)
                print(f"✅ {app_name}: Applied {fix_results['total_fixes']} fixes")
            
            print(f"\n🎉 Completed batch repair of {len(critical_apps)} apps!")
            
    except Exception as e:
        print(f"❌ Batch repair failed: {str(e)}")


@click.command('diagnose-app')
@click.argument('app_path')
@click.option('--fix', is_flag=True, help='Attempt to fix issues automatically')
def diagnose_app(app_path, fix):
    """Diagnose app health without installation"""
    from .pre_installation_diagnostics import diagnose_app_function
    return diagnose_app_function(app_path, fix)


@click.command('scan-bench-health')  
def scan_bench_health():
    """Scan health of all apps in bench"""
    from .app_health_scanner import scan_bench_health_function
    return scan_bench_health_function()

@click.command('quick-health-check')
@click.argument('app_name')
def quick_health_check(app_name):
    """Quick health check for a single app"""
    from .app_health_scanner import quick_health_check_function
    return quick_health_check_function(app_name)

def get_commands():
    return [diagnose_app, scan_bench_health, quick_health_check, repair_bench_apps]

