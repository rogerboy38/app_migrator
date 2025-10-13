"""
App Migrator REST API
Provides RESTful endpoints for CRUD operations and analysis tools
Version: 5.5.2
"""

import frappe
from frappe import _
import json
from typing import Dict, List, Optional, Any


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
        return {
            "success": False,
            "error": str(e),
            "message": f"Session '{session_id}' not found"
        }


@frappe.whitelist()
def update_migration_session(session_id: str, metadata: Dict) -> Dict:
    """
    Update migration session metadata
    
    Args:
        session_id: Session identifier
        metadata: Updated metadata dictionary
    
    Returns:
        dict: Updated session details
    
    Example:
        PUT /api/method/app_migrator.api.update_migration_session
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
        DELETE /api/method/app_migrator.api.delete_migration_session?session_id=migration_frappe_to_custom
    """
    try:
        from app_migrator.commands.session_manager import SessionManager
        
        session = SessionManager(session_id)
        # Clear session data
        session.operations = []
        session.errors = []
        session.metadata = {"status": "deleted"}
        session.save()
        
        return {
            "success": True,
            "session_id": session_id,
            "message": f"Session '{session_id}' deleted successfully"
        }
        
    except Exception as e:
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
        dict: List of all sessions
    
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
    Diagnose app issues and optionally apply fixes
    
    Args:
        app_path: Path to the application
        auto_fix: Whether to automatically fix detected issues
    
    Returns:
        dict: Diagnostic results and fixes applied
    
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
