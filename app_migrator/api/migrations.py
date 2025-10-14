import frappe
from frappe import _
from frappe.model.document import Document
import json
import os


@frappe.whitelist()
def create_migration(source_app, target_app, migration_type="full"):
    """
    Create a new migration session between two apps
    
    Args:
        source_app (str): Source application name
        target_app (str): Target application name  
        migration_type (str): Type of migration (full, schema, data, custom)
    
    Returns:
        dict: Migration session details
    """
    try:
        # Validate apps exist
        if not frappe.get_app_source_path(source_app):
            frappe.throw(_("Source app {} does not exist").format(source_app))
            
        if not frappe.get_app_source_path(target_app):
            frappe.throw(_("Target app {} does not exist").format(target_app))
        
        # Create migration session
        migration_id = f"mig_{source_app}_{target_app}_{frappe.generate_hash(length=8)}"
        
        session_data = {
            "migration_id": migration_id,
            "source_app": source_app,
            "target_app": target_app,
            "migration_type": migration_type,
            "status": "created",
            "created_at": frappe.utils.now(),
            "steps": [],
            "message": _("Migration session created successfully")
        }
        
        # Log the migration creation
        frappe.logger().info(f"Migration session created: {migration_id}")
        
        return session_data
        
    except Exception as e:
        frappe.log_error(f"Error creating migration: {str(e)}")
        frappe.throw(_("Failed to create migration session: {}").format(str(e)))


@frappe.whitelist()
def analyze_app_structure(app_name):
    """
    Analyze app structure and return components
    
    Args:
        app_name (str): Application name to analyze
    
    Returns:
        dict: App structure analysis
    """
    try:
        app_path = frappe.get_app_source_path(app_name)
        
        if not os.path.exists(app_path):
            frappe.throw(_("App {} not found").format(app_name))
        
        analysis = {
            "app_name": app_name,
            "app_path": app_path,
            "modules": [],
            "doctypes": [],
            "pages": [],
            "reports": [],
            "dashboard_charts": [],
            "web_forms": [],
            "scripts": [],
            "public_files": []
        }
        
        # Analyze modules
        modules_path = os.path.join(app_path, app_name)
        if os.path.exists(modules_path):
            analysis["modules"] = [d for d in os.listdir(modules_path) 
                                 if os.path.isdir(os.path.join(modules_path, d)) 
                                 and not d.startswith('__')]
        
        # Analyze doctypes
        doctypes_path = os.path.join(app_path, app_name, app_name, "doctype")
        if os.path.exists(doctypes_path):
            analysis["doctypes"] = [d for d in os.listdir(doctypes_path) 
                                  if os.path.isdir(os.path.join(doctypes_path, d))]
        
        frappe.logger().info(f"App structure analyzed: {app_name}")
        return analysis
        
    except Exception as e:
        frappe.log_error(f"Error analyzing app {app_name}: {str(e)}")
        frappe.throw(_("Failed to analyze app structure: {}").format(str(e)))


@frappe.whitelist()
def get_migration_status(migration_id):
    """
    Get status of a migration session
    
    Args:
        migration_id (str): Migration session ID
    
    Returns:
        dict: Migration status and details
    """
    return {
        "migration_id": migration_id,
        "status": "active",
        "progress": 0,
        "current_step": "initializing",
        "details": "Migration in progress"
    }


@frappe.whitelist()
def list_available_apps():
    """
    List all available apps in the bench
    
    Returns:
        list: Available applications
    """
    try:
        apps_path = frappe.get_app_path("frappe")
        bench_path = os.path.dirname(os.path.dirname(apps_path))
        apps_path = os.path.join(bench_path, "apps")
        
        if os.path.exists(apps_path):
            apps = [d for d in os.listdir(apps_path) 
                   if os.path.isdir(os.path.join(apps_path, d)) 
                   and not d.startswith('.')]
            return sorted(apps)
        else:
            return []
            
    except Exception as e:
        frappe.log_error(f"Error listing apps: {str(e)}")
        return []


@frappe.whitelist()
def validate_migration_readiness(source_app, target_app):
    """
    Validate if migration can proceed between apps
    
    Args:
        source_app (str): Source application
        target_app (str): Target application
    
    Returns:
        dict: Validation results
    """
    try:
        validation_results = {
            "can_proceed": True,
            "warnings": [],
            "errors": [],
            "recommendations": []
        }
        
        # Check if apps exist
        source_path = frappe.get_app_source_path(source_app)
        target_path = frappe.get_app_source_path(target_app)
        
        if not source_path:
            validation_results["can_proceed"] = False
            validation_results["errors"].append(f"Source app '{source_app}' not found")
            
        if not target_path:
            validation_results["can_proceed"] = False
            validation_results["errors"].append(f"Target app '{target_app}' not found")
        
        # Check if target app is empty (recommended)
        target_modules_path = os.path.join(target_path, target_app)
        if os.path.exists(target_modules_path) and len(os.listdir(target_modules_path)) > 2:
            validation_results["warnings"].append(
                f"Target app '{target_app}' may not be empty. Consider using a fresh app."
            )
        
        # Check for common conflicts
        if source_app == target_app:
            validation_results["can_proceed"] = False
            validation_results["errors"].append("Source and target apps cannot be the same")
        
        frappe.logger().info(f"Migration validation: {source_app} -> {target_app}")
        return validation_results
        
    except Exception as e:
        frappe.log_error(f"Error validating migration: {str(e)}")
        return {
            "can_proceed": False,
            "errors": [f"Validation error: {str(e)}"]
        }
