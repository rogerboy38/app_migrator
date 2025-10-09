"""
🏗️ App Migrator - Enterprise Multi-Bench Migration System
Main module with proper command registration
"""

import click
import frappe
import os
import subprocess
import time
from frappe.utils import get_sites
from pathlib import Path
from datetime import datetime

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

<<<<<<< HEAD
=======
def cross_bench_migration_analysis():
    """Step 3: Cross-bench migration analysis"""
    print("🔀 CROSS-BENCH MIGRATION ANALYSIS")
    print("=" * 50)
    
    benches = detect_available_benches()
    if len(benches) < 2:
        print("❌ Need at least 2 benches")
        return
    
    source_bench = benches[0]
    target_bench = benches[1]
    
    print(f"🔀 MIGRATION PATH: {source_bench} → {target_bench}")
    
    source_apps = set(get_bench_apps(f"/home/frappe/{source_bench}"))
    target_apps = set(get_bench_apps(f"/home/frappe/{target_bench}"))
    
    migratable = source_apps - target_apps
    common = source_apps & target_apps
    
    print(f"\n📊 MIGRATION ANALYSIS:")
    print(f"   ✅ Common apps: {len(common)}")
    print(f"   📦 Migratable apps: {len(migratable)}")
    
    if migratable:
        print(f"\n🎯 MIGRATION TARGETS:")
        for app in sorted(migratable):
            print(f"   • {app}")

