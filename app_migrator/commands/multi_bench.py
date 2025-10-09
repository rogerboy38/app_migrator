"""
🏗️ Multi-Bench Migration Commands
Handles cross-bench migration analysis and execution
"""

import click
import frappe
import os
import subprocess
from pathlib import Path

def detect_available_benches():
    """Detect all available benches in the system"""
    benches = []
    frappe_home = os.path.expanduser('~')
    
    for item in os.listdir(frappe_home):
        if item.startswith('frappe-bench') and os.path.isdir(os.path.join(frappe_home, item)):
            benches.append(item)
    
    return sorted(benches)  # Sort for consistent ordering

def get_bench_apps(bench_path):
    """Get installed apps from a specific bench"""
    try:
        result = subprocess.run(
            f"cd {bench_path} && bench version",
            shell=True, capture_output=True, text=True, timeout=30
        )
        lines = result.stdout.strip().split('\n')
        apps = []
        for line in lines:
            if ' ' in line and not line.startswith('✅'):
                app = line.split()[0]
                apps.append(app)
        return sorted(apps)  # Sort for consistent output
    except Exception as e:
        print(f"   ❌ Error getting apps from {bench_path}: {e}")
        return []

def multi_bench_analysis():
    """Step 51-1: Comprehensive multi-bench analysis"""
    print("🔍 Step 51-1: MULTI-BENCH ECOSYSTEM ANALYSIS")
    print("=" * 55)
    
    benches = detect_available_benches()
    print(f"📋 Found {len(benches)} benches in system:")
    
    bench_info = {}
    total_apps = 0
    
    for bench in benches:
        bench_path = os.path.join(os.path.expanduser('~'), bench)
        apps = get_bench_apps(bench_path)
        
        bench_info[bench] = {
            'path': bench_path,
            'apps': apps,
            'app_count': len(apps)
        }
        
        total_apps += len(apps)
        print(f"\n📦 {bench}:")
        print(f"   📍 Path: {bench_path}")
        print(f"   📊 Apps: {len(apps)}")
        if apps:
            print(f"   📋 App List: {', '.join(apps)}")
        else:
            print(f"   💡 Status: Empty bench")
    
    print(f"\n📈 SYSTEM SUMMARY: {len(benches)} benches, {total_apps} total apps")
    return bench_info

def smart_migration_recommendation():
    """Step 51-2: Intelligent migration recommendations"""
    print("🧠 Step 51-2: SMART MIGRATION RECOMMENDATION ENGINE")
    print("=" * 55)
    
    bench_info = multi_bench_analysis()
    
    if len(bench_info) < 2:
        print("❌ Need at least 2 benches for cross-bench migration")
        print("💡 Create new bench: cd /home/frappe/ && bench init frappe-bench-new")
        return
    
    # Find optimal source (most apps) and target (cleanest)
    source_bench = max(bench_info.keys(), key=lambda x: bench_info[x]['app_count'])
    target_bench = min(bench_info.keys(), key=lambda x: bench_info[x]['app_count'])
    
    # Avoid recommending empty source
    if bench_info[source_bench]['app_count'] == 0:
        print("❌ No apps found in source benches")
        return
    
    print(f"\n🎯 OPTIMAL MIGRATION PATH:")
    print(f"   🚀 SOURCE: {source_bench}")
    print(f"      • {bench_info[source_bench]['app_count']} apps available")
    print(f"      • Path: {bench_info[source_bench]['path']}")
    
    print(f"   🎯 TARGET: {target_bench}")
    print(f"      • {bench_info[target_bench]['app_count']} apps currently")
    print(f"      • Path: {bench_info[target_bench]['path']}")
    
    source_apps = set(bench_info[source_bench]['apps'])
    target_apps = set(bench_info[target_bench]['apps'])
    
    migratable_apps = source_apps - target_apps
    
    if migratable_apps:
        print(f"\n📦 MIGRATION CANDIDATES ({len(migratable_apps)} apps):")
        
        # Categorize apps
        core_apps = [app for app in migratable_apps if app in ['frappe', 'erpnext']]
        custom_apps = [app for app in migratable_apps if app not in ['frappe', 'erpnext']]
        
        if custom_apps:
            print(f"   🎯 HIGH-VALUE CUSTOM APPS:")
            for i, app in enumerate(custom_apps, 1):
                print(f"      {i}. {app}")
        
        if core_apps:
            print(f"   🔧 CORE FRAMEWORK APPS:")
            for app in core_apps:
                print(f"      • {app}")
        
        # Top recommendation
        if custom_apps:
            recommended_app = custom_apps[0]
            print(f"\n💡 QUICK START - Migrate '{recommended_app}':")
            print(f"   cd {bench_info[target_bench]['path']}")
            print(f"   bench get-app {recommended_app} {bench_info[source_bench]['path']}/apps/{recommended_app}")
            print(f"   bench --site [site_name] install-app {recommended_app}")
        
    else:
        print(f"\n✅ SYNC STATUS: All apps already synchronized")
        print(f"   No migration needed between {source_bench} and {target_bench}")
    
    return migratable_apps

def cross_bench_migration_analysis(source_bench=None, target_bench=None):
    """Step 51-3: Specific cross-bench migration analysis"""
    print("🔀 Step 51-3: CROSS-BENCH MIGRATION ANALYSIS")
    print("=" * 55)
    
    bench_info = multi_bench_analysis()
    
    if len(bench_info) < 2:
        print("❌ Need at least 2 benches")
        return
    
    benches = list(bench_info.keys())
    
    # Use provided benches or auto-select
    if not source_bench:
        source_bench = benches[0]
    if not target_bench:
        target_bench = benches[1]
    
    if source_bench not in bench_info or target_bench not in bench_info:
        print(f"❌ Invalid bench selection")
        return
    
    print(f"\n🔀 ANALYZING: {source_bench} → {target_bench}")
    print(f"   Source: {bench_info[source_bench]['app_count']} apps")
    print(f"   Target: {bench_info[target_bench]['app_count']} apps")
    
    source_apps = set(bench_info[source_bench]['apps'])
    target_apps = set(bench_info[target_bench]['apps'])
    
    migratable = source_apps - target_apps
    common = source_apps & target_apps
    
    print(f"\n📊 MIGRATION ANALYSIS:")
    print(f"   ✅ Common apps: {len(common)}")
    print(f"   📦 Migratable apps: {len(migratable)}")
    
    if migratable:
        print(f"\n🎯 MIGRATION TARGETS:")
        for app in sorted(migratable):
            print(f"   • {app}")
    
    return {
        'source_bench': source_bench,
        'target_bench': target_bench,
        'migratable_apps': migratable,
        'common_apps': common
    }

def get_bench_sites(bench_path):
    """Get sites from a bench (if needed by other modules)"""
    try:
        result = subprocess.run(
            f"cd {bench_path} && bench list-sites 2>/dev/null || ls sites/",
            shell=True, capture_output=True, text=True
        )
        sites = [line.strip() for line in result.stdout.split('\n') if line.strip()]
        return sites
    except:
        return []

def get_bench_info(bench_name):
    """Get comprehensive info about a bench"""
    bench_path = f"/home/frappe/{bench_name}"
    if not os.path.exists(bench_path):
        return None
    
    return {
        'path': bench_path,
        'apps': get_bench_apps(bench_path),
        'sites': get_bench_sites(bench_path),
        'exists': True
    }
