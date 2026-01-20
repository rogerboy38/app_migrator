"""
App Migrator Commands - Enterprise Edition
Version: 9.0.0
Merged: Original analysis + Enterprise multi-bench + Session management
"""

__version__ = "9.0.0"

# ONLY import the main class - no function imports!
from .analysis_tools import AppAnalysis

__all__ = ["AppAnalysis"]

print("✅ App Migrator commands loaded safely")

# Import Payment Security Migrator
from .payment_security_migrator import (
    PaymentSecurityMigrator,
    analyze_payment_security,
    migrate_payment_security,
    generate_security_report
)

__all__.extend([
    "PaymentSecurityMigrator",
    "analyze_payment_security", 
    "migrate_payment_security",
    "generate_security_report"
])

print("✅ Payment Security Migrator added to commands")

# Import Payment Gateway Migrator
try:
    from .payment_gateway_migrator import PaymentGatewayMigrator
    __all__.append("PaymentGatewayMigrator")
    print("✅ Payment Gateway Migrator added to commands")
except ImportError as e:
    print(f"⚠️ Payment Gateway Migrator not available: {e}")

# ============== CLI COMMANDS FOR BENCH ==============
import click
import json
import os
import subprocess
import time
import sys
from datetime import datetime

try:
    import frappe
    from frappe.commands import pass_context
    FRAPPE_AVAILABLE = True
except ImportError:
    FRAPPE_AVAILABLE = False
    pass_context = lambda f: f

def get_current_site():
    """Get current site from currentsite.txt or return None"""
    import os
    sites_path = os.path.join(os.getcwd(), 'sites')
    currentsite_file = os.path.join(sites_path, 'currentsite.txt')
    if os.path.exists(currentsite_file):
        with open(currentsite_file, 'r') as f:
            return f.read().strip()
    return None

# ==================== ENTERPRISE UTILITIES ====================

class ProgressTracker:
    """Visual progress tracking"""
    def __init__(self, app_name, total_steps=4):
        self.app_name = app_name
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = time.time()
    
    def update(self, message):
        self.current_step += 1
        elapsed = int(time.time() - self.start_time)
        print(f"🔄 [{self.current_step}/{self.total_steps}] {message} ({elapsed}s)")
    
    def complete(self):
        elapsed = int(time.time() - self.start_time)
        print(f"✅ [{self.total_steps}/{self.total_steps}] {self.app_name} completed! ({elapsed}s)")
    
    def fail(self, error):
        elapsed = int(time.time() - self.start_time)
        print(f"❌ [{self.current_step}/{self.total_steps}] {self.app_name} failed: {error} ({elapsed}s)")

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
        apps = []
        for line in result.stdout.strip().split('\n'):
            if ' ' in line and not line.startswith('✅'):
                app = line.split()[0]
                apps.append(app)
        return sorted(apps)
    except:
        return []

class MigrationSession:
    """Session management for migrations"""
    def __init__(self, name):
        self.name = name
        self.session_id = f"session_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.session_dir = os.path.expanduser("~/migration_sessions")
        self.session_file = f"{self.session_dir}/{self.session_id}.json"
        self.data = {
            "metadata": {"name": name, "session_id": self.session_id, 
                        "start_time": datetime.now().isoformat(), "status": "active"},
            "progress": {"completed_apps": [], "failed_apps": []},
            "migration_plan": {}
        }
        os.makedirs(self.session_dir, exist_ok=True)
    
    def save(self):
        with open(self.session_file, 'w') as f:
            json.dump(self.data, f, indent=2)
        return self.session_id
    
    @staticmethod
    def load(session_id):
        session_file = os.path.expanduser(f"~/migration_sessions/{session_id}.json")
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                return json.load(f)
        return None

# ==================== HEALTH COMMAND ====================

@click.command('app-migrator-health')
@pass_context
def app_migrator_health(context):
    """Check App Migrator health and list commands"""
    print("=" * 60)
    print(f"🔧 App Migrator Enterprise v{__version__} - OPERATIONAL")
    print("=" * 60)
    print("\n📋 AVAILABLE COMMANDS:")
    print("  Site Analysis:")
    print("    app-migrator-scan --site <name>          Scan site inventory")
    print("    app-migrator-conflicts --site <name>     Detect conflicts")
    print("  Migration:")
    print("    app-migrator-plan --site <name>          Create migration plan")
    print("    app-migrator-execute --site <name>       Execute migration")
    print("  Enterprise:")
    print("    app-migrator-benches                     List all benches")
    print("    app-migrator-apps --site <name>          Downloaded vs installed apps")
    print("    app-migrator-session-start <name>        Start session")
    print("    app-migrator-session-status <id>         Check session")
    print("  Diagnostics:")
    print("    app-migrator-analyze <app>               Analyze app structure")
    print("    app-migrator-fix-orphans --site <name>   Fix orphan doctypes")
    print("    app-migrator-fix-structure <app>         Fix nested folder structure")
    print("  Ping-Pong Staging:")
    print("    app-migrator-create-host <name>          Create staging app")
    print("    app-migrator-stage --site X --source A --host B    Stage doctypes")
    print("    app-migrator-unstage --site X --host B --target C  Unstage doctypes")
    print("=" * 60)

# ==================== SCAN SITE COMMAND ====================

@click.command('app-migrator-scan')
@click.option('--site', required=True, help='Site name')
@click.option('--output', '-o', help='Output JSON file')
@pass_context
def app_migrator_scan(context, site, output):
    """Scan site for apps, doctypes, custom fields"""
    print(f"🔍 Scanning site: {site}")
    print("=" * 60)
    
    frappe.init(site=site)
    frappe.connect()
    
    result = {
        "site": site,
        "timestamp": datetime.now().isoformat(),
        "frappe_version": getattr(frappe, '__version__', 'unknown'),
        "apps": frappe.get_installed_apps(),
        "doctypes": [],
        "custom_fields": [],
        "summary": {}
    }
    
    # Get doctypes
    doctypes = frappe.get_all("DocType", fields=["name", "module", "custom", "istable"])
    result["doctypes"] = [dict(dt) for dt in doctypes]
    
    # Get custom fields
    custom_fields = frappe.get_all("Custom Field", fields=["name", "dt", "fieldname", "fieldtype"])
    result["custom_fields"] = [dict(cf) for cf in custom_fields]
    
    # Summary
    result["summary"] = {
        "apps": len(result["apps"]),
        "doctypes": len(result["doctypes"]),
        "custom_doctypes": len([d for d in doctypes if d.custom]),
        "child_tables": len([d for d in doctypes if d.istable]),
        "custom_fields": len(result["custom_fields"])
    }
    
    frappe.db.close()
    
    # Display
    print(f"\n📊 SCAN RESULTS:")
    print(f"   Frappe: {result['frappe_version']}")
    print(f"   Apps: {result['summary']['apps']}")
    for app in result["apps"]:
        print(f"      • {app}")
    print(f"   DocTypes: {result['summary']['doctypes']}")
    print(f"   Custom DocTypes: {result['summary']['custom_doctypes']}")
    print(f"   Child Tables: {result['summary']['child_tables']}")
    print(f"   Custom Fields: {result['summary']['custom_fields']}")
    
    if output:
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✅ Saved to: {output}")

