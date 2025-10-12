"""App Migrator V5.2.0 Commands Module
Complete command module initialization

This module contains all migration commands for App Migrator V5.2.0
Merged from V2 and V4 with enhancements
"""

# Import version from parent module
from .. import __version__

# Import all command modules
from .doctype_classifier import (
    DoctypeStatus,
    get_doctype_classification,
    get_all_doctypes_by_app,
    get_all_custom_fields_by_app,
    get_all_property_setters_by_app,
    get_orphan_doctypes,
    analyze_touched_tables,
    generate_migration_risk_assessment,
    display_classification_summary,
    display_detailed_classifications
)

from .enhanced_interactive_wizard import (
    interactive_migration_wizard,
    guided_migration_workflow,
    select_site,
    list_apps_in_site,
    select_app,
    analyze_app_modules,
    filter_by_status
)

from .database_intel import (
    get_database_info,
    analyze_site_compatibility
)

from .data_quality import (
    fix_orphan_doctypes,
    restore_missing_doctypes,
    fix_app_none_doctypes,
    fix_all_references,
    verify_data_integrity
)

from .session_manager import (
    SessionManager,
    ensure_frappe_connection,
    with_session_management,
    with_session_tracking
)

from .migration_engine import (
    ProgressTracker,
    migrate_app_modules,
    migrate_specific_doctypes,
    move_module_files,
    validate_migration_readiness,
    clone_app_local,
    run_command_with_progress,
    monitor_directory_creation
)

from .analysis_tools import (
    analyze_bench_health,
    analyze_app_dependencies,
    analyze_app_comprehensive,
    detect_available_benches,
    get_bench_apps,
    multi_bench_analysis,
    get_directory_size,
    # Enhanced analysis functions
    analyze_app_security,
    analyze_performance_metrics,
    analyze_data_volume,
    generate_migration_report,
    compare_app_versions
)

from .progress_tracker import (
    ProgressTracker as ProgressTrackerV2,
    MultiStepProgressTracker,
    run_with_progress
)

# Import Intelligence Engine
try:
    from .intelligence_engine import (
        MigrationIntelligence,
        predict_migration_success,
        generate_intelligent_migration_plan,
        display_intelligence_dashboard
    )
    INTELLIGENCE_AVAILABLE = True
except ImportError as e:
    INTELLIGENCE_AVAILABLE = False
    print(f"⚠️  Intelligence Engine not available: {e}")

# Import Diagnostic Commands
try:
    from .diagnostic_commands import get_commands as get_diagnostic_commands
    DIAGNOSTICS_AVAILABLE = True
except ImportError as e:
    DIAGNOSTICS_AVAILABLE = False
    def get_diagnostic_commands():
        return []

# Re-export commonly used functions
__all__ = [
    # Version
    '__version__',
    
    # DocType Classifier
    'DoctypeStatus',
    'get_doctype_classification',
    'get_all_doctypes_by_app',
    'generate_migration_risk_assessment',
    
    # Interactive Wizard
    'interactive_migration_wizard',
    'guided_migration_workflow',
    
    # Database Schema
    'get_database_info',
    'analyze_site_compatibility',
    
    # Data Quality
    'fix_orphan_doctypes',
    'restore_missing_doctypes',
    'fix_app_none_doctypes',
    'fix_all_references',
    'verify_data_integrity',
    
    # Session Management
    'SessionManager',
    'ensure_frappe_connection',
    'with_session_management',
    
    # Migration Engine
    'migrate_app_modules',
    'migrate_specific_doctypes',
    'validate_migration_readiness',
    'clone_app_local',
    
    # Analysis Tools
    'analyze_bench_health',
    'analyze_app_comprehensive',
    'multi_bench_analysis',
    'analyze_app_security',
    'analyze_performance_metrics',
    'analyze_data_volume',
    'generate_migration_report',
    'compare_app_versions',
    
    # Progress Tracking
    'ProgressTracker',
    'MultiStepProgressTracker'
]

print(f"✅ App Migrator V{__version__} Commands Module loaded successfully!")

# ============================================================================
# ENHANCED COMMAND REGISTRY - All Commands
# ============================================================================

import click
import frappe

