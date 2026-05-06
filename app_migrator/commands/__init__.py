"""
App Migrator Commands
Version: 10.0.0-rc1
Merged: Original analysis + multi-bench + Session management
"""

__version__ = "10.0.0-rc1"

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
import json
import os
import subprocess
import sys
import time
from datetime import datetime

import click

try:
    import frappe
    from frappe.commands import pass_context
    FRAPPE_AVAILABLE = True
except ImportError:
    FRAPPE_AVAILABLE = False
    def pass_context(f):
        return f
# ==================== UTILITIES ====================
# Helpers extracted to _shared.py in T1.8.1
# ==================== FIX ORPHAN DOCTYPES [DEPRECATED] (T1.8.5 → _legacy/fix_orphans.py) ====================
from ._legacy.fix_orphans import app_migrator_fix_orphans
from ._shared import (
    MigrationSession,
    ProgressTracker,
    detect_available_benches,
    get_bench_apps,
    get_current_site,
)

# ==================== ANALYZE APP STRUCTURE (T1.8.4 → analyze_cmd.py) ====================
from .analyze_cmd import app_migrator_analyze

# ==================== LIST APPS (DOWNLOADED VS INSTALLED) (T1.8.2 → apps.py) ====================
from .apps import app_migrator_apps

# ==================== LIST BENCHES (T1.8.2 → benches.py) ====================
from .benches import app_migrator_benches

# ==================== DETECT CONFLICTS COMMAND (T1.8.2 → conflicts.py) ====================
from .conflicts import app_migrator_conflicts

# ==================== CREATE HOST COMMAND (T1.8.3 → create_host.py) ====================
from .create_host import app_migrator_create_host

# ==================== ENSURE CONTROLLERS COMMAND (T1.8.3 → ensure_controllers.py) ====================
from .ensure_controllers import app_migrator_ensure_controllers

# ==================== EXECUTE PLAN COMMAND (T1.8.2 → execute.py) ====================
from .execute import app_migrator_execute

# ==================== FIX APP FIELD COMMAND (T1.8.3 → fix_app_field.py) ====================
from .fix_app_field import app_migrator_fix_app_field

# ==================== FIX JSON APP COMMAND (T1.8.3 → fix_json_app.py) ====================
from .fix_json_app import app_migrator_fix_json_app

# ==================== FIX STRUCTURE COMMAND (T1.8.3 → fix_structure.py) ====================
from .fix_structure import app_migrator_fix_structure

# ==================== HEALTH COMMAND (T1.8.2 → health.py) ====================
from .health import app_migrator_health

# ==================== ORPHANS COMMAND (T1.8.3 → orphans.py) ====================
from .orphans import app_migrator_orphans

# ==================== GENERATE PLAN COMMAND (T1.8.2 → plan.py) ====================
from .plan import app_migrator_plan

# ==================== RESOLVE DUPLICATES COMMAND (T1.8.3 → resolve_duplicates.py) ====================
from .resolve_duplicates import app_migrator_resolve_duplicates

# ==================== SCAN SITE COMMAND (T1.8.2 → scan.py) ====================
from .scan import app_migrator_scan

# ==================== SESSION MANAGEMENT (T1.8.3 → session.py) ====================
from .session import app_migrator_session_start, app_migrator_session_status

# ==================== STAGE COMMAND (T1.8.3 → stage.py) ====================
from .stage import app_migrator_stage

# ==================== UNSTAGE COMMAND (T1.8.3 → unstage.py) ====================
from .unstage import app_migrator_unstage
from .promote_custom_doctype import app_migrator_promote_custom_doctype
from .scan_donor_residue import app_migrator_scan_donor_residue
from .verify_donor_cleanup_readiness import app_migrator_verify_donor_cleanup_readiness
from .audit_app_for_antipattern import app_migrator_audit_app_for_antipattern
from .audit_orphan_doctypes import app_migrator_audit_orphan_doctypes
from .new_fresh_app import app_migrator_new_fresh_app
from .migrate_module import app_migrator_migrate_module
from .denest_app import app_migrator_denest_app

# ==================== MAIN GROUP COMMAND ====================

@click.group('app-migrator', invoke_without_command=True)
@click.pass_context
def app_migrator(ctx):
    """App Migrator - Multi-bench migration toolkit"""
    if ctx.invoked_subcommand is None:
        # Show custom help when no subcommand
        click.echo(f"""
╔═══════════════════════════════════════════════════════╗
║   🚀 APP MIGRATOR v{__version__} 🚀
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

MULTI-BENCH:
  benches             List all available benches
  session-start       Start migration session
  session-status      Check session status

Usage: bench app-migrator <command> [options]
Help:  bench app-migrator <command> --help
""")

# ==================== INTELLIGENCE COMMANDS ====================

from .analyze.apps import analyze_apps
from .api_key_manager import api_key_cleanup, api_key_setup, api_key_status
from .fix_amb_w_tds2_orphans import fix_amb_w_tds2
from .fix_kpi_factors_validation import fix_kpi_factors
from .fix_module_naming import fix_module_names, standardize_modules
from .fix_orphan_modules import fix_orphan_modules
from .fix_orphan_specific import fix_alexa_orphan
from .git_info import git_info
from .git_pull import git_pull
from .git_push import git_push
from .git_utils import FrappeCloudAPI, clone_app_from_git, convert_to_git_repo, get_app_info
from .intelligence import diagnose_app, generate_intelligent_plan, predict_success
from .modernize import modernize_app
from .module_diagnostic import module_diagnostic
from .setup.wizard import setup_wizard
from .simple_api_setup import quick_setup, simple_api_setup

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
app_migrator.add_command(analyze_apps, 'analyze-apps')
app_migrator.add_command(quick_setup, 'quick-setup')
app_migrator.add_command(app_migrator_promote_custom_doctype, 'promote-custom-doctype')
app_migrator.add_command(app_migrator_scan_donor_residue, 'scan-donor-residue')
app_migrator.add_command(app_migrator_verify_donor_cleanup_readiness, 'verify-donor-cleanup-readiness')
app_migrator.add_command(app_migrator_audit_app_for_antipattern, 'audit-app-for-antipattern')
app_migrator.add_command(app_migrator_audit_orphan_doctypes, 'audit-orphan-doctypes')
app_migrator.add_command(app_migrator_new_fresh_app, 'new-fresh-app')
app_migrator.add_command(app_migrator_migrate_module, 'migrate-module')
app_migrator.add_command(app_migrator_denest_app, 'denest-app')

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
    app_migrator_resolve_duplicates,
    # Intelligence commands
    predict_success,
    generate_intelligent_plan,
    diagnose_app,
    modernize_app,

    setup_wizard,
    app_migrator_promote_custom_doctype,
    app_migrator_scan_donor_residue,
    app_migrator_verify_donor_cleanup_readiness,
    ]

logger.debug("App Migrator v%s ready", __version__)

# Git push command

# Analyze commands