# ==================== DETECT CONFLICTS COMMAND ====================

@click.command('app-migrator-conflicts')
@click.option('--site', required=True, help='Site name')
@click.option('--apps', help='Comma-separated apps to analyze')
@click.option('--output', '-o', help='Output JSON file')
@pass_context
def app_migrator_conflicts(context, site, apps, output):
    """Detect conflicts between apps"""
    print(f"🔍 Detecting conflicts in: {site}")
    print("=" * 60)
    
    frappe.init(site=site)
    frappe.connect()
    
    apps_list = apps.split(',') if apps else frappe.get_installed_apps()
    
    result = {
        "site": site,
        "apps_analyzed": apps_list,
        "timestamp": datetime.now().isoformat(),
        "conflicts": {
            "duplicate_doctypes": [],
            "orphan_doctypes": [],
            "field_conflicts": []
        }
    }
    
    # Find doctypes by module
    from collections import defaultdict
    doctype_to_apps = defaultdict(list)
    
    for app in apps_list:
        doctypes = frappe.get_all("DocType", filters={"module": app}, fields=["name"])
        for dt in doctypes:
            doctype_to_apps[dt.name].append(app)
    
    # Duplicate doctypes
    for dt, dt_apps in doctype_to_apps.items():
        if len(dt_apps) > 1:
            result["conflicts"]["duplicate_doctypes"].append({
                "doctype": dt, "apps": dt_apps
            })
    
    # Orphan doctypes
    orphans = frappe.get_all("DocType", 
        filters={"module": ["in", ["", None]], "custom": 0},
        fields=["name"])
    result["conflicts"]["orphan_doctypes"] = [{"doctype": o.name} for o in orphans]
    
    frappe.db.close()
    
    # Display
    total = len(result["conflicts"]["duplicate_doctypes"]) + len(result["conflicts"]["orphan_doctypes"])
    print(f"\n📊 CONFLICT SUMMARY:")
    print(f"   Duplicate DocTypes: {len(result['conflicts']['duplicate_doctypes'])}")
    print(f"   Orphan DocTypes: {len(result['conflicts']['orphan_doctypes'])}")
    print(f"   Total Issues: {total}")
    
    if result["conflicts"]["duplicate_doctypes"]:
        print("\n⚠️ DUPLICATES:")
        for dup in result["conflicts"]["duplicate_doctypes"]:
            print(f"   • {dup['doctype']} → {dup['apps']}")
    
    if output:
        with open(output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n✅ Saved to: {output}")

# ==================== GENERATE PLAN COMMAND ====================

@click.command('app-migrator-plan')
@click.option('--site', required=True, help='Site name')
@click.option('--source-apps', required=True, help='Source apps (comma-separated)')
@click.option('--target-app', required=True, help='Target consolidated app')
@click.option('--output', '-o', required=True, help='Output plan file')
@pass_context
def app_migrator_plan(context, site, source_apps, target_app, output):
    """Generate a migration plan"""
    print(f"📋 Generating migration plan")
    print(f"   Source: {source_apps}")
    print(f"   Target: {target_app}")
    print("=" * 60)
    
    frappe.init(site=site)
    frappe.connect()
    
    apps_list = [a.strip() for a in source_apps.split(',')]
    
    plan = {
        "version": "9.0.0",
        "created": datetime.now().isoformat(),
        "source_apps": apps_list,
        "target_app": target_app,
        "doctypes": [],
        "custom_fields": [],
        "data_migration": []
    }
    
    for app in apps_list:
        doctypes = frappe.get_all("DocType", 
            filters={"module": app}, 
            fields=["name", "module", "istable"])
        
        for dt in doctypes:
            try:
                count = frappe.db.count(dt.name)
            except:
                count = 0
            
            plan["doctypes"].append({
                "name": dt.name,
                "source_app": app,
                "target_app": target_app,
                "is_child": dt.istable,
                "record_count": count
            })
            
            if count > 0:
                plan["data_migration"].append({
                    "doctype": dt.name,
                    "records": count,
                    "action": "migrate"
                })
    
    frappe.db.close()
    
    with open(output, 'w') as f:
        json.dump(plan, f, indent=2)
    
    print(f"\n✅ Plan saved: {output}")
    print(f"   DocTypes: {len(plan['doctypes'])}")
    print(f"   Data migrations: {len(plan['data_migration'])}")
    print(f"\n📋 Next: bench app-migrator-execute --site {site} --plan {output} --dry-run")

# ==================== EXECUTE PLAN COMMAND ====================

@click.command('app-migrator-execute')
@click.option('--site', required=True, help='Site name')
@click.option('--plan', 'plan_file', required=True, help='Migration plan file')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_execute(context, site, plan_file, dry_run):
    """Execute a migration plan"""
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"🚀 Executing migration [{mode}]")
    print("=" * 60)
    
    with open(plan_file, 'r') as f:
        plan = json.load(f)
    
    if not dry_run:
        if not click.confirm("⚠️ This will modify your database. Continue?"):
            print("❌ Cancelled")
            return
    
    frappe.init(site=site)
    frappe.connect()
    
    tracker = ProgressTracker("Migration", len(plan["doctypes"]))
    
    for dt in plan["doctypes"]:
        tracker.update(f"Processing {dt['name']}")
        if not dry_run:
            frappe.db.sql("""
                UPDATE `tabDocType` SET module = %s WHERE name = %s
            """, (dt["target_app"], dt["name"]))
    
    if not dry_run:
        frappe.db.commit()
    
    frappe.db.close()
    tracker.complete()
    
    if dry_run:
        print(f"\n✅ Dry-run complete. Run with --apply to execute.")
    else:
        print(f"\n✅ Migration complete! Run 'bench --site {site} migrate'")

