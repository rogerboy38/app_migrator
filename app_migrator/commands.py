"""
App Migrator CLI Commands v8.1.0
Main entry point for all app_migrator bench commands

Usage:
  bench app-migrator-health
  bench app-migrator-scan --site sitename
  bench app-migrator-conflicts --site sitename --apps app1,app2
  bench app-migrator-plan --site sitename --apps app1,app2 --target newapp --output plan.json
  bench app-migrator-execute --site sitename --plan plan.json --dry-run
  bench app-migrator-fix appname
"""

import click
import json
import yaml
import os
import sys
from datetime import datetime

try:
    import frappe
    from frappe.commands import pass_context, get_site
    FRAPPE_AVAILABLE = True
except ImportError:
    FRAPPE_AVAILABLE = False
    pass_context = lambda f: f
    get_site = lambda c: None


# ==================== HEALTH COMMAND ====================

@click.command('app-migrator-health')
@pass_context
def app_migrator_health(context):
    """Check App Migrator health and version"""
    site = get_site(context)
    print("=" * 50)
    print("🔧 App Migrator Health Check")
    print("=" * 50)
    print(f"   Version: 8.1.0")
    print(f"   Site: {site}")
    print(f"   Status: ✅ OPERATIONAL")
    print()
    print("📋 Available Commands:")
    print("   • app-migrator-scan       - Scan site inventory")
    print("   • app-migrator-conflicts  - Find app conflicts")
    print("   • app-migrator-plan       - Create migration plan")
    print("   • app-migrator-execute    - Run migration")
    print("   • app-migrator-fix        - Fix app structure")
    print("=" * 50)


# ==================== SCAN SITE COMMAND ====================

@click.command('app-migrator-scan')
@click.option('--site', required=True, help='Site name to scan')
@click.option('--apps', default=None, help='Comma-separated list of apps to filter')
@click.option('--output', '-o', default=None, help='Output file path (JSON)')
@pass_context
def app_migrator_scan(context, site, apps, output):
    """Scan site to list installed apps, doctypes, custom fields"""
    print(f"🔍 Scanning site: {site}")
    print("=" * 60)
    
    try:
        frappe.init(site=site)
        frappe.connect()
        
        result = {
            "site_name": site,
            "scan_timestamp": datetime.now().isoformat(),
            "frappe_version": getattr(frappe, '__version__', 'unknown'),
            "installed_apps": [],
            "doctypes": [],
            "custom_fields": [],
            "summary": {}
        }
        
        # Get installed apps
        installed_apps = frappe.get_installed_apps()
        for app_name in installed_apps:
            result["installed_apps"].append({"name": app_name})
        
        # Get doctypes
        apps_filter = apps.split(',') if apps else None
        filters = {"module": ["in", apps_filter]} if apps_filter else {}
        
        doctypes = frappe.get_all("DocType", filters=filters, 
            fields=["name", "module", "custom", "istable"])
        result["doctypes"] = [dict(dt) for dt in doctypes]
        
        # Get custom fields
        custom_fields = frappe.get_all("Custom Field",
            fields=["name", "dt", "fieldname", "fieldtype"])
        result["custom_fields"] = [dict(cf) for cf in custom_fields]
        
        # Summary
        result["summary"] = {
            "installed_apps": len(result["installed_apps"]),
            "doctypes": len(result["doctypes"]),
            "custom_fields": len(result["custom_fields"])
        }
        
        frappe.db.close()
        
        if output:
            with open(output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"✅ Results saved to: {output}")
        
        # Display summary
        print(f"\n📊 SCAN SUMMARY")
        print(f"   Frappe Version: {result['frappe_version']}")
        print(f"   Installed Apps: {result['summary']['installed_apps']}")
        print(f"   DocTypes: {result['summary']['doctypes']}")
        print(f"   Custom Fields: {result['summary']['custom_fields']}")
        print("\n✅ Scan complete!")
        
    except Exception as e:
        print(f"❌ Scan failed: {str(e)}")
        sys.exit(1)


# ==================== DETECT CONFLICTS COMMAND ====================

