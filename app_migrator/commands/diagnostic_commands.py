#!/usr/bin/env python3
"""
🔍 DIAGNOSTIC COMMANDS - v5.5.0
Pre-installation diagnostics for uninstalled apps
"""

import os
import click
import sys

def diagnose_app_callback(app_path, fix=False):
    """Callback for diagnose-app command"""
    try:
        # Try relative import first
        from .pre_installation_diagnostics import diagnose_app_function
        return diagnose_app_function(app_path, fix)
    except ImportError:
        # Fallback to absolute import
        from pre_installation_diagnostics import diagnose_app_function
        return diagnose_app_function(app_path, fix)

def scan_bench_health_callback():
    """Callback for scan-bench-health command"""
    try:
        # Try relative import first
        from .app_health_scanner import scan_bench_health_function
        return scan_bench_health_function()
    except ImportError:
        # Fallback to absolute import
        from app_health_scanner import scan_bench_health_function
        return scan_bench_health_function()

def quick_health_check_callback(app_name):
    """Callback for quick-health-check command"""
    try:
        # Try relative import first
        from .app_health_scanner import quick_health_check_function
        return quick_health_check_function(app_name)
    except ImportError:
        # Fallback to absolute import
        from app_health_scanner import quick_health_check_function
        return quick_health_check_function(app_name)

def repair_bench_apps_callback(dry_run=False):
    """Callback for repair-bench-apps command"""
    print("🔧 App Migrator V5.5.0: Batch Repair Mode")
    
    try:
        # Try relative imports first
        from .app_health_scanner import AppHealthScanner
        from .pre_installation_diagnostics import PreInstallationAnalyzer
    except ImportError:
        # Fallback to absolute imports
        from app_health_scanner import AppHealthScanner
        from pre_installation_diagnostics import PreInstallationAnalyzer
    
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