# ==================== ENTERPRISE: LIST BENCHES ====================

@click.command('app-migrator-benches')
@pass_context
def app_migrator_benches(context):
    """List all available benches and their apps"""
    print("🏗️ MULTI-BENCH ANALYSIS")
    print("=" * 60)
    
    benches = detect_available_benches()
    print(f"Found {len(benches)} benches:\n")
    
    for bench in benches:
        bench_path = os.path.expanduser(f"~/{bench}")
        apps = get_bench_apps(bench_path)
        print(f"📦 {bench}: {len(apps)} apps")
        for app in apps:
            print(f"   • {app}")
        print()

# ==================== ENTERPRISE: SESSION MANAGEMENT ====================

@click.command('app-migrator-session-start')
@click.argument('name')
@pass_context
def app_migrator_session_start(context, name):
    """Start a new migration session"""
    session = MigrationSession(name)
    session_id = session.save()
    print(f"✅ Session started: {name}")
    print(f"📁 Session ID: {session_id}")
    print(f"\n   Check status: bench app-migrator-session-status {session_id}")

@click.command('app-migrator-session-status')
@click.argument('session_id')
@pass_context  
def app_migrator_session_status(context, session_id):
    """Check migration session status"""
    data = MigrationSession.load(session_id)
    if not data:
        print(f"❌ Session not found: {session_id}")
        return
    
    print(f"📊 SESSION STATUS")
    print("=" * 40)
    print(f"   Name: {data['metadata']['name']}")
    print(f"   ID: {data['metadata']['session_id']}")
    print(f"   Status: {data['metadata']['status'].upper()}")
    print(f"   Started: {data['metadata']['start_time']}")
    print(f"   Completed Apps: {len(data['progress']['completed_apps'])}")
    print(f"   Failed Apps: {len(data['progress']['failed_apps'])}")

# ==================== LIST APPS (DOWNLOADED VS INSTALLED) ====================

@click.command('app-migrator-apps')
@click.option('--site', help='Site name (optional)')
@pass_context
def app_migrator_apps(context, site):
    """List downloaded apps vs installed apps"""
    print("📦 APP INVENTORY")
    print("=" * 60)
    
    # Get downloaded apps from apps directory
    apps_dir = os.path.expanduser("~/frappe-bench/apps")
    downloaded = []
    if os.path.exists(apps_dir):
        for item in os.listdir(apps_dir):
            item_path = os.path.join(apps_dir, item)
            if os.path.isdir(item_path) and not item.startswith('.'):
                # Check if it's a valid Frappe app
                has_hooks = os.path.exists(os.path.join(item_path, item, "hooks.py")) or \
                           os.path.exists(os.path.join(item_path, "hooks.py"))
                has_pyproject = os.path.exists(os.path.join(item_path, "pyproject.toml"))
                if has_hooks or has_pyproject:
                    downloaded.append(item)
    
    downloaded = sorted(downloaded)
    
    # Get installed apps if site provided
    installed = []
    if site:
        try:
            frappe.init(site=site)
            frappe.connect()
            installed = frappe.get_installed_apps()
            frappe.db.close()
        except:
            pass
    
    print(f"\n📥 DOWNLOADED APPS ({len(downloaded)}):")
    for app in downloaded:
        status = "✅ installed" if app in installed else "⬜ not installed"
        print(f"   {app:30} {status}")
    
    if site and installed:
        not_downloaded = [a for a in installed if a not in downloaded]
        if not_downloaded:
            print(f"\n⚠️ INSTALLED BUT NOT IN APPS DIR:")
            for app in not_downloaded:
                print(f"   {app}")
    
    print(f"\n📊 SUMMARY:")
    print(f"   Downloaded: {len(downloaded)}")
    print(f"   Installed:  {len(installed)}")
    print(f"   Available:  {len(downloaded) - len(installed)}")

# ==================== FIX ORPHAN DOCTYPES ====================

@click.command('app-migrator-fix-orphans')
@click.option('--site', required=True, help='Site name')
@click.option('--target-module', default=None, help='Target module for orphans')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_fix_orphans(context, site, target_module, dry_run):
    """Fix orphan doctypes (doctypes with no module or invalid module)"""
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"🔧 FIXING ORPHAN DOCTYPES [{mode}]")
    print(f"   Site: {site}")
    print("=" * 60)
    
    frappe.init(site=site)
    frappe.connect()
    
    # Find orphan doctypes - those with empty/null module or module not matching any app
    installed_apps = frappe.get_installed_apps()
    
    # Get all modules from installed apps
    valid_modules = set()
    for app in installed_apps:
        try:
            modules = frappe.get_all("Module Def", filters={"app_name": app}, pluck="name")
            valid_modules.update(modules)
        except:
            pass
    
    # Also add app names as valid modules (some doctypes use app name as module)
    valid_modules.update(installed_apps)
    
    # Find orphans
    orphans = []
    
    # 1. DocTypes with empty/null module
    empty_module = frappe.get_all("DocType", 
        filters=[["module", "in", ["", None]]],
        fields=["name", "module", "custom"])
    orphans.extend([{"name": d.name, "module": d.module or "(empty)", "type": "empty_module", "custom": d.custom} for d in empty_module])
    
    # 2. DocTypes with module not in valid_modules (excluding custom doctypes)
    all_doctypes = frappe.get_all("DocType", 
        filters={"custom": 0},
        fields=["name", "module"])
    
    for dt in all_doctypes:
        if dt.module and dt.module not in valid_modules:
            orphans.append({"name": dt.name, "module": dt.module, "type": "invalid_module", "custom": 0})
    
    # 3. Custom Fields with orphan dt
    orphan_custom_fields = frappe.db.sql("""
        SELECT cf.name, cf.dt, cf.fieldname
        FROM `tabCustom Field` cf
        LEFT JOIN `tabDocType` dt ON cf.dt = dt.name
        WHERE dt.name IS NULL
    """, as_dict=True)
    
    print(f"\n📊 ORPHAN ANALYSIS:")
    print(f"   DocTypes with empty module: {len([o for o in orphans if o['type'] == 'empty_module'])}")
    print(f"   DocTypes with invalid module: {len([o for o in orphans if o['type'] == 'invalid_module'])}")
    print(f"   Orphan Custom Fields: {len(orphan_custom_fields)}")
    
    if orphans:
        print(f"\n⚠️ ORPHAN DOCTYPES ({len(orphans)}):")
        for o in orphans[:20]:  # Show first 20
            print(f"   • {o['name']:40} module='{o['module']}' ({o['type']})")
        if len(orphans) > 20:
            print(f"   ... and {len(orphans) - 20} more")
    
    if orphan_custom_fields:
        print(f"\n⚠️ ORPHAN CUSTOM FIELDS ({len(orphan_custom_fields)}):")
        for cf in orphan_custom_fields[:10]:
            print(f"   • {cf['name']} → dt='{cf['dt']}'")
        if len(orphan_custom_fields) > 10:
            print(f"   ... and {len(orphan_custom_fields) - 10} more")
    
    if not dry_run and target_module:
        print(f"\n🔧 APPLYING FIXES (target module: {target_module})...")
        fixed = 0
        
        for o in orphans:
            # Fix both empty_module and invalid_module types
            frappe.db.sql("""
                UPDATE `tabDocType` SET module = %s WHERE name = %s
            """, (target_module, o['name']))
            print(f"   📝 Fixed: {o['name']} → {target_module}")
            fixed += 1
        
        # Delete orphan custom fields
        for cf in orphan_custom_fields:
            frappe.db.sql("DELETE FROM `tabCustom Field` WHERE name = %s", cf['name'])
        
        frappe.db.commit()
        print(f"\n   ✅ Fixed {fixed} doctypes")
        print(f"   ✅ Deleted {len(orphan_custom_fields)} orphan custom fields")
    elif not dry_run and not target_module:
        print(f"\n❌ --target-module required when using --apply")
    else:
        print(f"\n📋 Run with --apply --target-module <module> to fix")
    
    frappe.db.close()

