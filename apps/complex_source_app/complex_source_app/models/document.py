import frappe

class ComplexSourceDocument(frappe.Document):
    def complex_source_method(self):
        return "Method from complex_source_app"