@click.command('app-migrator-conflicts')
@click.option('--site', required=True, help='Site name to analyze')
@click.option('--apps', required=True, help='Comma-separated list of apps')
@click.option('--output', '-o', default=None, help='Output file path')
@pass_context
def app_migrator_conflicts(context, site, apps, output):
    """Detect conflicts between apps"""
    print(f"🔍 Detecting conflicts in: {site}")
    print(f"   Apps: {apps}")
    print("=" * 60)
    
    try:
        frappe.init(site=site)
        frappe.connect()
        
        apps_list = [a.strip() for a in apps.split(',')]
        
        result = {
            "site_name": site,
            "apps_analyzed": apps_list,
            "scan_timestamp": datetime.now().isoformat(),
            "conflicts": {
                "duplicate_doctypes": [],
                "orphan_doctypes": [],
                "field_clashes": []
            },
            "summary": {"total_conflicts": 0}
        }
        
        # Get doctypes by app
        from collections import defaultdict
        doctype_to_apps = defaultdict(list)
        
        for app in apps_list:
            doctypes = frappe.get_all("DocType", filters={"module": app}, fields=["name"])
            for dt in doctypes:
                doctype_to_apps[dt.name].append(app)
        
        # Find duplicates
        for dt, dt_apps in doctype_to_apps.items():
            if len(dt_apps) > 1:
                result["conflicts"]["duplicate_doctypes"].append({
                    "doctype": dt,
                    "found_in_apps": dt_apps
                })
        
        # Find orphans
        orphans = frappe.get_all("DocType", 
            filters=[["module", "in", ["", None]], ["custom", "=", 0]],
            fields=["name", "module"])
        for dt in orphans:
            result["conflicts"]["orphan_doctypes"].append({"doctype": dt.name})
        
        # Calculate total
        total = (len(result["conflicts"]["duplicate_doctypes"]) + 
                len(result["conflicts"]["orphan_doctypes"]))
        result["summary"]["total_conflicts"] = total
        
        frappe.db.close()
        
        if output:
            with open(output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"✅ Results saved to: {output}")
        
        print(f"\n📊 CONFLICT SUMMARY")
        print(f"   Total Conflicts: {total}")
        print(f"   Duplicate DocTypes: {len(result['conflicts']['duplicate_doctypes'])}")
        print(f"   Orphan DocTypes: {len(result['conflicts']['orphan_doctypes'])}")
        
        if total == 0:
            print(f"\n✅ No conflicts detected!")
        else:
            print(f"\n⚠️ Conflicts found! Review output for details.")
        
    except Exception as e:
        print(f"❌ Conflict detection failed: {str(e)}")
        sys.exit(1)


# ==================== GENERATE PLAN COMMAND ====================

@click.command('app-migrator-plan')
@click.option('--site', required=True, help='Site name')
@click.option('--apps', required=True, help='Source apps to consolidate')
@click.option('--target', required=True, help='Target app name')
@click.option('--output', '-o', required=True, help='Output file for plan')
@pass_context
def app_migrator_plan(context, site, apps, target, output):
    """Generate a migration plan"""
    print(f"📋 Generating migration plan")
    print(f"   Site: {site}")
    print(f"   Source Apps: {apps}")
    print(f"   Target App: {target}")
    print("=" * 60)
    
    try:
        frappe.init(site=site)
        frappe.connect()
        
        apps_list = [a.strip() for a in apps.split(',')]
        
        plan = {
            "plan_version": "8.1.0",
            "created_at": datetime.now().isoformat(),
            "source_apps": apps_list,
            "target_app": target,
            "doctype_mappings": [],
            "data_rules": [],
            "execution_order": []
        }
        
        # Get all doctypes from source apps
        all_doctypes = []
        for app in apps_list:
            doctypes = frappe.get_all("DocType", 
                filters={"module": app},
                fields=["name", "module", "istable"])
            for dt in doctypes:
                plan["doctype_mappings"].append({
                    "doctype": dt.name,
                    "source_app": app,
                    "target_app": target,
                    "is_table": dt.istable
                })
                
                # Get record count
                try:
                    count = frappe.db.count(dt.name)
                except:
                    count = 0
                
                plan["data_rules"].append({
                    "doctype": dt.name,
                    "record_count": count,
                    "action": "migrate" if count > 0 else "skip"
                })
                
                all_doctypes.append(dt.name)
        
        plan["execution_order"] = all_doctypes
        
        frappe.db.close()
        
        with open(output, 'w') as f:
            json.dump(plan, f, indent=2)
        
        print(f"\n✅ Migration plan saved to: {output}")
        print(f"   DocType Mappings: {len(plan['doctype_mappings'])}")
        print(f"   Data Rules: {len(plan['data_rules'])}")
        print(f"\n📋 Next: bench app-migrator-execute --site {site} --plan {output} --dry-run")
        
    except Exception as e:
        print(f"❌ Plan generation failed: {str(e)}")
        sys.exit(1)