# ==================== ANALYZE APP STRUCTURE (MODERN VS TRADITIONAL) ====================

@click.command('app-migrator-analyze')
@click.argument('app_name')
@pass_context
def app_migrator_analyze(context, app_name):
    """Analyze app structure (modern pyproject.toml vs traditional)"""
    print(f"🔍 ANALYZING APP: {app_name}")
    print("=" * 60)
    
    app_path = os.path.expanduser(f"~/frappe-bench/apps/{app_name}")
    
    if not os.path.exists(app_path):
        print(f"❌ App not found: {app_path}")
        return
    
    result = {
        "app_name": app_name,
        "path": app_path,
        "structure": "unknown",
        "has_pyproject": False,
        "has_hooks": False,
        "has_modules_txt": False,
        "nested_package": False,
        "modules": [],
        "dependencies": [],
        "issues": []
    }
    
    # Check for modern structure (pyproject.toml)
    pyproject_path = os.path.join(app_path, "pyproject.toml")
    result["has_pyproject"] = os.path.exists(pyproject_path)
    
    # Check for nested package structure
    nested_path = os.path.join(app_path, app_name)
    if os.path.isdir(nested_path):
        result["nested_package"] = True
        hooks_path = os.path.join(nested_path, "hooks.py")
        modules_txt_path = os.path.join(nested_path, "modules.txt")
    else:
        hooks_path = os.path.join(app_path, "hooks.py")
        modules_txt_path = os.path.join(app_path, "modules.txt")
    
    result["has_hooks"] = os.path.exists(hooks_path)
    result["has_modules_txt"] = os.path.exists(modules_txt_path)
    
    # Determine structure type
    if result["has_pyproject"] and result["nested_package"]:
        result["structure"] = "modern"
    elif result["has_hooks"]:
        result["structure"] = "traditional"
    else:
        result["structure"] = "incomplete"
        result["issues"].append("Missing hooks.py")
    
    # Read modules.txt if exists
    if result["has_modules_txt"]:
        with open(modules_txt_path, 'r') as f:
            result["modules"] = [line.strip() for line in f if line.strip()]
    
    # Detect Python modules in nested package
    if result["nested_package"]:
        for item in os.listdir(nested_path):
            item_path = os.path.join(nested_path, item)
            if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "__init__.py")):
                if item not in ['templates', 'public', 'patches', 'config', '__pycache__']:
                    if item not in result["modules"]:
                        result["modules"].append(item)
    
    # Read dependencies from pyproject.toml
    if result["has_pyproject"]:
        try:
            with open(pyproject_path, 'r') as f:
                content = f.read()
                # Simple extraction of dependencies
                if 'dependencies' in content:
                    import re
                    deps = re.findall(r'"([a-zA-Z0-9_-]+)"', content)
                    result["dependencies"] = [d for d in deps if d not in ['python', 'frappe', app_name]][:10]
        except:
            pass
    
    # Check for issues
    if not result["has_hooks"]:
        result["issues"].append("Missing hooks.py")
    if not result["has_modules_txt"] and result["modules"]:
        result["issues"].append("Missing modules.txt (has modules)")
    
    # Display results
    print(f"\n📋 STRUCTURE ANALYSIS:")
    print(f"   Type: {result['structure'].upper()}")
    print(f"   Nested Package: {'Yes' if result['nested_package'] else 'No'}")
    print(f"   pyproject.toml: {'✅' if result['has_pyproject'] else '❌'}")
    print(f"   hooks.py: {'✅' if result['has_hooks'] else '❌'}")
    print(f"   modules.txt: {'✅' if result['has_modules_txt'] else '❌'}")
    
    if result["modules"]:
        print(f"\n📦 MODULES ({len(result['modules'])}):")
        for mod in result["modules"][:15]:
            print(f"   • {mod}")
        if len(result["modules"]) > 15:
            print(f"   ... and {len(result['modules']) - 15} more")
    
    if result["dependencies"]:
        print(f"\n📚 DEPENDENCIES ({len(result['dependencies'])}):")
        for dep in result["dependencies"]:
            print(f"   • {dep}")
    
    if result["issues"]:
        print(f"\n⚠️ ISSUES:")
        for issue in result["issues"]:
            print(f"   • {issue}")
    
    # Health score
    score = 0
    if result["has_hooks"]: score += 30
    if result["has_modules_txt"]: score += 20
    if result["has_pyproject"]: score += 20
    if result["modules"]: score += 20
    if not result["issues"]: score += 10
    
    print(f"\n💯 HEALTH SCORE: {score}%")

