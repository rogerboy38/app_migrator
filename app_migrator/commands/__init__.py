"""
App Migrator Commands - Enterprise Edition
Version: 9.0.0
Merged: Original analysis + Enterprise multi-bench + Session management
"""

__version__ = "9.0.0"

import logging
logger = logging.getLogger("app_migrator")

# ONLY import the main class - no function imports!
from .analysis_tools import AppAnalysis

__all__ = ["AppAnalysis"]

logger.debug("App Migrator commands loaded")

# Payment Security/Gateway Migrators were digested into
# intelligence_engine.py in T1.5b and the originals archived to
# app_migrator/_archive/. See _archive/README.md for what was extracted.

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
# Helpers extracted to _shared.py in T1.8.1
from ._shared import (
    ProgressTracker,
    MigrationSession,
    get_current_site,
    detect_available_benches,
    get_bench_apps,
)

# ==================== HEALTH COMMAND (T1.8.2 → health.py) ====================
from .health import app_migrator_health

# ==================== SCAN SITE COMMAND (T1.8.2 → scan.py) ====================
from .scan import app_migrator_scan

# ==================== DETECT CONFLICTS COMMAND (T1.8.2 → conflicts.py) ====================
from .conflicts import app_migrator_conflicts

# ==================== GENERATE PLAN COMMAND (T1.8.2 → plan.py) ====================
from .plan import app_migrator_plan

# ==================== EXECUTE PLAN COMMAND (T1.8.2 → execute.py) ====================
from .execute import app_migrator_execute

# ==================== ENTERPRISE: LIST BENCHES (T1.8.2 → benches.py) ====================
from .benches import app_migrator_benches

# ==================== ENTERPRISE: SESSION MANAGEMENT (T1.8.3 → session.py) ====================
from .session import app_migrator_session_start, app_migrator_session_status

# ==================== LIST APPS (DOWNLOADED VS INSTALLED) (T1.8.2 → apps.py) ====================
from .apps import app_migrator_apps

# ==================== FIX ORPHAN DOCTYPES ====================

@click.command('app-migrator-fix-orphans')
@click.option('--site', required=True, help='Site name')
@click.option('--target-module', default=None, help='Target module for orphans')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def app_migrator_fix_orphans(context, site, target_module, dry_run):
    """[DEPRECATED] Fix orphan doctypes — use 'orphans --fix --apply' instead (will be removed in v11)"""
    click.echo("⚠️  DEPRECATED: 'fix-orphans' is deprecated and will be removed in v11.")
    click.echo("   Use 'bench app-migrator orphans --fix --apply' instead.")
    click.echo("")
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

# ==================== CREATE HOST COMMAND (T1.8.3 → create_host.py) ====================
from .create_host import app_migrator_create_host

# ==================== STAGE COMMAND (T1.8.3 → stage.py) ====================
from .stage import app_migrator_stage

# ==================== UNSTAGE COMMAND (T1.8.3 → unstage.py) ====================
from .unstage import app_migrator_unstage

# ==================== FIX STRUCTURE COMMAND (T1.8.3 → fix_structure.py) ====================
from .fix_structure import app_migrator_fix_structure

# ==================== ENSURE CONTROLLERS COMMAND (T1.8.3 → ensure_controllers.py) ====================
from .ensure_controllers import app_migrator_ensure_controllers

# ==================== FIX APP FIELD COMMAND (T1.8.3 → fix_app_field.py) ====================
from .fix_app_field import app_migrator_fix_app_field

# ==================== FIX JSON APP COMMAND (T1.8.3 → fix_json_app.py) ====================
from .fix_json_app import app_migrator_fix_json_app

# ==================== RESOLVE DUPLICATES COMMAND (T1.8.3 → resolve_duplicates.py) ====================
from .resolve_duplicates import app_migrator_resolve_duplicates

# ==================== ORPHANS COMMAND (T1.8.3 → orphans.py) ====================
from .orphans import app_migrator_orphans

# ==================== MAIN GROUP COMMAND ====================

@click.group('app-migrator', invoke_without_command=True)
@click.pass_context
def app_migrator(ctx):
    """App Migrator Enterprise - Multi-bench migration toolkit"""
    if ctx.invoked_subcommand is None:
        # Show custom help when no subcommand
        click.echo("""
╔═══════════════════════════════════════════════════════╗
║       🚀 APP MIGRATOR ENTERPRISE v9.0.0 🚀            ║
║   Multi-bench, multi-site migration toolkit           ║
╚═══════════════════════════════════════════════════════╝

QUICK START:
  setup-wizard        Interactive setup wizard
  health              Check system health

SITE ANALYSIS:
  scan                Scan site inventory
  conflicts           Detect app conflicts
  apps                Downloaded vs installed apps

MIGRATION:
  plan                Generate migration plan
  execute             Execute migration plan

PING-PONG STAGING:
  create-host         Create staging app
  stage               Stage doctypes to host
  unstage             Unstage to target

INTELLIGENCE (AI-Powered):
  predict-success     Predict migration success
  generate-plan       Generate intelligent plan
  diagnose            Comprehensive app diagnosis
  modernize           Upgrade to pyproject.toml

FIXES & DIAGNOSTICS:
  orphans             🆕 Intelligent orphan detection & resolution
  analyze             Analyze app structure
  fix-orphans         Fix orphan doctypes (legacy)
  fix-structure       Analyze folder structure
  fix-app-field       Fix NULL app field in DB
  fix-json-app        Fix app field in JSON
  ensure-controllers  Create missing .py files
  resolve-duplicates  Remove duplicate doctypes between apps

ENTERPRISE:
  benches             List all available benches
  session-start       Start migration session
  session-status      Check session status

Usage: bench app-migrator <command> [options]
Help:  bench app-migrator <command> --help
""")

