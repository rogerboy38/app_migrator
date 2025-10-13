"""
🌐 App Migrator REST API v5.5.3
Comprehensive REST endpoints combining CRUD operations, AI commands, and analysis tools
"""

import frappe
from frappe import _
import json
from typing import Dict, List, Optional, Any


# ============================================================================
# AI & Intelligence Endpoints
# ============================================================================

@frappe.whitelist(allow_guest=False)
def execute_ai_command(user_query: str) -> Dict[str, Any]:
    """
    🤖 Execute AI commands via REST API
    Cloud-friendly natural language interface
    """
    try:
        from .commands.ai_integration import AppMigratorAIAgent
        
        agent = AppMigratorAIAgent()
        result = agent.parse_and_execute(user_query)
        
        return {
            "success": result.get("success", False),
            "command": result.get("command", ""),
            "output": result.get("output", ""),
            "enhanced_analysis": result.get("enhanced_analysis", ""),
            "error": result.get("error", ""),
            "suggestions": result.get("suggestions", [])
        }
        
    except Exception as e:
        frappe.log_error(f"AI Command API Error: {str(e)}")
        return {
            "success": False,
            "error": f"API execution failed: {str(e)}"
        }


@frappe.whitelist(allow_guest=False)
def scan_bench_health_api() -> Dict[str, Any]:
    """
    🔍 Scan bench health via REST API
    Cloud-friendly health analysis
    """
    try:
        from .commands.app_health_scanner import scan_bench_health_function
        
        result = scan_bench_health_function()
        
        return {
            "success": True,
            "result": result,
            "message": "Bench health scan completed successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Bench Health API Error: {str(e)}")
        return {
            "success": False,
            "error": f"Bench health scan failed: {str(e)}"
        }


@frappe.whitelist(allow_guest=False)
def analyze_app_api(app_name: str) -> Dict[str, Any]:
    """
    📊 Analyze app health via REST API
    """
    try:
        from .commands.app_health_scanner import quick_health_check_function
        
        result = quick_health_check_function(app_name)
        
        return {
            "success": True,
            "app_name": app_name,
            "result": result,
            "message": f"App analysis completed for {app_name}"
        }
        
    except Exception as e:
        frappe.log_error(f"App Analysis API Error: {str(e)}")
        return {
            "success": False,
            "error": f"App analysis failed: {str(e)}"
        }


@frappe.whitelist(allow_guest=False)
def predict_success_api(app_name: str) -> Dict[str, Any]:
    """
    🎯 Predict migration success via REST API
    """
    try:
        from .commands.intelligence_engine import predict_migration_success
        
        result = predict_migration_success(app_name, app_name)
        
        return {
            "success": True,
            "app_name": app_name,
            "result": result,
            "message": f"Success prediction completed for {app_name}"
        }
        
    except Exception as e:
        frappe.log_error(f"Success Prediction API Error: {str(e)}")
        return {
            "success": False,
            "error": f"Success prediction failed: {str(e)}"
        }


@frappe.whitelist(allow_guest=False)
def get_bench_apps_api(bench_name: str = "frappe-bench-v5") -> Dict[str, Any]:
    """
    📦 Get bench apps list via REST API
    """
    try:
        from .commands.analysis_tools import get_bench_apps
        
        apps = get_bench_apps(bench_name)
        
        return {
            "success": True,
            "bench_name": bench_name,
            "apps": apps,
            "total_apps": len(apps),
            "message": f"Found {len(apps)} apps in {bench_name}"
        }
        
    except Exception as e:
        frappe.log_error(f"Bench Apps API Error: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to get bench apps: {str(e)}"
        }


@frappe.whitelist(allow_guest=False)
def list_benches_api() -> Dict[str, Any]:
    """
    🏗️ List available benches via REST API
    """
    try:
        from .commands.analysis_tools import detect_available_benches
        
        benches = detect_available_benches()
        
        return {
            "success": True,
            "benches": benches,
            "total_benches": len(benches),
            "message": f"Found {len(benches)} benches"
        }
        
    except Exception as e:
        frappe.log_error(f"List Benches API Error: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to list benches: {str(e)}"
        }