# ==================== PING-PONG STAGING: CREATE HOST APP ====================

@click.command('app-migrator-create-host')
@click.argument('host_app_name')
@pass_context
def app_migrator_create_host(context, host_app_name):
    """Create a staging/host app for ping-pong migration"""
    print(f"🏗️ CREATE HOST APP: {host_app_name}")
    print("=" * 60)
    
    apps_dir = os.path.expanduser("~/frappe-bench/apps")
    host_path = os.path.join(apps_dir, host_app_name)
    
    if os.path.exists(host_path):
        print(f"✅ App already exists: {host_path}")
        print(f"\n📋 NEXT STEPS:")
        print(f"   1. Install: bench --site <site> install-app {host_app_name}")
        print(f"   2. Stage: bench app-migrator-stage --site <site> --source <app> --host {host_app_name}")
        return
    
    # Use frappe API directly to create app non-interactively
    print(f"\n🔄 Creating app: {host_app_name}...")
    
    try:
        from frappe.utils.boilerplate import _create_app_boilerplate
        import frappe
        
        hooks = frappe._dict(
            app_name=host_app_name,
            app_title=host_app_name.replace("_", " ").title(),
            app_description="Staging app for ping-pong migration",
            app_publisher="App Migrator",
            app_email="migrator@localhost",
            app_license="mit",
            create_github_workflow=False,
            branch_name="develop"
        )
        
        _create_app_boilerplate(apps_dir, hooks, no_git=True)
        
        print(f"✅ App created: {host_path}")
        print(f"\n📋 NEXT STEPS:")
        print(f"   1. Install: bench --site <site> install-app {host_app_name}")
        print(f"   2. Stage: bench app-migrator-stage --site <site> --source <app> --host {host_app_name}")
        
    except ImportError:
        # Fallback if direct import fails
        print(f"\n⚠️ Direct creation failed. Run manually:")
        print(f"   cd ~/frappe-bench && bench new-app {host_app_name}")
        print(f"\n   Answer prompts:")
        print(f"     App Title: {host_app_name.replace('_', ' ').title()}")
        print(f"     App Description: Staging app for migration")
        print(f"     App Publisher: Your Name")
        print(f"     App Email: your@email.com")
        print(f"     App License: mit")

# ==================== PING-PONG STAGING: STAGE DOCTYPES ====================

@click.command('app-migrator-stage')
@click.option('--site', default=None, help='Site name (uses current site if not specified)')
@click.option('--source', required=True, help='Source app name')
@click.option('--host', required=True, help='Host/staging app name')
@click.option('--doctypes', default=None, help='Comma-separated doctype names (or all)')
@click.option('--prefix', default='STAGE_', help='Prefix for staged doctypes')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_stage(context, site, source, host, doctypes, prefix, dry_run):
    """Stage doctypes from source app to host app with prefix"""
    if not site:
        site = get_current_site()
        if not site:
            print("❌ No site specified and no current site set. Use --site or 'bench use <site>'")
            return
    mode = "DRY-RUN" if dry_run else "APPLY"
    source_module_title = source.replace("_", " ").title()
    print(f"📤 STAGING DOCTYPES [{mode}]")
    print(f"   Source: {source} (module: {source_module_title})")
    print(f"   Host: {host}")
    print(f"   Prefix: {prefix}")
    print("=" * 60)
    
    frappe.init(site=site)
    frappe.connect()
    
    # Get doctypes from source app (use title case for module matching)
    if doctypes:
        dt_list = [d.strip() for d in doctypes.split(',')]
        source_doctypes = frappe.get_all("DocType", 
            filters={"name": ["in", dt_list]},
            fields=["name", "module"])
    else:
        source_doctypes = frappe.get_all("DocType", 
            filters={"module": source_module_title},
            fields=["name", "module"])
    
    host_module_title = host.replace("_", " ").title()
    print(f"\n📦 DOCTYPES TO REASSIGN TO MODULE '{host_module_title}' ({len(source_doctypes)}):")
    staged = []
    
    for dt in source_doctypes:
        print(f"   • {dt.name} (current: {dt.module})")
        staged.append({"old_name": dt.name, "old_module": dt.module})
    
    if not dry_run:
        print(f"\n🔧 STAGING (reassigning module via Frappe API)...")
        
        # Step 1: Ensure host module exists in Module Def
        host_module_title = host.replace("_", " ").title()
        if not frappe.db.exists("Module Def", host_module_title):
            try:
                module_doc = frappe.new_doc("Module Def")
                module_doc.module_name = host_module_title
                module_doc.app_name = host
                module_doc.insert(ignore_permissions=True)
                print(f"   ✅ Created Module Def: {host_module_title}")
            except Exception as e:
                print(f"   ⚠️ Module Def creation: {e}")
        
        # Step 2: Update modules.txt in host app (if it exists)
        host_apps_path = os.path.expanduser(f"~/frappe-bench/apps/{host}/{host}/modules.txt")
        if os.path.exists(host_apps_path):
            with open(host_apps_path, 'r') as f:
                modules = [m.strip() for m in f.readlines() if m.strip()]
            if host_module_title not in modules:
                modules.append(host_module_title)
                with open(host_apps_path, 'w') as f:
                    f.write('\n'.join(modules) + '\n')
                print(f"   ✅ Updated modules.txt with: {host_module_title}")
        else:
            print(f"   ℹ️ No modules.txt found (host app not required for staging)")
        
        # Step 3: Reassign doctypes to host module AND mark as custom (prevents orphan deletion)
        success_count = 0
        for item in staged:
            dt_name = item["old_name"]
            try:
                # Update module field AND set custom=1 to prevent orphan deletion during migrate
                frappe.db.set_value("DocType", dt_name, {
                    "module": host_module_title,
                    "custom": 1  # CRITICAL: prevents bench migrate from deleting as orphan
                }, update_modified=False)
                print(f"   ✅ {dt_name} → module: {host_module_title} (custom=1)")
                success_count += 1
            except Exception as e:
                print(f"   ❌ {dt_name}: {e}")
        
        frappe.db.commit()
        print(f"\n✅ Reassigned {success_count}/{len(staged)} doctypes to module '{host_module_title}'")
        print(f"\n📋 To move back to original or new app, run:")
        print(f"   bench app-migrator-unstage --site {site} --host {host} --target <target_app>")
    else:
        print(f"\n📋 Run with --apply to reassign doctypes to host module")
    
    frappe.db.close()