@click.command('migrate-app')
@click.argument('action', required=False)
@click.argument('source_app', required=False)
@click.argument('target_app', required=False)
@click.option('--modules', help='Specific modules to migrate')
@click.option('--site', help='Site name for operations')
@click.option('--session-id', help='Session ID for tracking')
@click.option('--bench-path', help='Specific bench path for analysis')
@click.option('--output-format', default='text', help='Output format: text, json, csv')
@click.option('--detailed', is_flag=True, help='Show detailed analysis')
@click.option('--fix', is_flag=True, help='Attempt to fix issues automatically')  # ADD THIS
@click.option('--dry-run', is_flag=True, help='Show what would be fixed without applying changes')  # ADD THIS
def migrate_app_command(action=None, source_app=None, target_app=None, modules=None, site=None, session_id=None, bench_path=None, output_format='text', detailed=False, fix=False, dry_run=False):  # ADD PARAMETERS
    """
    App Migrator v5.2.0 - Ultimate Edition with Intelligence
    """
    
    if not action:
        display_help()
        return
    
    print(f"🚀 App Migrator v{__version__}: {action}")
    
    # ===== DIAGNOSTIC COMMANDS =====
    if action == 'diagnose-app':
        if not source_app:
            print("❌ Please specify app path: bench --site <site> migrate-app diagnose-app <app_path>")
            return
        if DIAGNOSTICS_AVAILABLE:
            from .diagnostic_commands import diagnose_app
            return diagnose_app.callback(source_app, fix)  # PASS FIX PARAMETER
        else:
            print("❌ Diagnostic tools not available")
        return

    elif action == 'scan-bench-health':
        if DIAGNOSTICS_AVAILABLE:
            from .diagnostic_commands import scan_bench_health
            return scan_bench_health.callback()
        else:
            print("❌ Diagnostic tools not available")
        return

    elif action == 'quick-health-check':
        if not source_app:
            print("❌ Please specify app name: bench --site <site> migrate-app quick-health-check <app_name>")
            return
        if DIAGNOSTICS_AVAILABLE:
            from .diagnostic_commands import quick_health_check
            return quick_health_check.callback(source_app)
        else:
            print("❌ Diagnostic tools not available")
        return

    elif action == 'repair-bench-apps':  # ADD THIS NEW COMMAND
        if DIAGNOSTICS_AVAILABLE:
            from .diagnostic_commands import repair_bench_apps
            return repair_bench_apps.callback(dry_run)  # PASS DRY_RUN PARAMETER
        else:
            print("❌ Diagnostic tools not available")
        return

    # ===== INTELLIGENCE COMMANDS =====
    elif action == 'intelligence-dashboard':
        if INTELLIGENCE_AVAILABLE:
            display_intelligence_dashboard()
        else:
            print("❌ Intelligence Engine not available")
        return
        
    elif action == 'predict-success':
        if not source_app:
            print("❌ Please specify app name: bench --site <site> migrate-app predict-success <app_name>")
            return
        if INTELLIGENCE_AVAILABLE:
            report = predict_migration_success(source_app, target_app or source_app)
            print(f"🧠 Success Prediction: {report.get('success_probability', 'N/A')}%")
        else:
            print("❌ Intelligence Engine not available")
        return

def display_help():
    """Display comprehensive help for all enhanced commands"""
    print("\n" + "=" * 80)
    print("📚 APP MIGRATOR v5.2.0 - ULTIMATE EDITION WITH INTELLIGENCE")
    print("=" * 80)
    
    print("\n🩺 DIAGNOSTIC COMMANDS:")
    print("   diagnose-app <path>       - Analyze app health without installation")
    print("   scan-bench-health         - Scan health of all apps in bench")
    print("   quick-health-check <app>  - Quick health check for single app")
    print("   repair-bench-apps         - Batch repair all apps in bench")
    
    print("\n⚙️  OPTIONS:")
    print("   --detailed               - Show detailed analysis")
    print("   --output-format          - Output format: text, json, csv")
    print("   --bench-path             - Specific bench path for analysis")
    print("   --fix                    - Attempt to fix issues automatically")
    print("   --dry-run                - Show what would be fixed without applying changes")
    
    print("\n💡 EXAMPLES:")
    print("   bench --site mysite migrate-app diagnose-app /path/to/app --fix")
    print("   bench --site mysite migrate-app repair-bench-apps --dry-run")
    print("   bench --site mysite migrate-app repair-bench-apps")
    print("   bench --site mysite migrate-app scan-bench-health")
    print("\n" + "=" * 80)

    
# Register command for bench CLI
commands = [migrate_app_command]