# ==================== INTELLIGENCE COMMANDS ====================

from .intelligence import predict_success, generate_intelligent_plan, diagnose_app
from .modernize import modernize_app
from .git_push import git_push
from .git_pull import git_pull
from .git_utils import get_app_info, FrappeCloudAPI, clone_app_from_git, convert_to_git_repo
from .git_info import git_info
from .api_key_manager import api_key_setup, api_key_status, api_key_cleanup
from .setup.wizard import setup_wizard
from .fix_module_naming import fix_module_names, standardize_modules
from .fix_orphan_specific import fix_alexa_orphan
from .fix_orphan_modules import fix_orphan_modules
from .fix_amb_w_tds2_orphans import fix_amb_w_tds2
from .fix_kpi_factors_validation import fix_kpi_factors
from .module_diagnostic import module_diagnostic
from .simple_api_setup import simple_api_setup

# Add subcommands to the group
app_migrator.add_command(app_migrator_health, 'health')
app_migrator.add_command(app_migrator_scan, 'scan')
app_migrator.add_command(app_migrator_conflicts, 'conflicts')
app_migrator.add_command(app_migrator_plan, 'plan')
app_migrator.add_command(app_migrator_execute, 'execute')
app_migrator.add_command(app_migrator_benches, 'benches')
app_migrator.add_command(app_migrator_session_start, 'session-start')
app_migrator.add_command(app_migrator_session_status, 'session-status')
app_migrator.add_command(app_migrator_apps, 'apps')
app_migrator.add_command(app_migrator_fix_orphans, 'fix-orphans')
app_migrator.add_command(app_migrator_analyze, 'analyze')
app_migrator.add_command(app_migrator_create_host, 'create-host')
app_migrator.add_command(app_migrator_stage, 'stage')
app_migrator.add_command(app_migrator_unstage, 'unstage')
app_migrator.add_command(app_migrator_fix_structure, 'fix-structure')
app_migrator.add_command(app_migrator_ensure_controllers, 'ensure-controllers')
app_migrator.add_command(app_migrator_fix_app_field, 'fix-app-field')
app_migrator.add_command(app_migrator_fix_json_app, 'fix-json-app')
app_migrator.add_command(app_migrator_resolve_duplicates, 'resolve-duplicates')
app_migrator.add_command(app_migrator_orphans, 'orphans')
app_migrator.add_command(fix_module_names, "fix-module-names")
app_migrator.add_command(standardize_modules, "standardize-modules")
app_migrator.add_command(module_diagnostic, "module-diagnostic")
app_migrator.add_command(fix_alexa_orphan, "fix-alexa-orphan")
app_migrator.add_command(fix_orphan_modules, "fix-modules")
app_migrator.add_command(fix_amb_w_tds2, "fix-amb-w-tds2")
app_migrator.add_command(fix_kpi_factors, "fix-kpi-factors")

app_migrator.add_command(predict_success, 'predict-success')
app_migrator.add_command(generate_intelligent_plan, 'generate-plan')
app_migrator.add_command(diagnose_app, 'diagnose')
app_migrator.add_command(modernize_app, 'modernize')
app_migrator.add_command(git_push, "git-push")
app_migrator.add_command(git_pull, "git-pull")
app_migrator.add_command(api_key_cleanup, "api-key-cleanup")
app_migrator.add_command(api_key_status, "api-key-status")
app_migrator.add_command(api_key_setup, "api-key-setup")
app_migrator.add_command(git_info, "git-info")
app_migrator.add_command(setup_wizard,"setup-wizard")
app_migrator.add_command(simple_api_setup, 'simple-api-setup')

# ==================== EXPORT ALL COMMANDS ====================

commands = [
    app_migrator,  # Main group command
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
    app_migrator_fix_json_app,
    app_migrator_orphans,
    # Intelligence commands
    predict_success,
    generate_intelligent_plan,
    diagnose_app,
    modernize_app,
    
    setup_wizard
    ]

logger.debug("App Migrator Enterprise v%s ready", __version__)

# Git push command

# Analyze commands
from app_migrator.commands.analyze.apps import analyze_apps