# ==================== PING-PONG STAGING: UNSTAGE DOCTYPES ====================

@click.command('app-migrator-unstage')
@click.option('--site', default=None, help='Site name (uses current site if not specified)')
@click.option('--host', required=True, help='Host/staging module name')
@click.option('--target', required=True, help='Target module name')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_unstage(context, site, host, target, dry_run):
    """Unstage doctypes from host module to target module (reassign module)"""
    if not site:
        site = get_current_site()
        if not site:
            print("❌ No site specified and no current site set. Use --site or 'bench use <site>'")
            return
    mode = "DRY-RUN" if dry_run else "APPLY"
    host_module_title = host.replace("_", " ").title()
    target_module_title = target.replace("_", " ").title()
    
    print(f"📥 UNSTAGING DOCTYPES [{mode}]")
    print(f"   From module: {host_module_title}")
    print(f"   To module: {target_module_title}")
    print("=" * 60)
    
    frappe.init(site=site)
    frappe.connect()
    
    # Get doctypes in the host module
    host_doctypes = frappe.get_all("DocType", 
        filters={"module": host_module_title},
        fields=["name", "module"])
    
    print(f"\n📦 DOCTYPES TO REASSIGN ({len(host_doctypes)}):")
    
    for dt in host_doctypes:
        print(f"   • {dt.name}")
    
    if not dry_run:
        print(f"\n🔧 REASSIGNING TO MODULE '{target_module_title}'...")
        success_count = 0
        for dt in host_doctypes:
            try:
                # Restore module, set custom=0, and set app field (CRITICAL for orphan prevention)
                frappe.db.set_value("DocType", dt.name, {
                    "module": target_module_title,
                    "custom": 0,  # Restore to normal doctype
                    "app": target  # CRITICAL: prevents orphan deletion
                }, update_modified=False)
                print(f"   ✅ {dt.name} → module: {target_module_title} (custom=0)")
                success_count += 1
            except Exception as e:
                print(f"   ❌ {dt.name}: {e}")
        
        frappe.db.commit()
        print(f"\n✅ Reassigned {success_count}/{len(host_doctypes)} doctypes to '{target_module_title}'")
        
        # Auto-create missing controller files for the target app
        print(f"\n🔧 Ensuring controller files exist for target app...")
        created = ensure_controller_files(target, target, dry_run=False)
        if created:
            print(f"   Created {len(created)} controller file(s)")
        else:
            print(f"   All controller files already exist")
        
        print(f"\n📋 Now run: bench --site {site} migrate")
    else:
        print(f"\n📋 Run with --apply to reassign")
    
    frappe.db.close()

# ==================== ANALYZE APP STRUCTURE (DETAILED) ====================

@click.command('app-migrator-fix-structure')
@click.argument('app_name')
@pass_context
def app_migrator_fix_structure(context, app_name):
    """
    Analyze Frappe app folder structure and report findings.
    
    Frappe apps can have different valid structures:
    
    1. Single-module app (module name = app name):
       apps/{app}/{app}/{app}/doctype/  <- VALID (triple-nested)
       
    2. Multi-module app:
       apps/{app}/{app}/{module1}/doctype/
       apps/{app}/{app}/{module2}/doctype/
    
    This command analyzes the structure and reports what it finds.
    It does NOT automatically move files (that was causing issues).
    """
    print(f"🔍 ANALYZE APP STRUCTURE")
    print(f"   App: {app_name}")
    print("=" * 60)
    
    apps_dir = os.path.expanduser("~/frappe-bench/apps")
    app_path = os.path.join(apps_dir, app_name)
    
    if not os.path.exists(app_path):
        print(f"❌ App not found: {app_path}")
        return
    
    # Level structure
    level1 = app_path  # apps/{app}/
    level2 = os.path.join(level1, app_name)  # apps/{app}/{app}/
    
    print(f"\n📁 DIRECTORY STRUCTURE:")
    print(f"   Level 1 (repo root): {level1}")
    
    # Check level2
    if not os.path.isdir(level2):
        print(f"   ❌ Level 2 missing: {level2}")
        print(f"\n⚠️ Invalid app structure - missing Python package folder")
        return
    
    print(f"   Level 2 (package):   {level2}")
    
    # Check for hooks.py at level2
    hooks_path = os.path.join(level2, "hooks.py")
    modules_txt_path = os.path.join(level2, "modules.txt")
    
    print(f"\n📋 PACKAGE FILES:")
    print(f"   hooks.py:    {'✅ Found' if os.path.exists(hooks_path) else '❌ Missing'}")
    print(f"   modules.txt: {'✅ Found' if os.path.exists(modules_txt_path) else '❌ Missing'}")
    
    # Read modules.txt
    modules = []
    if os.path.exists(modules_txt_path):
        with open(modules_txt_path, 'r') as f:
            modules = [m.strip() for m in f.readlines() if m.strip()]
        print(f"\n📦 MODULES DEFINED ({len(modules)}):")
        for m in modules:
            print(f"   • {m}")
    
    # Check module folders at level2
    print(f"\n📂 MODULE FOLDERS AT LEVEL 2:")
    
    level2_dirs = [d for d in os.listdir(level2) 
                   if os.path.isdir(os.path.join(level2, d)) 
                   and not d.startswith('.') 
                   and d not in ['__pycache__', 'templates', 'public', 'patches', 'config', 'www']]
    
    for dir_name in sorted(level2_dirs):
        dir_path = os.path.join(level2, dir_name)
        has_doctype = os.path.isdir(os.path.join(dir_path, "doctype"))
        has_page = os.path.isdir(os.path.join(dir_path, "page"))
        has_report = os.path.isdir(os.path.join(dir_path, "report"))
        
        if has_doctype or has_page or has_report:
            # This is a module folder
            module_title = dir_name.replace("_", " ").title()
            in_modules_txt = module_title in modules or dir_name in [m.lower().replace(" ", "_") for m in modules]
            
            doctype_count = 0
            if has_doctype:
                doctype_path = os.path.join(dir_path, "doctype")
                doctype_count = len([d for d in os.listdir(doctype_path) 
                                    if os.path.isdir(os.path.join(doctype_path, d)) and d != '__pycache__'])
            
            status = "✅" if in_modules_txt else "⚠️ NOT IN modules.txt"
            print(f"   • {dir_name}/ - {doctype_count} doctypes {status}")
            
            if has_doctype:
                print(f"      └── doctype/")
            if has_page:
                print(f"      └── page/")
            if has_report:
                print(f"      └── report/")
    
    # Check for doctypes directly at level2
    direct_doctype = os.path.join(level2, "doctype")
    if os.path.isdir(direct_doctype):
        doctype_count = len([d for d in os.listdir(direct_doctype) 
                            if os.path.isdir(os.path.join(direct_doctype, d)) and d != '__pycache__'])
        print(f"\n⚠️ DOCTYPES DIRECTLY AT LEVEL 2 ({doctype_count}):")
        print(f"   Path: {direct_doctype}")
        print(f"   This is unusual - doctypes should be inside a module folder.")
        print(f"   Expected: apps/{app_name}/{app_name}/{app_name}/doctype/")
        print(f"   Found:    apps/{app_name}/{app_name}/doctype/")
    
    # Summary
    print(f"\n📊 SUMMARY:")
    
    # Check if app_name is also a module
    app_module_path = os.path.join(level2, app_name, "doctype")
    if os.path.isdir(app_module_path):
        print(f"   ✅ App uses module '{app_name}' (triple-nested structure is CORRECT)")
    elif os.path.isdir(direct_doctype):
        print(f"   ⚠️ App has doctypes at level2 without module folder")
        print(f"      This may cause import issues. Consider:")
        print(f"      1. Create module folder: {app_name}/{app_name}/{app_name}/")
        print(f"      2. Move doctype/ into it")
        print(f"      3. Update modules.txt with module name")
    else:
        print(f"   ℹ️ App structure looks standard")


