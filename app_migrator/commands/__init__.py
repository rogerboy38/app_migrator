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
    print("    app-migrator-session-start <name>        Start session")
    print("    app-migrator-session-status <id>         Check session")
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

# ==================== EXPORT ALL COMMANDS ====================

commands = [
    app_migrator_health,
    app_migrator_scan,
    app_migrator_conflicts,
    app_migrator_plan,
    app_migrator_execute,
    app_migrator_benches,
    app_migrator_session_start,
    app_migrator_session_status
]

print("✅ App Migrator Enterprise v9.0.0 ready!")
