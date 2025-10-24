import frappe
from frappe.model.document import Document

class DoctypeConflictResolver:
    """SPC-based conflict resolution system"""
    
    def __init__(self):
        self.learned_patterns = []
        self.migration_history = []
        
    def detect_doctype_conflicts(self, app_name):
        """
        FROM SPC FIX: Detect duplicate doctypes like we encountered
        Pattern: spc_corrective_action (custom:1) vs SPC Corrective Action (custom:0)
        """
        conflicts = []
        
        # Get all doctypes for the app
        doctypes = frappe.get_all("DocType", 
                                filters={"module": app_name},
                                fields=["name", "module", "custom", "modified"])
        
        # Check for naming conflicts and custom vs standard issues
        doctype_names = {}
        for dt in doctypes:
            normalized_name = self._normalize_doctype_name(dt['name'])
            if normalized_name not in doctype_names:
                doctype_names[normalized_name] = []
            doctype_names[normalized_name].append(dt)
        
        # Identify conflicts
        for name, doctype_list in doctype_names.items():
            if len(doctype_list) > 1:
                conflict = {
                    'type': 'duplicate_doctype',
                    'normalized_name': name,
                    'doctypes': doctype_list,
                    'resolution_strategy': 'remove_custom_keep_standard'
                }
                conflicts.append(conflict)
                
        return conflicts
    
    def _normalize_doctype_name(self, name):
        """Normalize doctype name for comparison"""
        return name.lower().replace(' ', '_').replace('-', '_')
    
    def resolve_conflicts(self, conflicts):
        """
        Apply SPC-learned resolution patterns
        """
        resolutions = []
        
        for conflict in conflicts:
            if conflict['type'] == 'duplicate_doctype':
                resolution = self._resolve_duplicate_doctype(conflict)
                resolutions.append(resolution)
        
        return resolutions
    
    def _resolve_duplicate_doctype(self, conflict):
        """
        SPC FIX PATTERN: Remove custom doctypes, keep standard ones
        """
        resolution = {
            'conflict_type': conflict['type'],
            'actions_taken': [],
            'doctypes_removed': [],
            'doctypes_kept': []
        }
        
        for doctype_info in conflict['doctypes']:
            if doctype_info['custom'] == 1:
                # Remove custom doctype (like we did with spc_corrective_action)
                try:
                    frappe.delete_doc("DocType", doctype_info['name'], force=1)
                    resolution['actions_taken'].append(f"Removed custom doctype: {doctype_info['name']}")
                    resolution['doctypes_removed'].append(doctype_info['name'])
                except Exception as e:
                    resolution['actions_taken'].append(f"Failed to remove {doctype_info['name']}: {str(e)}")
            else:
                resolution['doctypes_kept'].append(doctype_info['name'])
        
        frappe.db.commit()
        return resolution
