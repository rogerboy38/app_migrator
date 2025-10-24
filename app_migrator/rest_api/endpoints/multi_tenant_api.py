import frappe
from frappe import _
from frappe.utils.response import build_response

@frappe.whitelist(allow_guest=False)
def create_tenant(tenant_data):
    """Create a new migration tenant"""
    try:
        if isinstance(tenant_data, str):
            import json
            tenant_data = json.loads(tenant_data)
        
        from app_migrator.enterprise_features.multi_tenant.multi_tenant_orchestrator import MultiTenantOrchestrator
        
        orchestrator = MultiTenantOrchestrator()
        result = orchestrator.create_tenant(tenant_data)
        
        if result["success"]:
            return build_response("success", data=result["tenant"])
        else:
            return build_response("error", message=result["error"])
            
    except Exception as e:
        return build_response("error", message=str(e))

@frappe.whitelist(allow_guest=False)
def migrate_tenant_data(project_data):
    """Migrate data between tenants"""
    try:
        if isinstance(project_data, str):
            import json
            project_data = json.loads(project_data)
        
        from app_migrator.enterprise_features.multi_tenant.multi_tenant_orchestrator import MultiTenantOrchestrator
        
        orchestrator = MultiTenantOrchestrator()
        result = orchestrator.migrate_tenant(
            project_data.get("source_tenant"),
            project_data.get("target_tenant"),
            project_data.get("migration_project")
        )
        
        return build_response("success", data=result)
        
    except Exception as e:
        return build_response("error", message=str(e))

@frappe.whitelist(allow_guest=False)
def get_tenant_list():
    """Get list of all tenants"""
    try:
        tenants = frappe.get_all("Migration Tenant", 
                               fields=["name", "tenant_name", "tenant_domain", "is_active"])
        return build_response("success", data=tenants)
    except Exception as e:
        return build_response("error", message=str(e))