# ========== PROGRESS TRACKING FUNCTIONS ==========
def monitor_directory_creation(app_name, timeout=600, check_interval=5):
    """Monitor app directory creation with progress"""
    target_path = f"/home/frappe/frappe-bench/apps/{app_name}"
    print(f"👀 Monitoring directory: {target_path}")
    
    for i in range(timeout // check_interval):
        if os.path.exists(target_path):
            size = get_directory_size(target_path)
            print(f"✅ Directory created: {app_name} ({size})")
            return True
        
        # Progress indicator
        dots = "." * (i % 4)
        print(f"\r⏳ Waiting for {app_name} directory{dots} ({i*check_interval}s)", end="", flush=True)
        time.sleep(check_interval)
    
    print(f"\r❌ Timeout: {app_name} directory not created after {timeout}s")
    return False

def get_directory_size(path):
    """Get human-readable directory size"""
    try:
        result = subprocess.run(
            f"du -sh {path}", 
            shell=True, capture_output=True, text=True
        )
        return result.stdout.strip().split()[0]
    except:
        return "unknown size"

def run_command_with_progress(command, description, timeout=600):
    """Run command with progress feedback"""
    print(f"🔄 {description}...")
    
    try:
        # Start process
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Monitor process with timeout
        start_time = time.time()
        while process.poll() is None:
            if time.time() - start_time > timeout:
                process.terminate()
                return False, f"Timeout after {timeout}s"
            
            # Show progress indicator
            elapsed = int(time.time() - start_time)
            print(f"\r⏳ {description}... ({elapsed}s)", end="", flush=True)
            time.sleep(2)
        
        # Get result
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            print(f"\r✅ {description} completed!")
            return True, stdout
        else:
            print(f"\r❌ {description} failed!")
            return False, stderr
            
    except Exception as e:
        return False, str(e)

def validate_migration_readiness(app_name):
    """Check if migration is possible"""
    # Check if app already exists in target
    target_path = f"/home/frappe/frappe-bench/apps/{app_name}"
    if os.path.exists(target_path):
        print(f"❌ {app_name} already exists in target bench")
        return False
    
    # Check disk space
    try:
        result = subprocess.run(
            "df /home/frappe --output=avail | tail -1",
            shell=True, capture_output=True, text=True
        )
        free_space = int(result.stdout.strip()) / 1024 / 1024  # Convert to GB
        if free_space < 2:  # Less than 2GB free
            print(f"❌ Insufficient disk space: {free_space:.1f}GB free")
            return False
    except:
        pass  # Continue if disk check fails
    
    return True

>>>>>>> b44e085 (STEP 60-1: Pre-progress-bar implementation)
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
    
    # ========== ENTERPRISE SESSION COMMANDS ==========
    elif action == 'start-session':
        try:
            from ..utils.session import MigrationSession
            
            if not source_app:  # Using source_app as session name
                print("❌ Please specify session name: bench migrate-app start-session <session_name>")
                return
                
            session = MigrationSession(source_app)
            session_id = session.save()
            
            if session_id:
                print(f"✅ ENTERPRISE SESSION STARTED: {source_app}")
                print(f"📁 Session ID: {session_id}")
                print(f"💾 Storage: {session.session_file}")
                print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"🔧 Status: Active")
                print(f"\n💡 Next: Use this session for migration operations")
            else:
                print("❌ Failed to create session")
                
        except Exception as e:
            print(f"❌ Session creation failed: {e}")
            
    elif action == 'session-status':
        try:
            from ..utils.session import load_session, get_session_by_name
            if not source_app:
                print("❌ Please specify session ID or name: bench migrate-app session-status <session_id_or_name>")
                return
                
            # Try loading by session_id first, then by name
            session_data = load_session(source_app)
            if not session_data:
                session_data = get_session_by_name(source_app)
                
            if session_data:
                metadata = session_data["metadata"]
                progress = session_data["progress"]
                migration = session_data["migration_data"]
                
                print(f"📊 ENTERPRISE SESSION STATUS")
                print("=" * 50)
                print(f"🏷️  Name: {metadata['name']}")
                print(f"🆔 ID: {metadata['session_id']}")
                print(f"📈 Status: {metadata['status'].upper()}")
                print(f"🔧 Phase: {metadata['current_phase']}")
                print(f"⏰ Started: {metadata['start_time']}")
                
                # ENHANCED: Progress calculation with visual bar
                completed_ops = len([op for op in progress['completed_operations'] if op['status'] == 'completed'])
                total_ops = len(progress.get('planned_operations', [])) or len(progress['completed_operations'])
                success_rate = (completed_ops/total_ops)*100 if total_ops > 0 else 0
                
                # Progress bar visualization
                progress_bar_length = 20
                filled_length = int(progress_bar_length * completed_ops // total_ops) if total_ops > 0 else 0
                bar = '█' * filled_length + '░' * (progress_bar_length - filled_length)
                
                print(f"\n📈 PROGRESS: [{bar}] {completed_ops}/{total_ops} ({success_rate:.1f}%)")
                
                if progress['current_operation']:
                    print(f"🔄 CURRENT: {progress['current_operation']}")
                
                # Migration progress
                if migration['apps_to_migrate']:
                    completed_apps = len(migration['completed_apps'])
                    total_apps = len(migration['apps_to_migrate'])
                    app_success_rate = (completed_apps/total_apps)*100 if total_apps > 0 else 0
                    
                    print(f"\n🚀 MIGRATION PROGRESS:")
                    print(f"   • Apps: {completed_apps}/{total_apps} completed ({app_success_rate:.1f}%)")
                    print(f"   • Remaining: {total_apps - completed_apps}")
                    
                    # Show current app being processed
                    if migration.get('current_app'):
                        print(f"   • Processing: {migration['current_app']}")
                    
                # Recent operations
                if progress['completed_operations']:
                    print(f"\n🕐 RECENT OPERATIONS:")
                    recent_ops = progress['completed_operations'][-5:]  # Last 5 operations
                    for op in recent_ops:
                        status_icon = "✅" if op['status'] == 'completed' else "❌"
                        print(f"   {status_icon} {op['operation']} - {op['timestamp'][11:19]}")
                        
            else:
                print(f"❌ Session not found: {source_app}")
                print("💡 Available sessions: bench migrate-app list-sessions")
                
        except Exception as e:
            print(f"❌ Session status check failed: {e}")
            
    elif action == 'list-sessions':
        try:
            from ..utils.session import list_all_sessions
            sessions = list_all_sessions()
            
            if sessions:
                print(f"📁 ENTERPRISE MIGRATION SESSIONS")
                print("=" * 50)
                
                for session in sessions:
                    metadata = session["data"]["metadata"]
                    progress = session["data"]["progress"]
                    
                    completed_ops = len([op for op in progress['completed_operations'] if op['status'] == 'completed'])
                    total_ops = len(progress['completed_operations'])
                    
                    status_icon = "🟢" if metadata['status'] == 'active' else "🔵" if metadata['status'] == 'completed' else "🔴"
                    
                    print(f"\n{status_icon} {metadata['name']}")
                    print(f"   🆔 {metadata['session_id']}")
                    print(f"   📊 {completed_ops}/{total_ops} ops • {metadata['status']}")
                    print(f"   ⏰ {metadata['start_time'][:19]}")
                    
            else:
                print("📭 No migration sessions found")
                print("💡 Create one: bench migrate-app start-session <name>")
                
        except Exception as e:
            print(f"❌ Session listing failed: {e}")
    
    # ========== MIGRATION COMMANDS ==========
    elif action == 'clone-app':
        if not source_app:  # Using source_app as app_name
            print("❌ Please specify app name: bench migrate-app clone-app <app_name>")
            return
            
        # Handle session parameter (using --site as temporary session ID)
        session_id = None
        if site:  # Using --site option for session ID temporarily
            session_id = site
            
        print(f"🚀 CLONING APP (PROGRESS MODE): {source_app}")
        
        # Enhanced progress tracking
        print(f"🔍 Validating migration readiness for {source_app}...")
        
        # Check if app already exists
        target_path = f"/home/frappe/frappe-bench/apps/{source_app}"
        if os.path.exists(target_path):
            print(f"❌ {source_app} already exists in target bench")
            if session_id:
                from ..utils.session import update_session_progress
                update_session_progress(session_id, f"clone_{source_app}", "failed", "App already exists")
            return False
        
        # Execute with progress tracking
        try:
            # Step 1: Get app
            print(f"📥 Downloading {source_app}...")
            success, output = run_command_with_progress(
                f"cd /home/frappe/frappe-bench && bench get-app {source_app}",
                f"Downloading {source_app}",
                timeout=600
            )
            
            if not success:
                print(f"❌ Download failed: {output}")
                if session_id:
                    from ..utils.session import update_session_progress
                    update_session_progress(session_id, f"clone_{source_app}", "failed", f"Download failed: {output}")
                return False
            
            # Step 2: Monitor directory creation
            print(f"👀 Monitoring {source_app} installation...")
            if not monitor_directory_creation(source_app):
                if session_id:
                    from ..utils.session import update_session_progress
                    update_session_progress(session_id, f"clone_{source_app}", "failed", "Directory not created")
                return False
            
            # Step 3: Install app
            print(f"⚙️ Installing {source_app} to sites...")
            success, output = run_command_with_progress(
                f"cd /home/frappe/frappe-bench && bench install-app {source_app}",
                f"Installing {source_app}",
                timeout=300
            )
            
            if success:
                print(f"✅ {source_app} migration completed successfully!")
                if session_id:
                    from ..utils.session import update_session_progress
                    update_session_progress(session_id, f"clone_{source_app}", "completed")
                return True
            else:
                print(f"❌ Installation failed: {output}")
                if session_id:
                    from ..utils.session import update_session_progress
                    update_session_progress(session_id, f"clone_{source_app}", "failed", f"Installation failed: {output}")
                return False
                
        except Exception as e:
            print(f"❌ Clone operation failed: {e}")
            if session_id:
                from ..utils.session import update_session_progress
                update_session_progress(session_id, f"clone_{source_app}", "failed", str(e))
            return False
    
    # ========== HELP ==========
    else:
        print(f"❌ Unknown action: {action}")
        print("\n📋 MULTI-BENCH COMMANDS:")
        print("   multi-bench-analysis    - Analyze all benches")
        print("   smart-recommendation    - Get migration recommendations")
        print("   list-benches            - List available benches")
        print("   bench-apps <bench>      - Show apps in bench")
<<<<<<< HEAD
        print("   cross-bench-analysis    - Cross-bench migration analysis")
=======
        
>>>>>>> b44e085 (STEP 60-1: Pre-progress-bar implementation)
        print("\n📋 SITE COMMANDS:")
        print("   db-info                 - Database information")
        print("   discover-sites          - Discover sites and apps")
        print("   list-sites              - List available sites")
        print("   show-apps <site>        - Show apps in site")
        
        print("\n🎯 ENTERPRISE SESSION COMMANDS:")
        print("   start-session <name>    - Start new migration session")
        print("   session-status <id>     - Check session status with details")
        print("   list-sessions           - List all sessions")
        
        print("\n🚀 MIGRATION COMMANDS:")
        print("   clone-app <app_name>    - Clone app between benches")

# ========== COMMAND REGISTRATION ==========
# This is CRITICAL - Frappe looks for this list
commands = [migrate_app]

print("✅ App Migrator commands registered successfully!")
