"""
🏗️ App Migrator - Enterprise Multi-Bench Migration System
Main module with proper command registration
"""

import click
import frappe
import os
import subprocess
from frappe.utils import get_sites
from pathlib import Path

__version__ = "4.0.0"
app_name = "app_migrator"

print(f"🚀 App Migrator v{__version__}")

# ========== MULTI-BENCH FUNCTIONS ==========
def detect_available_benches():
    """Detect all available benches"""
    benches = []
    frappe_home = os.path.expanduser('~')
    
    for item in os.listdir(frappe_home):
        if item.startswith('frappe-bench') and os.path.isdir(os.path.join(frappe_home, item)):
            benches.append(item)
    
    return sorted(benches)

def get_bench_apps(bench_path):
    """Get installed apps from a bench"""
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
        return sorted(apps)
    except Exception as e:
        print(f"   ❌ Error getting apps: {e}")
        return []

def multi_bench_analysis():
    """Step 52-1: Multi-bench ecosystem analysis"""
    print("🔍 Step 52-1: MULTI-BENCH ECOSYSTEM ANALYSIS")
    print("=" * 55)
    
    benches = detect_available_benches()
    print(f"📋 Found {len(benches)} benches:")
    
    total_apps = 0
    for bench in benches:
        apps = get_bench_apps(f"/home/frappe/{bench}")
        total_apps += len(apps)
        print(f"\n📦 {bench}:")
        print(f"   Apps: {len(apps)}")
        if apps:
            print(f"   {apps}")
        else:
            print(f"   💡 Empty bench")
    
    print(f"\n📈 SYSTEM SUMMARY: {len(benches)} benches, {total_apps} total apps")
    return benches

def smart_migration_recommendation():
    """Step 52-2: Smart migration recommendations"""
    print("🧠 Step 52-2: SMART MIGRATION RECOMMENDATION")
    print("=" * 55)
    
    benches = detect_available_benches()
    if len(benches) < 2:
        print("❌ Need at least 2 benches for migration")
        print("💡 Create new bench: cd /home/frappe/ && bench init frappe-bench-new")
        return
    
    # Get bench info
    bench_info = {}
    for bench in benches:
        apps = get_bench_apps(f"/home/frappe/{bench}")
        bench_info[bench] = {
            'apps': apps,
            'app_count': len(apps)
        }
    
    # Find optimal migration path
    source_bench = max(bench_info.keys(), key=lambda x: bench_info[x]['app_count'])
    target_bench = min(bench_info.keys(), key=lambda x: bench_info[x]['app_count'])
    
    print(f"🎯 RECOMMENDED MIGRATION PATH:")
    print(f"   🚀 SOURCE: {source_bench} ({bench_info[source_bench]['app_count']} apps)")
    print(f"   🎯 TARGET: {target_bench} ({bench_info[target_bench]['app_count']} apps)")
    
    source_apps = set(bench_info[source_bench]['apps'])
    target_apps = set(bench_info[target_bench]['apps'])
    migratable = source_apps - target_apps
    
    if migratable:
        custom_apps = [app for app in migratable if app not in ['frappe', 'erpnext']]
        if custom_apps:
            print(f"\n📦 RECOMMENDED APPS TO MIGRATE:")
            for app in custom_apps[:3]:  # Top 3
                print(f"   • {app}")
            
            print(f"\n💡 QUICK MIGRATION COMMAND:")
            print(f"   cd /home/frappe/{target_bench}")
            print(f"   bench get-app {custom_apps[0]} /home/frappe/{source_bench}/apps/{custom_apps[0]}")
            print(f"   bench --site [site_name] install-app {custom_apps[0]}")
    else:
        print(f"\n✅ All apps already synchronized")

