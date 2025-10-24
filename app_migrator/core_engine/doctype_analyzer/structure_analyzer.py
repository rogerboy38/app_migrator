import frappe

class DoctypeStructureAnalyzer:
    """Analyze doctype structure like we did for SPC Corrective Action"""
    
    def analyze_doctype(self, doctype_name):
        """
        Comprehensive doctype analysis
        """
        try:
            if not frappe.db.exists("DocType", doctype_name):
                return {
                    'doctype': doctype_name,
                    'error': 'doctype_not_found',
                    'potential_issues': ['doctype_not_found']
                }
                
            doc = frappe.get_doc("DocType", doctype_name)
            
            # Safely check for workflow_state_field
            has_workflow = hasattr(doc, 'workflow_state_field') and bool(doc.workflow_state_field)
            
            analysis = {
                'doctype': doctype_name,
                'total_fields': len(doc.fields),
                'field_types': {},
                'custom': doc.custom,
                'module': doc.module,
                'is_submittable': doc.is_submittable,
                'has_workflow': has_workflow,
                'potential_issues': [],
                'field_details': []
            }
            
            # Analyze field types and structure
            for field in doc.fields:
                field_info = {
                    'fieldname': field.fieldname,
                    'fieldtype': field.fieldtype,
                    'label': field.label,
                    'mandatory': field.reqd or False,
                    'options': field.options or ''
                }
                analysis['field_details'].append(field_info)
                
                # Count field types
                analysis['field_types'][field.fieldtype] = \
                    analysis['field_types'].get(field.fieldtype, 0) + 1
            
            # Detect potential issues based on SPC experience
            self._detect_issues(analysis)
            
            return analysis
            
        except Exception as e:
            return {
                'doctype': doctype_name,
                'error': str(e),
                'potential_issues': ['analysis_error']
            }
    
    def _detect_issues(self, analysis):
        """Detect potential issues based on SPC patterns"""
        
        # Minimal custom doctype (like our SPC issue)
        if analysis['total_fields'] == 1 and analysis['custom'] == 1:
            analysis['potential_issues'].append('minimal_custom_doctype')
        
        # No fields
        if analysis['total_fields'] == 0:
            analysis['potential_issues'].append('no_fields')
        
        # Only system fields
        system_fields = ['name', 'owner', 'creation', 'modified', 'modified_by']
        actual_fields = [f['fieldname'] for f in analysis['field_details'] 
                        if f['fieldname'] not in system_fields]
        if len(actual_fields) == 0:
            analysis['potential_issues'].append('only_system_fields')