# ==================== ENSURE CONTROLLER FILES ====================

def ensure_controller_files(app_name, module_name=None, dry_run=True):
    """
    Create missing .py controller files for DocTypes in an app.
    
    When DocTypes are marked as custom=0 (standard), Frappe requires
    a .py controller file. This function creates basic controller files
    for any DocTypes that are missing them.
    
    Args:
        app_name: The app name (e.g., 'amb_w_tds')
        module_name: Optional module name (defaults to app_name)
        dry_run: If True, only report what would be created
    
    Returns:
        List of created/would-create file paths
    """
    import re
    
    if module_name is None:
        module_name = app_name
    
    apps_dir = os.path.expanduser("~/frappe-bench/apps")
    
    # Try different possible structures
    possible_paths = [
        os.path.join(apps_dir, app_name, app_name, module_name, "doctype"),  # Triple nested
        os.path.join(apps_dir, app_name, app_name, "doctype"),  # Double nested
    ]
    
    doctype_path = None
    for path in possible_paths:
        if os.path.isdir(path):
            doctype_path = path
            break
    
    if not doctype_path:
        print(f"❌ No doctype folder found for app: {app_name}")
        return []
    
    print(f"📁 DocType folder: {doctype_path}")
    
    created_files = []
    
    for item in os.listdir(doctype_path):
        item_path = os.path.join(doctype_path, item)
        
        # Skip non-directories and __pycache__
        if not os.path.isdir(item_path) or item.startswith('__'):
            continue
        
        doctype_name = item
        py_file = os.path.join(item_path, f"{doctype_name}.py")
        json_file = os.path.join(item_path, f"{doctype_name}.json")
        
        # Only create .py if .json exists but .py doesn't
        if os.path.exists(json_file) and not os.path.exists(py_file):
            # Convert doctype_name to PascalCase class name
            # e.g., 'third_party_api' -> 'ThirdPartyApi'
            class_name = ''.join(word.capitalize() for word in doctype_name.split('_'))
            
            controller_content = f'''import frappe
from frappe.model.document import Document

class {class_name}(Document):
    pass
'''
            
            if dry_run:
                print(f"   Would create: {py_file}")
            else:
                with open(py_file, 'w') as f:
                    f.write(controller_content)
                print(f"   ✅ Created: {py_file}")
            
            created_files.append(py_file)
    
    return created_files


@click.command('app-migrator-ensure-controllers')
@click.argument('app_name')
@click.option('--module', default=None, help='Module name (defaults to app name)')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_ensure_controllers(context, app_name, module, dry_run):
    """
    Create missing .py controller files for DocTypes in an app.
    
    This is needed when converting custom DocTypes (custom=1) to standard
    DocTypes (custom=0). Standard DocTypes require a .py controller file.
    
    Example:
        bench app-migrator-ensure-controllers amb_w_tds --apply
    """
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"🔧 ENSURE CONTROLLER FILES [{mode}]")
    print(f"   App: {app_name}")
    print(f"   Module: {module or app_name}")
    print("=" * 60)
    
    created = ensure_controller_files(app_name, module, dry_run)
    
    if created:
        print(f"\n📊 {'Would create' if dry_run else 'Created'} {len(created)} controller file(s)")
        if dry_run:
            print(f"\n📋 Run with --apply to create the files")
    else:
        print(f"\n✅ All DocTypes already have controller files")


# ==================== FIX APP FIELD (PREVENTS ORPHAN DELETION) ====================

@click.command('app-migrator-fix-app-field')
@click.option('--site', required=True, help='Site name')
@click.option('--module', required=True, help='Module name (e.g., "Amb W Tds")')
@click.option('--app', required=True, help='App name (e.g., "amb_w_tds")')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_fix_app_field(context, site, module, app, dry_run):
    """
    Fix DocTypes with NULL app field to prevent orphan deletion.
    
    CRITICAL: When a DocType's 'app' field is NULL, bench migrate marks it
    as an orphan and DELETES it, even if the JSON file exists!
    
    This command finds all DocTypes in a module where app=NULL and sets
    the correct app name.
    
    Example:
        bench app-migrator-fix-app-field --site mysite --module "Amb W Tds" --app amb_w_tds --apply
    """
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"🔧 FIX APP FIELD [{mode}]")
    print(f"   Site: {site}")
    print(f"   Module: {module}")
    print(f"   Target App: {app}")
    print("=" * 60)
    
    frappe.init(site=site)
    frappe.connect()
    
    # Find DocTypes with NULL app field in this module
    doctypes_with_null_app = frappe.db.sql("""
        SELECT name, module, custom, app 
        FROM `tabDocType` 
        WHERE module = %s AND (app IS NULL OR app = '')
    """, (module,), as_dict=True)
    
    if not doctypes_with_null_app:
        print(f"\n✅ No DocTypes found with NULL app field in module '{module}'")
        frappe.db.close()
        return
    
    print(f"\n⚠️ DOCTYPES WITH NULL APP FIELD ({len(doctypes_with_null_app)}):")
    for dt in doctypes_with_null_app:
        print(f"   • {dt['name']} (custom={dt['custom']}, app={dt['app']})")
    
    if not dry_run:
        print(f"\n🔧 FIXING APP FIELD...")
        fixed_count = 0
        for dt in doctypes_with_null_app:
            try:
                frappe.db.set_value("DocType", dt['name'], "app", app, update_modified=False)
                print(f"   ✅ {dt['name']} → app: {app}")
                fixed_count += 1
            except Exception as e:
                print(f"   ❌ {dt['name']}: {e}")
        
        frappe.db.commit()
        print(f"\n✅ Fixed {fixed_count}/{len(doctypes_with_null_app)} DocTypes")
        print(f"\n📋 Now run: bench --site {site} migrate")
    else:
        print(f"\n📋 Run with --apply to fix the app field")
    
    frappe.db.close()


