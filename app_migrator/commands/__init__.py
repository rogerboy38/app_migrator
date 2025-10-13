"""App Migrator Commands Module
Complete command module initialization for App Migrator
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
    from .diagnostic_commands import (
        diagnose_app_callback,
        scan_bench_health_callback,
        quick_health_check_callback,
        repair_bench_apps_callback
    )
    DIAGNOSTICS_AVAILABLE = True
except ImportError as e:
    DIAGNOSTICS_AVAILABLE = False
    print(f"⚠️  Diagnostic commands not available: {e}")
    
    # Create dummy callbacks
    def diagnose_app_callback(app_path, fix=False):
        print("❌ Diagnostic tools not available")
    
    def scan_bench_health_callback():
        print("❌ Diagnostic tools not available")
    
    def quick_health_check_callback(app_name):
        print("❌ Diagnostic tools not available")
    
    def repair_bench_apps_callback(dry_run=False):
        print("❌ Diagnostic tools not available")

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
    'MultiStepProgressTracker',
    
    # Diagnostic Commands
    'diagnose_app_callback',
    'scan_bench_health_callback',
    'quick_health_check_callback',
    'repair_bench_apps_callback'
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
@click.option('--fix', is_flag=True, help='Attempt to fix issues automatically')
@click.option('--dry-run', is_flag=True, help='Show what would be fixed without applying changes')
def migrate_app_command(action=None, source_app=None, target_app=None, modules=None, site=None, session_id=None, bench_path=None, output_format='text', detailed=False, fix=False, dry_run=False):
    """
    App Migrator {version} - Ultimate Edition with Enhanced Diagnostics
    
    Complete Frappe app migration system with enhanced commands and predictive analytics
    
    Usage:
        bench --site <site> migrate-app <command> [args]
    
    Examples:
        bench --site mysite migrate-app interactive
        bench --site mysite migrate-app list-benches
        bench --site mysite migrate-app analyze myapp
        bench --site mysite migrate-app intelligence-dashboard
    """.format(version=__version__)
    
    if not action:
        display_help()
        return
    
    print(f"🚀 App Migrator v{__version__}: {action}")
    
    # ===== INTELLIGENCE COMMANDS =====
    if action == 'intelligence-dashboard':
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
        else:
            print("❌ Intelligence Engine not available")
        return

    elif action == 'intelligent-validate':
        if not source_app or not target_app:
            print("❌ Please specify source and target apps: bench --site <site> migrate-app intelligent-validate <source> <target>")
            return
        if INTELLIGENCE_AVAILABLE:
            intelligence = MigrationIntelligence()
            intelligence.intelligent_validate_migration(source_app, target_app)
        else:
            print("❌ Intelligence Engine not available")
        return

    elif action == 'generate-intelligent-plan':
        if not source_app or not target_app:
            print("❌ Please specify source and target apps: bench --site <site> migrate-app generate-intelligent-plan <source> <target>")
            return
        if INTELLIGENCE_AVAILABLE:
            plan = generate_intelligent_migration_plan(source_app, target_app)
            print("🧠 Generated Intelligent Migration Plan:")
            import json
            print(json.dumps(plan, indent=2))
        else:
            print("❌ Intelligence Engine not available")
        return

    elif action == 'prevent-issues':
        if not source_app:
            print("❌ Please specify app name: bench --site <site> migrate-app prevent-issues <app_name>")
            return
        if INTELLIGENCE_AVAILABLE:
            intelligence = MigrationIntelligence()
            prevention_report = intelligence.prevent_issues_before_migration(source_app)
            print("🛡️ Prevention Report:")
            import json
            print(json.dumps(prevention_report, indent=2))
        else:
            print("❌ Intelligence Engine not available")
        return
    
    # ===== DIAGNOSTIC COMMANDS =====
    elif action == 'diagnose-app':
        if not source_app:
            print("❌ Please specify app path: bench --site <site> migrate-app diagnose-app <app_path>")
            return
        return diagnose_app_callback(source_app, fix=fix)

    elif action == 'scan-bench-health':
        return scan_bench_health_callback()

    elif action == 'quick-health-check':
        if not source_app:
            print("❌ Please specify app name: bench --site <site> migrate-app quick-health-check <app_name>")
            return
        return quick_health_check_callback(source_app)

    elif action == 'repair-bench-apps':
        return repair_bench_apps_callback(dry_run=dry_run)

    elif action == 'health-report':
        if not source_app:
            print("❌ Please specify app name: bench --site <site> migrate-app health-report <app_name>")
            return
        from .app_health_scanner import quick_health_check_function
        return quick_health_check_function(source_app)

    # ===== AI INTEGRATION COMMANDS =====
    elif action == 'ai-migrate':
        if not source_app:
            print("❌ Please specify your query: bench --site <site> migrate-app ai-migrate \"your natural language query\"")
            return
        try:
            from .ai_integration import AppMigratorAIAgent
            agent = AppMigratorAIAgent()
            result = agent.parse_and_execute(source_app)
            
            if result.get('success'):
                print(f"✅ AI Command Result:\n{result['output']}")
            else:
                print(f"❌ AI Command Failed:\n{result.get('error', 'Unknown error')}")
                
        except ImportError:
            print("❌ AI integration not available. Make sure ai_integration.py exists.")
        except Exception as e:
            print(f"❌ AI command error: {str(e)}")
        return

    # ===== INTERACTIVE COMMANDS =====
    elif action == 'interactive':
        interactive_migration_wizard()
        
    # ===== MULTI-BENCH COMMANDS =====
    elif action == 'multi-bench-analysis':
        multi_bench_analysis(bench_path)
        
    elif action == 'list-benches':
        benches = detect_available_benches()
        print("\n🏗️  AVAILABLE BENCHES:")
        for idx, bench in enumerate(benches, 1):
            print(f"   {idx}. {bench}")
        
    elif action == 'bench-apps':
        if not source_app:
            print("❌ Please specify bench name: bench --site <site> migrate-app bench-apps <bench_name>")
            return
        apps = get_bench_apps(source_app)
        print(f"\n📦 APPS IN {source_app}:")
        for idx, app in enumerate(apps, 1):
            print(f"   {idx}. {app}")
        
    elif action == 'bench-health':
        analyze_bench_health(bench_path)
        
    # ===== DATABASE COMMANDS =====
    elif action == 'fix-database-schema':
        from .database_schema import fix_database_schema
        fix_database_schema()
        
    elif action == 'complete-erpnext-install':
        from .database_schema import complete_erpnext_install
        complete_erpnext_install()
        
    elif action == 'fix-tree-doctypes':
        from .database_schema import fix_tree_doctypes
        fix_tree_doctypes()
        
    elif action == 'db-diagnostics':
        from .database_schema import run_database_diagnostics
        run_database_diagnostics()
        
    # ===== ENHANCED ANALYSIS COMMANDS =====
    elif action == 'analyze':
        if not source_app:
            print("❌ Please specify app name: bench --site <site> migrate-app analyze <app_name>")
            return
        analyze_app_comprehensive(source_app, detailed=detailed)
        
    elif action == 'security-analysis':
        if not source_app:
            print("❌ Please specify app name: bench --site <site> migrate-app security-analysis <app_name>")
            return
        analyze_app_security(source_app, output_format=output_format)
        
    elif action == 'performance':
        if not source_app:
            print("❌ Please specify app name: bench --site <site> migrate-app performance <app_name>")
            return
        analyze_performance_metrics(source_app, output_format=output_format)
        
    elif action == 'data-volume':
        if not source_app:
            print("❌ Please specify app name: bench --site <site> migrate-app data-volume <app_name>")
            return
        analyze_data_volume(source_app, output_format=output_format)
        
    elif action == 'compare-versions':
        if not source_app:
            print("❌ Please specify app name: bench --site <site> migrate-app compare-versions <app_name>")
            return
        compare_app_versions(source_app, target_app)
        
    elif action == 'generate-report':
        if not source_app:
            print("❌ Please specify app name: bench --site <site> migrate-app generate-report <app_name>")
            return
        generate_migration_report(source_app, output_format=output_format)
        
    elif action == 'analyze-orphans':
        orphans = get_orphan_doctypes()
        print(f"\n⚠️  ORPHAN DOCTYPES: {len(orphans)}")
        for orphan in orphans[:20]:
            print(f"   - {orphan.get('name')}: {orphan.get('status')}")
        
    elif action == 'validate-migration':
        if not source_app:
            print("❌ Please specify app name")
            return
        validate_migration_readiness(source_app)
        
    elif action == 'classify-doctypes':
        if not source_app:
            print("❌ Please specify app name")
            return
        classifications = get_all_doctypes_by_app(source_app)
        display_classification_summary(classifications)
        if detailed:
            display_detailed_classifications(classifications)
        else:
            display_detailed_classifications(classifications, limit=20)
        
    # ===== DATA QUALITY COMMANDS =====
    elif action == 'fix-orphans':
        if not source_app:
            print("❌ Please specify app name")
            return
        fix_orphan_doctypes(source_app)
        
    elif action == 'restore-missing':
        if not source_app:
            print("❌ Please specify app name")
            return
        restore_missing_doctypes(source_app)
        
    elif action == 'fix-app-none':
        if not source_app:
            print("❌ Please specify app name")
            return
        fix_app_none_doctypes(source_app)
        
    elif action == 'fix-all-references':
        if not source_app:
            print("❌ Please specify app name")
            return
        fix_all_references(source_app)
        
    elif action == 'verify-integrity':
        verify_data_integrity()
        
    # ===== MIGRATION COMMANDS =====
    elif action == 'migrate':
        if not source_app or not target_app:
            print("❌ Please specify source and target apps")
            print("   Usage: bench --site <site> migrate-app migrate <source> <target>")
            return
        migrate_app_modules(source_app, target_app, modules)
        
    elif action == 'clone-app-local':
        if not source_app:
            print("❌ Please specify app name")
            return
        clone_app_local(source_app, session_id or site)
        
    # ===== CLASSIFICATION & REPORTING =====
    elif action == 'touched-tables':
        result = analyze_touched_tables()
        if result.get('exists'):
            print(f"\n📊 TOUCHED TABLES: {result.get('count')} tables")
            for table in result.get('tables', [])[:20]:
                print(f"   - {table}")
        else:
            print(f"\n⚠️  {result.get('message', 'No touched tables data')}")
            
    elif action == 'risk-assessment':
        if not source_app:
            print("❌ Please specify doctype name")
            return
        risk = generate_migration_risk_assessment(source_app)
        print(f"\n⚠️  RISK ASSESSMENT: {source_app}")
        print(f"   Status: {risk.get('status')}")
        print(f"   Risk Level: {risk.get('risk_level')}")
        print(f"   Description: {risk.get('description')}")
        print(f"\n📋 Recommendations:")
        for rec in risk.get('recommendations', []):
            print(f"   - {rec}")
    
    # ===== HELP =====
    else:
        print(f"❌ Unknown command: {action}")
        display_help()

def display_help():
    """Display comprehensive help for all enhanced commands"""
    print("\n" + "=" * 80)
    print("📚 APP MIGRATOR v{version} - ULTIMATE EDITION WITH ENHANCED DIAGNOSTICS".format(version=__version__))
    print("=" * 80)
    
    print("\n🤖 AI INTEGRATION COMMANDS:")
    print("   ai-migrate \"query\"        - AI-powered natural language commands")
    
    print("\n🧠 INTELLIGENCE COMMANDS:")
    print("   intelligence-dashboard      - Display intelligence system status")
    print("   predict-success <app>       - Predict migration success probability")
    print("   intelligent-validate <source> <target> - Enhanced validation with predictions")
    print("   generate-intelligent-plan <source> <target> - Create intelligent migration plan")
    print("   prevent-issues <app>        - Proactive issue prevention")
    
    print("\n🩺 DIAGNOSTIC COMMANDS:")
    print("   diagnose-app <path>       - Analyze app health without installation")
    print("   scan-bench-health         - Scan health of all apps in bench")
    print("   quick-health-check <app>  - Quick health check for single app")
    print("   repair-bench-apps         - Batch repair all apps in bench")
    print("   health-report <app>       - Generate health report for app")
    
    print("\n🎨 INTERACTIVE COMMANDS:")
    print("   interactive              - Enhanced guided migration wizard")
    
    print("\n🏗️  MULTI-BENCH COMMANDS:")
    print("   multi-bench-analysis     - Analyze entire bench ecosystem")
    print("   list-benches             - List all available benches")
    print("   bench-apps <bench>       - List apps in specific bench")
    print("   bench-health             - Check bench health status")
    
    print("\n🗄️  DATABASE COMMANDS:")
    print("   fix-database-schema      - Fix database schema issues")
    print("   complete-erpnext-install - Complete ERPNext installation")
    print("   fix-tree-doctypes        - Fix tree structure doctypes")
    print("   db-diagnostics           - Run comprehensive diagnostics")
    
    print("\n🔍 ENHANCED ANALYSIS COMMANDS:")
    print("   analyze <app>            - Comprehensive app analysis")
    print("   security-analysis <app>  - Security vulnerability analysis")
    print("   performance <app>        - Performance metrics analysis")
    print("   data-volume <app>        - Data volume and growth analysis")
    print("   compare-versions <app1> <app2> - Compare app versions")
    print("   generate-report <app>    - Generate migration report")
    print("   analyze-orphans          - Detect orphan doctypes")
    print("   validate-migration <app> - Pre-migration validation")
    print("   classify-doctypes <app>  - Classify doctypes by status")
    
    print("\n🧹 DATA QUALITY COMMANDS:")
    print("   fix-orphans <app>        - Fix orphaned doctypes")
    print("   restore-missing <app>    - Restore missing doctypes")
    print("   fix-app-none <app>       - Fix doctypes with app=None")
    print("   fix-all-references <app> - Fix all app references")
    print("   verify-integrity         - Verify data integrity")
    
    print("\n🚀 MIGRATION COMMANDS:")
    print("   migrate <source> <target> - Migrate app modules")
    print("   clone-app-local <app>    - Clone app to local bench")
    
    print("\n📊 REPORTING COMMANDS:")
    print("   touched-tables           - Show migration history")
    print("   risk-assessment <doctype> - Generate risk assessment")
    
    print("\n⚙️  OPTIONS:")
    print("   --detailed               - Show detailed analysis")
    print("   --output-format          - Output format: text, json, csv")
    print("   --bench-path             - Specific bench path for analysis")
    print("   --fix                    - Attempt to fix issues automatically")
    print("   --dry-run                - Show what would be fixed without applying changes")
    
    print("\n💡 EXAMPLES:")
    print("   bench --site mysite migrate-app ai-migrate \"analyze payments app health\"")
    print("   bench --site mysite migrate-app ai-migrate \"scan bench health\"")
    print("   bench --site mysite migrate-app ai-migrate \"fix broken apps\"")
    print("   bench --site mysite migrate-app diagnose-app /path/to/app --fix")
    print("   bench --site mysite migrate-app scan-bench-health")
    print("   bench --site mysite migrate-app quick-health-check myapp")
    print("   bench --site mysite migrate-app repair-bench-apps --dry-run")
    print("   bench --site mysite migrate-app intelligence-dashboard")
    print("   bench --site mysite migrate-app predict-success erpnext")
    print("   bench --site mysite migrate-app intelligent-validate frappe erpnext")
    print("   bench --site mysite migrate-app interactive")
    print("   bench --site mysite migrate-app analyze erpnext --detailed")
    print("   bench --site mysite migrate-app security-analysis custom_app --output-format json")
    print("   bench --site mysite migrate-app performance erpnext")
    print("   bench --site mysite migrate-app migrate custom_app new_app")
    print("   bench --site mysite migrate-app generate-report erpnext --output-format csv")
    print("\n" + "=" * 80)

# ============================================================================
# AI INTEGRATION COMMAND
# ============================================================================

@click.command('ai-migrate')
@click.argument('user_query')
def ai_migrate_command(user_query: str):
    """AI-powered migration using natural language"""
    try:
        from .ai_integration import AppMigratorAIAgent
        agent = AppMigratorAIAgent()
        result = agent.parse_and_execute(user_query)
        
        if result.get('success'):
            click.echo(f"✅ AI Command Result:\n{result['output']}")
        else:
            click.echo(f"❌ AI Command Failed:\n{result.get('error', 'Unknown error')}")
            
    except ImportError:
        click.echo("❌ AI integration not available. Make sure ai_integration.py exists.")
    except Exception as e:
        click.echo(f"❌ AI command error: {str(e)}")

# Register both commands for bench CLI
commands = [migrate_app_command, ai_migrate_command]