@frappe.whitelist(allow_guest=False)
def intelligence_dashboard_api() -> Dict[str, Any]:
    """
    🧠 Get intelligence dashboard via REST API
    """
    try:
        from .commands.intelligence_engine import display_intelligence_dashboard
        
        # Capture the dashboard output
        import io
        from contextlib import redirect_stdout
        
        f = io.StringIO()
        with redirect_stdout(f):
            display_intelligence_dashboard()
        dashboard_output = f.getvalue()
        
        return {
            "success": True,
            "dashboard": dashboard_output,
            "message": "Intelligence dashboard generated successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Intelligence Dashboard API Error: {str(e)}")
        return {
            "success": False,
            "error": f"Intelligence dashboard failed: {str(e)}"
        }


@frappe.whitelist(allow_guest=False)
def repair_apps_api(dry_run: bool = True) -> Dict[str, Any]:
    """
    🔧 Batch repair apps via REST API
    """
    try:
        from .commands.diagnostic_commands import repair_bench_apps_callback
        
        result = repair_bench_apps_callback(dry_run=dry_run)
        
        return {
            "success": True,
            "dry_run": dry_run,
            "result": result,
            "message": f"Batch repair completed (dry_run: {dry_run})"
        }
        
    except Exception as e:
        frappe.log_error(f"Repair Apps API Error: {str(e)}")
        return {
            "success": False,
            "error": f"Batch repair failed: {str(e)}"
        }


# ============================================================================
# CRUD Operations for Migration Sessions
# ============================================================================

@frappe.whitelist()
def create_migration_session(name: str, source_app: str, target_app: str, metadata: Optional[Dict] = None) -> Dict:
    """
    Create a new migration session
    
    Args:
        name: Session name/identifier
        source_app: Source application path or name
        target_app: Target application path or name
        metadata: Optional metadata dictionary
    
    Returns:
        dict: Created session details
    
    Example:
        POST /api/method/app_migrator.api.create_migration_session
        {
            "name": "migration_frappe_to_custom",
            "source_app": "frappe",
            "target_app": "custom_app",
            "metadata": {"user": "admin", "notes": "Test migration"}
        }
    """
    try:
        from app_migrator.commands.session_manager import SessionManager
        
        session = SessionManager(name)
        session.metadata.update({
            "source_app": source_app,
            "target_app": target_app,
            "created_via": "REST_API",
            "status": "created"
        })
        
        if metadata:
            session.metadata.update(metadata)
        
        session.save()
        
        return {
            "success": True,
            "session_id": name,
            "data": session.metadata,
            "message": f"Session '{name}' created successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error creating migration session: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to create migration session"
        }


@frappe.whitelist()
def get_migration_session(session_id: str) -> Dict:
    """
    Retrieve migration session details
    
    Args:
        session_id: Session identifier
    
    Returns:
        dict: Session details
    
    Example:
        GET /api/method/app_migrator.api.get_migration_session?session_id=migration_frappe_to_custom
    """
    try:
        from app_migrator.commands.session_manager import SessionManager
        
        session = SessionManager(session_id)
        
        return {
            "success": True,
            "session_id": session_id,
            "data": {
                "name": session.name,
                "metadata": session.metadata,
                "operations": session.operations,
                "errors": session.errors
            },
            "message": "Session retrieved successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error retrieving session: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to retrieve session"
        }


@frappe.whitelist()
def update_migration_session(session_id: str, metadata: Dict) -> Dict:
    """
    Update migration session metadata
    
    Args:
        session_id: Session identifier
        metadata: Metadata dictionary to update
    
    Returns:
        dict: Updated session details
    
    Example:
        POST /api/method/app_migrator.api.update_migration_session
        {
            "session_id": "migration_frappe_to_custom",
            "metadata": {"status": "in_progress", "progress": 50}
        }
    """
    try:
        from app_migrator.commands.session_manager import SessionManager
        
        session = SessionManager(session_id)
        session.metadata.update(metadata)
        session.save()
        
        return {
            "success": True,
            "session_id": session_id,
            "data": session.metadata,
            "message": "Session updated successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error updating session: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to update session"
        }


@frappe.whitelist()
def delete_migration_session(session_id: str) -> Dict:
    """
    Delete a migration session
    
    Args:
        session_id: Session identifier
    
    Returns:
        dict: Deletion confirmation
    
    Example:
        POST /api/method/app_migrator.api.delete_migration_session
        {
            "session_id": "migration_frappe_to_custom"
        }
    """
    try:
        from app_migrator.commands.session_manager import SessionManager
        
        session = SessionManager(session_id)
        session.delete()
        
        return {
            "success": True,
            "session_id": session_id,
            "message": f"Session '{session_id}' deleted successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error deleting session: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to delete session"
        }


