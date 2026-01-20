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
@click.option('--site', required=True, help='Site name')
@click.option('--source', required=True, help='Source app name')
@click.option('--host', required=True, help='Host/staging app name')
@click.option('--doctypes', default=None, help='Comma-separated doctype names (or all)')
@click.option('--prefix', default='STAGE_', help='Prefix for staged doctypes')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_stage(context, site, source, host, doctypes, prefix, dry_run):
    """Stage doctypes from source app to host app with prefix"""
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"📤 STAGING DOCTYPES [{mode}]")
    print(f"   Source: {source}")
    print(f"   Host: {host}")
    print(f"   Prefix: {prefix}")
    print("=" * 60)
    
    frappe.init(site=site)
    frappe.connect()
    
    # Get doctypes from source app
    if doctypes:
        dt_list = [d.strip() for d in doctypes.split(',')]
        source_doctypes = frappe.get_all("DocType", 
            filters={"name": ["in", dt_list]},
            fields=["name", "module"])
    else:
        source_doctypes = frappe.get_all("DocType", 
            filters={"module": source},
            fields=["name", "module"])
    
    print(f"\n📦 DOCTYPES TO STAGE ({len(source_doctypes)}):")
    staged = []
    
    for dt in source_doctypes:
        new_name = f"{prefix}{dt.name}"
        print(f"   • {dt.name} → {new_name}")
        staged.append({"old_name": dt.name, "new_name": new_name})
    
    if not dry_run:
        print(f"\n🔧 STAGING...")
        for item in staged:
            try:
                # Rename doctype
                frappe.rename_doc("DocType", item["old_name"], item["new_name"], force=True)
                # Update module
                frappe.db.sql("""
                    UPDATE `tabDocType` SET module = %s WHERE name = %s
                """, (host, item["new_name"]))
                print(f"   ✅ {item['old_name']} → {item['new_name']}")
            except Exception as e:
                print(f"   ❌ {item['old_name']}: {e}")
        
        frappe.db.commit()
        print(f"\n✅ Staged {len(staged)} doctypes to {host}")
        print(f"\n📋 After modifications, run:")
        print(f"   bench app-migrator-unstage --site {site} --host {host} --target <target_app> --prefix {prefix}")
    else:
        print(f"\n📋 Run with --apply to stage")
    
    frappe.db.close()

# ==================== PING-PONG STAGING: UNSTAGE DOCTYPES ====================

@click.command('app-migrator-unstage')
@click.option('--site', required=True, help='Site name')
@click.option('--host', required=True, help='Host/staging app name')
@click.option('--target', required=True, help='Target app name')
@click.option('--prefix', default='STAGE_', help='Prefix to remove')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_unstage(context, site, host, target, prefix, dry_run):
    """Unstage doctypes from host app to target app, removing prefix"""
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"📥 UNSTAGING DOCTYPES [{mode}]")
    print(f"   Host: {host}")
    print(f"   Target: {target}")
    print(f"   Prefix to remove: {prefix}")
    print("=" * 60)
    
    frappe.init(site=site)
    frappe.connect()
    
    # Get staged doctypes from host app
    host_doctypes = frappe.get_all("DocType", 
        filters={"module": host},
        fields=["name", "module"])
    
    # Filter to only prefixed ones
    staged_doctypes = [dt for dt in host_doctypes if dt.name.startswith(prefix)]
    
    print(f"\n📦 DOCTYPES TO UNSTAGE ({len(staged_doctypes)}):")
    unstaged = []
    
    for dt in staged_doctypes:
        original_name = dt.name[len(prefix):]  # Remove prefix
        print(f"   • {dt.name} → {original_name}")
        unstaged.append({"staged_name": dt.name, "original_name": original_name})
    
    if not dry_run:
        print(f"\n🔧 UNSTAGING...")
        for item in unstaged:
            try:
                # Rename doctype back
                frappe.rename_doc("DocType", item["staged_name"], item["original_name"], force=True)
                # Update module to target
                frappe.db.sql("""
                    UPDATE `tabDocType` SET module = %s WHERE name = %s
                """, (target, item["original_name"]))
                print(f"   ✅ {item['staged_name']} → {item['original_name']}")
            except Exception as e:
                print(f"   ❌ {item['staged_name']}: {e}")
        
        frappe.db.commit()
        print(f"\n✅ Unstaged {len(unstaged)} doctypes to {target}")
        print(f"\n📋 Now run: bench --site {site} migrate")
    else:
        print(f"\n📋 Run with --apply to unstage")
    
    frappe.db.close()

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
    app_migrator_unstage
]

print("✅ App Migrator Enterprise v9.0.0 ready!")
