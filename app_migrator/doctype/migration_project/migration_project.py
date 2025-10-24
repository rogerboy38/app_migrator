import frappe
from frappe.model.document import Document

class MigrationProject(Document):
    def before_save(self):
        # Auto-generate project code if not set
        if not self.project_code:
            self.project_code = f"MIG-{frappe.generate_hash()[:8].upper()}"
    
    def validate(self):
        # Validate that source and target are different
        if self.source_app == self.target_app:
            frappe.throw("Source and target applications cannot be the same")