@frappe.whitelist()
def list_migration_sessions() -> Dict:
    """
    List all migration sessions
    
    Returns:
        dict: List of sessions
    
    Example:
        GET /api/method/app_migrator.api.list_migration_sessions
    """
    try:
        # This would need to be implemented based on how sessions are stored
        # For now, return a placeholder response
        return {
            "success": True,
            "data": {
                "sessions": [],
                "count": 0
            },
            "message": "Sessions list retrieved (feature in development)"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to list sessions"
        }


# ============================================================================
# Analysis & Diagnostic Endpoints
# ============================================================================

@frappe.whitelist()
def analyze_app(app_path: str, detailed: bool = False) -> Dict:
    """
    Analyze a Frappe application structure
    
    Args:
        app_path: Path to the application
        detailed: Whether to return detailed analysis
    
    Returns:
        dict: Analysis results
    
    Example:
        POST /api/method/app_migrator.api.analyze_app
        {
            "app_path": "/path/to/frappe",
            "detailed": true
        }
    """
    try:
        from app_migrator.commands.analysis_tools import analyze_app_structure
        
        result = analyze_app_structure(app_path, detailed=detailed)
        
        return {
            "success": True,
            "data": result,
            "message": "App analysis completed successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error analyzing app: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "App analysis failed"
        }


@frappe.whitelist()
def quick_health_check(app_path: str) -> Dict:
    """
    Perform quick health check on an app
    
    Args:
        app_path: Path to the application
    
    Returns:
        dict: Health check results
    
    Example:
        GET /api/method/app_migrator.api.quick_health_check?app_path=/path/to/app
    """
    try:
        from app_migrator.commands.app_health_scanner import AppHealthScanner
        
        scanner = AppHealthScanner()
        result = scanner.quick_health_check(app_path)
        
        return {
            "success": True,
            "data": result,
            "message": "Health check completed"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Health check failed"
        }


@frappe.whitelist()
def diagnose_app(app_path: str, auto_fix: bool = False) -> Dict:
    """
    Diagnose application issues
    
    Args:
        app_path: Path to the application
        auto_fix: Whether to automatically fix issues
    
    Returns:
        dict: Diagnosis results
    
    Example:
        POST /api/method/app_migrator.api.diagnose_app
        {
            "app_path": "/path/to/app",
            "auto_fix": true
        }
    """
    try:
        from app_migrator.commands.diagnostic_tools import DiagnosticTools
        
        diagnostic = DiagnosticTools()
        result = diagnostic.diagnose(app_path, auto_fix=auto_fix)
        
        return {
            "success": True,
            "data": result,
            "message": "Diagnosis completed" + (" with auto-fix applied" if auto_fix else "")
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Diagnosis failed"
        }


# ============================================================================
# Migration Operations
# ============================================================================

@frappe.whitelist()
def migrate_modules(source_app: str, target_app: str, modules: List[str], session_id: Optional[str] = None) -> Dict:
    """
    Migrate specific modules from source to target app
    
    Args:
        source_app: Source application path
        target_app: Target application path
        modules: List of module names to migrate
        session_id: Optional session ID for tracking
    
    Returns:
        dict: Migration results
    
    Example:
        POST /api/method/app_migrator.api.migrate_modules
        {
            "source_app": "frappe",
            "target_app": "custom_app",
            "modules": ["Core", "Custom"],
            "session_id": "migration_001"
        }
    """
    try:
        from app_migrator.commands.migration_tools import MigrationTools
        
        migrator = MigrationTools(session_id=session_id)
        result = migrator.migrate_modules(source_app, target_app, modules)
        
        return {
            "success": True,
            "data": result,
            "session_id": session_id,
            "message": f"Migrated {len(modules)} modules successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Migration error: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Migration failed"
        }