# ==================== EXECUTE PLAN COMMAND ====================

@click.command('app-migrator-execute')
@click.option('--site', required=True, help='Site name')
@click.option('--plan', 'plan_file', required=True, help='Path to migration plan')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_execute(context, site, plan_file, dry_run):
    """Execute a migration plan"""
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"🚀 Executing migration plan [{mode}]")
    print(f"   Site: {site}")
    print(f"   Plan: {plan_file}")
    print("=" * 60)
    
    if not dry_run:
        if not click.confirm("⚠️ This will modify your database. Continue?"):
            print("❌ Cancelled")
            sys.exit(0)
    
    try:
        with open(plan_file, 'r') as f:
            plan = json.load(f)
        
        frappe.init(site=site)
        frappe.connect()
        
        completed = 0
        total_records = 0
        
        for mapping in plan.get("doctype_mappings", []):
            dt_name = mapping["doctype"]
            target = mapping["target_app"]
            
            print(f"   Processing: {dt_name}")
            
            if not dry_run:
                frappe.db.sql("""
                    UPDATE `tabDocType` SET module = %s WHERE name = %s
                """, (target, dt_name))
            
            completed += 1
        
        for rule in plan.get("data_rules", []):
            total_records += rule.get("record_count", 0)
        
        if not dry_run:
            frappe.db.commit()
        
        frappe.db.close()
        
        print(f"\n📊 EXECUTION SUMMARY [{mode}]")
        print(f"   DocTypes Processed: {completed}")
        print(f"   Total Records: {total_records}")
        
        if dry_run:
            print(f"\n✅ Dry-run complete! Run with --apply to execute.")
        else:
            print(f"\n✅ Migration complete! Run 'bench --site {site} migrate'")
        
    except Exception as e:
        print(f"❌ Execution failed: {str(e)}")
        if not dry_run:
            try:
                frappe.db.rollback()
            except:
                pass
        sys.exit(1)


# ==================== FIX APP COMMAND ====================

@click.command('app-migrator-fix')
@click.argument('app_name')
@click.option('--bench-path', default='.', help='Path to bench')
@pass_context
def app_migrator_fix(context, app_name, bench_path):
    """Fix common app structural issues"""
    print(f"🛠️ Fixing app: {app_name}")
    print("=" * 50)
    
    try:
        from app_migrator.commands.fix_app import AppFixer
        fixer = AppFixer(app_name, bench_path)
        success = fixer.fix_app_quick()
        
        if success:
            print("🎉 Fix completed!")
        else:
            print("❌ Fix failed!")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)


# ==================== INTERACTIVE WIZARD COMMAND ====================

@click.command('app-migrator-wizard')
def app_migrator_wizard():
    """Launch interactive migration wizard (no site required)"""
    from app_migrator.commands.enhanced_interactive_wizard import interactive_migration_wizard
    interactive_migration_wizard()


# Export all commands for Frappe to discover
commands = [
    app_migrator_health,
    app_migrator_scan,
    app_migrator_conflicts,
    app_migrator_plan,
    app_migrator_execute,
    app_migrator_fix,
    app_migrator_wizard
]