# ========== MAIN COMMAND HANDLER ==========
@click.command('migrate-app')
@click.argument('action')
@click.argument('source_app', required=False)
@click.argument('target_app', required=False)
@click.option('--modules', help='Specific modules to migrate')
@click.option('--site', help='Specific site to use')
def migrate_app(action, source_app=None, target_app=None, modules=None, site=None):
    """🚀 App Migrator - Enterprise Multi-Bench Migration System"""
    
    print(f"🚀 App Migrator: {action}")
    
    # ========== MULTI-BENCH COMMANDS ==========
    if action == 'multi-bench-analysis':
        multi_bench_analysis()
        
    elif action == 'smart-recommendation':
        smart_migration_recommendation()
        
    elif action == 'list-benches':
        benches = detect_available_benches()
        print("🏗️ AVAILABLE BENCHES:")
        for i, bench in enumerate(benches, 1):
            print(f"   {i}. {bench}")
            
    elif action == 'bench-apps':
        if not source_app:
            print("❌ Please specify bench name: bench migrate-app bench-apps <bench_name>")
            return
            
        apps = get_bench_apps(f"/home/frappe/{source_app}")
        print(f"📦 APPS IN {source_app}:")
        for i, app in enumerate(apps, 1):
            print(f"   {i}. {app}")
        print(f"   Total: {len(apps)} apps")
    
    elif action == 'cross-bench-analysis':
        print("🔀 CROSS-BENCH MIGRATION ANALYSIS")
        benches = detect_available_benches()
        if len(benches) >= 2:
            source = benches[0]
            target = benches[1]
            print(f"   Analyzing: {source} → {target}")
            # Add detailed analysis here
    
    # ========== SITE COMMANDS ==========
    elif action == 'db-info':
        print("🔍 DATABASE INFORMATION")
        print("=" * 30)
        sites = get_sites()
        for site_name in sites:
            try:
                frappe.init(site_name)
                frappe.connect(site=site_name)
                print(f"\n🌐 {site_name}:")
                print(f"   Database: {frappe.conf.db_name}")
                print(f"   Host: {frappe.conf.db_host}")
                apps = frappe.get_installed_apps()
                print(f"   Apps: {len(apps)}")
                frappe.db.close()
            except Exception as e:
                print(f"   Error: {e}")
                
    elif action == 'discover-sites':
        print("🔍 DISCOVERING SITES AND APPS")
        sites = get_sites()
        print(f"📋 Found {len(sites)} sites: {sites}")
        for site_name in sites:
            print(f"\n🌐 {site_name}:")
            try:
                frappe.init(site_name)
                frappe.connect(site=site_name)
                apps = frappe.get_installed_apps()
                print(f"   Apps: {len(apps)} - {apps}")
                frappe.db.close()
            except Exception as e:
                print(f"   Error: {e}")
    
    elif action == 'list-sites':
        sites = get_sites()
        print("🌐 AVAILABLE SITES:")
        for i, site in enumerate(sites, 1):
            print(f"   {i}. {site}")
            
    elif action == 'show-apps':
        if not source_app:
            print("❌ Please specify a site: bench migrate-app show-apps <site_name>")
            return
            
        try:
            frappe.init(source_app)
            frappe.connect(site=source_app)
            apps = frappe.get_installed_apps()
            print(f"📦 APPS IN {source_app}:")
            for i, app in enumerate(apps, 1):
                print(f"   {i}. {app}")
            print(f"   Total: {len(apps)} apps")
            frappe.db.close()
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # ========== HELP ==========
    else:
        print(f"❌ Unknown action: {action}")
        print("\n📋 MULTI-BENCH COMMANDS:")
        print("   multi-bench-analysis    - Analyze all benches")
        print("   smart-recommendation    - Get migration recommendations")
        print("   list-benches            - List available benches")
        print("   bench-apps <bench>      - Show apps in bench")
        print("   cross-bench-analysis    - Cross-bench migration analysis")
        print("\n📋 SITE COMMANDS:")
        print("   db-info                 - Database information")
        print("   discover-sites          - Discover sites and apps")
        print("   list-sites              - List available sites")
        print("   show-apps <site>        - Show apps in site")

# ========== COMMAND REGISTRATION ==========
# This is CRITICAL - Frappe looks for this list
commands = [migrate_app]

print("✅ App Migrator commands registered successfully!")