# ==================== FIX APP FIELD IN JSON FILES ====================

@click.command('app-migrator-fix-json-app')
@click.argument('app_name')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
def app_migrator_fix_json_app(app_name, dry_run):
    """
    Fix JSON app field issues to prevent orphan deletion on fresh installs.
    
    This command fixes TWO common issues:
    1. 'app': null - Replaces with correct app name
    2. Duplicate 'app' fields - Removes the first occurrence (keeps the one near 'module')
    
    Both issues cause DocTypes to be deleted as orphans during bench migrate.
    
    Example:
        bench app-migrator-fix-json-app amb_w_tds --apply
    """
    import os
    import re
    
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"🔧 FIX JSON APP FIELD [{mode}]")
    print(f"   App: {app_name}")
    print("=" * 60)
    
    # Find app directory
    bench_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    apps_path = os.path.join(bench_path, "apps")
    app_path = os.path.join(apps_path, app_name)
    
    if not os.path.exists(app_path):
        print(f"❌ App not found: {app_path}")
        return
    
    # Find all DocType JSON files
    null_app_files = []
    duplicate_app_files = []
    already_correct = []
    errors = []
    
    for root, dirs, files in os.walk(app_path):
        if "/doctype/" in root:
            for f in files:
                if f.endswith(".json") and not f.startswith("_"):
                    json_path = os.path.join(root, f)
                    try:
                        with open(json_path, 'r') as fp:
                            content = fp.read()
                        
                        # Check if this is a DocType JSON
                        if '"doctype": "DocType"' not in content:
                            continue
                        
                        needs_fix = False
                        
                        # Issue 1: Check for "app": null
                        if '"app": null' in content or '"app":null' in content:
                            null_app_files.append(json_path)
                            needs_fix = True
                            if not dry_run:
                                content = re.sub(
                                    r'"app":\s*null',
                                    f'"app": "{app_name}"',
                                    content
                                )
                        
                        # Issue 2: Check for duplicate "app" fields
                        app_count = len(re.findall(r'"app":', content))
                        if app_count > 1:
                            duplicate_app_files.append(json_path)
                            needs_fix = True
                            if not dry_run:
                                # Remove the first occurrence (in first 30 lines)
                                lines = content.split('\n')
                                new_lines = []
                                removed = False
                                for i, line in enumerate(lines):
                                    if not removed and i < 30 and '"app":' in line:
                                        removed = True
                                        continue
                                    new_lines.append(line)
                                content = '\n'.join(new_lines)
                        
                        if needs_fix and not dry_run:
                            with open(json_path, 'w') as fp:
                                fp.write(content)
                        elif not needs_fix:
                            already_correct.append(json_path)
                            
                    except Exception as e:
                        errors.append((json_path, str(e)))
    
    print(f"\n📊 SCAN RESULTS:")
    print(f"   Files with 'app': null: {len(null_app_files)}")
    print(f"   Files with duplicate 'app': {len(duplicate_app_files)}")
    print(f"   Already correct: {len(already_correct)}")
    if errors:
        print(f"   Errors: {len(errors)}")
    
    total_issues = len(set(null_app_files + duplicate_app_files))
    
    if null_app_files:
        print(f"\n📝 {'Would fix' if dry_run else 'Fixed'} 'app': null → 'app': '{app_name}':")
        for f in null_app_files[:5]:
            print(f"   • {os.path.basename(os.path.dirname(f))}")
        if len(null_app_files) > 5:
            print(f"   ... and {len(null_app_files) - 5} more")
    
    if duplicate_app_files:
        print(f"\n📝 {'Would remove' if dry_run else 'Removed'} duplicate 'app' field:")
        for f in duplicate_app_files[:5]:
            print(f"   • {os.path.basename(os.path.dirname(f))}")
        if len(duplicate_app_files) > 5:
            print(f"   ... and {len(duplicate_app_files) - 5} more")
    
    if dry_run and total_issues > 0:
        print(f"\n📋 Run with --apply to fix {total_issues} file(s)")
        print(f"   Then commit: cd {app_path} && git add -A && git commit -m 'Fix app field in JSON' && git push")
    elif not dry_run and total_issues > 0:
        print(f"\n✅ Fixed {total_issues} file(s)")
        print(f"\n📋 Now commit the changes:")
        print(f"   cd {app_path}")
        print(f"   git add -A && git commit -m 'Fix app field in JSON' && git push")
    elif total_issues == 0:
        print(f"\n✅ All JSON files are correct - no issues found")


# ==================== EXPORT ALL COMMANDS ====================

commands = [
    app_migrator_health,
    app_migrator_scan,
    app_migrator_conflicts,
    app_migrator_plan,
    app_migrator_execute,
    app_migrator_benches,
    app_migrator_session_start,
    app_migrator_session_status,
    app_migrator_apps,
    app_migrator_fix_orphans,
    app_migrator_analyze,
    app_migrator_create_host,
    app_migrator_stage,
    app_migrator_unstage,
    app_migrator_fix_structure,
    app_migrator_ensure_controllers,
    app_migrator_fix_app_field,
    app_migrator_fix_json_app
]

print("✅ App Migrator Enterprise v9.0.0 ready!")
