import frappe
from frappe import _
from frappe.utils.response import build_response

@frappe.whitelist(allow_guest=False)
def create_migration_project(project_data):
    """
    REST API for creating migration projects
    """
    try:
        if isinstance(project_data, str):
            import json
            project_data = json.loads(project_data)
            
        project = frappe.get_doc({
            "doctype": "Migration Project",
            "project_name": project_data.get("project_name"),
            "source_app": project_data.get("source_app"),
            "target_app": project_data.get("target_app"),
            "migration_type": project_data.get("migration_type", "standard"),
            "description": project_data.get("description", ""),
            "conflict_resolution_strategy": project_data.get("conflict_resolution_strategy", "AI-Assisted")
        })
        project.insert()
        
        return build_response("success", data=project.as_dict())
        
    except Exception as e:
        frappe.log_error(f"Migration project creation failed: {str(e)}")
        return build_response("error", message=str(e))

@frappe.whitelist(allow_guest=False)
def start_migration(project_name):
    """Start migration for a project"""
    try:
        if frappe.db.exists("Migration Project", project_name):
            project = frappe.get_doc("Migration Project", project_name)
            
            if project.status == "In Progress":
                return build_response("error", message="Migration already in progress")
                
            project.status = "In Progress"
            project.save()
            
            # Start migration process
            from app_migrator.core_engine.migration_orchestrator.migration_orchestrator import MigrationOrchestrator
            orchestrator = MigrationOrchestrator()
            result = orchestrator.execute_migration(project)
            
            project.status = "Completed" if result.get("overall_success") else "Failed"
            project.save()
            
            return build_response("success", data={
                "project": project.as_dict(),
                "migration_result": result
            })
        else:
            return build_response("error", message="Project not found")
    except Exception as e:
        # Update project status to failed
        if frappe.db.exists("Migration Project", project_name):
            project = frappe.get_doc("Migration Project", project_name)
            project.status = "Failed"
            project.save()
            
        frappe.log_error(f"Migration start failed: {str(e)}")
        return build_response("error", message=str(e))

@frappe.whitelist(allow_guest=False)
def get_migration_status(project_name):
    """Get migration project status"""
    try:
        if frappe.db.exists("Migration Project", project_name):
            project = frappe.get_doc("Migration Project", project_name)
            
            status_info = {
                "project": project.as_dict(),
                "progress": {
                    "status": project.status,
                    "completion_percentage": 0,  # Would be calculated from actual progress
                    "current_step": "Initializing",
                    "details": {}
                }
            }
            
            return build_response("success", data=status_info)
        else:
            return build_response("error", message="Project not found")
    except Exception as e:
        return build_response("error", message=str(e))

@frappe.whitelist(allow_guest=False)
def rollback_migration(project_name):
    """Rollback a migration"""
    try:
        if frappe.db.exists("Migration Project", project_name):
            project = frappe.get_doc("Migration Project", project_name)
            
            from app_migrator.core_engine.migration_orchestrator.migration_orchestrator import MigrationOrchestrator
            orchestrator = MigrationOrchestrator()
            rollback_result = orchestrator.rollback_migration(project)
            
            project.status = "Rolled Back"
            project.save()
            
            return build_response("success", data={
                "project": project.as_dict(),
                "rollback_result": rollback_result
            })
        else:
            return build_response("error", message="Project not found")
    except Exception as e:
        frappe.log_error(f"Migration rollback failed: {str(e)}")
        return build_response("error", message=str(e))

@frappe.whitelist(allow_guest=False)
def analyze_app_structure(app_name):
    """Analyze app structure before migration"""
    try:
        from app_migrator.core_engine.doctype_analyzer import DoctypeStructureAnalyzer
        from app_migrator.core_engine.conflict_resolver import DoctypeConflictResolver
        
        analyzer = DoctypeStructureAnalyzer()
        resolver = DoctypeConflictResolver()
        
        # Get all doctypes for the app
        doctypes = frappe.get_all("DocType", 
                                filters={"module": app_name},
                                fields=["name", "module", "custom"])
        
        analysis_results = {
            "app_name": app_name,
            "total_doctypes": len(doctypes),  # FIX: Add this key
            "doctype_analysis": {},
            "conflicts": resolver.detect_doctype_conflicts(app_name),
            "summary": {
                "total_doctypes": len(doctypes),  # FIX: This is the correct key
                "custom_doctypes": 0,
                "standard_doctypes": 0,
                "total_fields": 0
            }
        }
        
        for dt in doctypes:
            analysis = analyzer.analyze_doctype(dt['name'])
            analysis_results["doctype_analysis"][dt['name']] = analysis
            
            if dt['custom'] == 1:
                analysis_results["summary"]["custom_doctypes"] += 1
            else:
                analysis_results["summary"]["standard_doctypes"] += 1
                
            if 'total_fields' in analysis:
                analysis_results["summary"]["total_fields"] += analysis['total_fields']
        
        return build_response("success", data=analysis_results)
        
    except Exception as e:
        frappe.log_error(f"App analysis failed: {str(e)}")
        return build_response("error", message=str(e))


def build_response(status, data=None, message=None):
    """Standard response builder"""
    return {
        "status": status,
        "data": data,
        "message": message
    }