@frappe.whitelist()
def get_migration_status(session_id: str) -> Dict:
    """
    Get status of an ongoing migration
    
    Args:
        session_id: Session identifier
    
    Returns:
        dict: Migration status and progress
    
    Example:
        GET /api/method/app_migrator.api.get_migration_status?session_id=migration_001
    """
    try:
        from app_migrator.commands.session_manager import SessionManager
        
        session = SessionManager(session_id)
        
        # Calculate progress
        total_ops = len(session.operations)
        completed_ops = sum(1 for op in session.operations if op.get("status") == "completed")
        progress = (completed_ops / total_ops * 100) if total_ops > 0 else 0
        
        return {
            "success": True,
            "session_id": session_id,
            "data": {
                "status": session.metadata.get("status", "unknown"),
                "progress": round(progress, 2),
                "total_operations": total_ops,
                "completed_operations": completed_ops,
                "errors": len(session.errors),
                "metadata": session.metadata
            },
            "message": "Status retrieved successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting migration status: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to get migration status"
        }


# ============================================================================
# API Status & Documentation
# ============================================================================

@frappe.whitelist(allow_guest=False)
def get_api_status() -> Dict[str, Any]:
    """
    📡 Get API status and available endpoints
    """
    endpoints = [
        {
            "endpoint": "execute_ai_command",
            "method": "POST",
            "description": "Execute natural language AI commands",
            "parameters": {"user_query": "string"}
        },
        {
            "endpoint": "scan_bench_health_api", 
            "method": "GET",
            "description": "Scan health of all apps in bench",
            "parameters": {}
        },
        {
            "endpoint": "analyze_app_api",
            "method": "GET", 
            "description": "Analyze specific app health",
            "parameters": {"app_name": "string"}
        },
        {
            "endpoint": "predict_success_api",
            "method": "GET",
            "description": "Predict migration success probability",
            "parameters": {"app_name": "string"}
        },
        {
            "endpoint": "get_bench_apps_api",
            "method": "GET",
            "description": "Get list of apps in bench", 
            "parameters": {"bench_name": "string (optional)"}
        },
        {
            "endpoint": "list_benches_api",
            "method": "GET",
            "description": "List available benches",
            "parameters": {}
        },
        {
            "endpoint": "intelligence_dashboard_api",
            "method": "GET", 
            "description": "Get AI intelligence dashboard",
            "parameters": {}
        },
        {
            "endpoint": "repair_apps_api",
            "method": "POST",
            "description": "Batch repair apps",
            "parameters": {"dry_run": "boolean (optional)"}
        },
        {
            "endpoint": "create_migration_session",
            "method": "POST",
            "description": "Create new migration session",
            "parameters": {"name": "string", "source_app": "string", "target_app": "string", "metadata": "dict (optional)"}
        },
        {
            "endpoint": "get_migration_session",
            "method": "GET",
            "description": "Get migration session details",
            "parameters": {"session_id": "string"}
        },
        {
            "endpoint": "update_migration_session",
            "method": "POST",
            "description": "Update migration session",
            "parameters": {"session_id": "string", "metadata": "dict"}
        },
        {
            "endpoint": "delete_migration_session",
            "method": "POST",
            "description": "Delete migration session",
            "parameters": {"session_id": "string"}
        },
        {
            "endpoint": "list_migration_sessions",
            "method": "GET",
            "description": "List all migration sessions",
            "parameters": {}
        },
        {
            "endpoint": "analyze_app",
            "method": "POST",
            "description": "Analyze app structure",
            "parameters": {"app_path": "string", "detailed": "boolean"}
        },
        {
            "endpoint": "quick_health_check",
            "method": "GET",
            "description": "Quick app health check",
            "parameters": {"app_path": "string"}
        },
        {
            "endpoint": "diagnose_app",
            "method": "POST",
            "description": "Diagnose app issues",
            "parameters": {"app_path": "string", "auto_fix": "boolean"}
        },
        {
            "endpoint": "migrate_modules",
            "method": "POST",
            "description": "Migrate modules between apps",
            "parameters": {"source_app": "string", "target_app": "string", "modules": "list", "session_id": "string (optional)"}
        },
        {
            "endpoint": "get_migration_status",
            "method": "GET",
            "description": "Get migration progress",
            "parameters": {"session_id": "string"}
        }
    ]
    
    return {
        "success": True,
        "version": "5.5.3",
        "status": "active",
        "total_endpoints": len(endpoints),
        "endpoints": endpoints,
        "message": "App Migrator REST API v5.5.3 is operational"
    }
