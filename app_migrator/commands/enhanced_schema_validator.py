"""
Enhanced Schema Validator for App Migrator
Validates database schema integrity after migration
"""

import frappe
import os
from typing import Dict, List, Tuple

class EnhancedSchemaValidator:
    def __init__(self, app_name: str):
        self.app_name = app_name
        self.validation_results = {}
        
    def validate_app_schema(self) -> Dict:
        """Comprehensive schema validation for an app"""
        print(f"🔍 Validating schema for {self.app_name}...")
        
        validations = {
            "doctypes": self.validate_doctypes(),
            "modules": self.validate_modules(),
            "custom_fields": self.validate_custom_fields(),
            "property_setters": self.validate_property_setters(),
            "workspaces": self.validate_workspaces()
        }
        
        self.validation_results = validations
        return validations
    
    def validate_doctypes(self) -> Dict:
        """Validate all doctypes for the app"""
        try:
            doctypes = frappe.get_all("DocType", 
                                    filters={"module": self.app_name},
                                    fields=["name", "issingle", "istable", "custom"])
            
            validation_result = {
                "total": len(doctypes),
                "single": len([d for d in doctypes if d.issingle]),
                "table": len([d for d in doctypes if d.istable]),
                "custom": len([d for d in doctypes if d.custom]),
                "standard": len([d for d in doctypes if not d.custom])
            }
            
            print(f"✅ Found {validation_result['total']} doctypes in {self.app_name}")
            return validation_result
            
        except Exception as e:
            print(f"❌ Error validating doctypes: {e}")
            return {"error": str(e)}
    
    def validate_modules(self) -> Dict:
        """Validate modules for the app"""
        try:
            modules = frappe.get_all("Module Def", 
                                   filters={"app_name": self.app_name},
                                   fields=["name", "app_name"])
            
            validation_result = {
                "total": len(modules),
                "modules": [m.name for m in modules]
            }
            
            print(f"✅ Found {validation_result['total']} modules in {self.app_name}")
            return validation_result
            
        except Exception as e:
            print(f"❌ Error validating modules: {e}")
            return {"error": str(e)}
    
    def validate_custom_fields(self) -> Dict:
        """Validate custom fields for the app"""
        try:
            custom_fields = frappe.get_all("Custom Field", 
                                         filters={"module": self.app_name},
                                         fields=["name", "dt", "fieldname"])
            
            validation_result = {
                "total": len(custom_fields),
                "by_doctype": {}
            }
            
            for cf in custom_fields:
                if cf.dt not in validation_result["by_doctype"]:
                    validation_result["by_doctype"][cf.dt] = 0
                validation_result["by_doctype"][cf.dt] += 1
            
            print(f"✅ Found {validation_result['total']} custom fields in {self.app_name}")
            return validation_result
            
        except Exception as e:
            print(f"❌ Error validating custom fields: {e}")
            return {"error": str(e)}
    
    def validate_property_setters(self) -> Dict:
        """Validate property setters for the app"""
        try:
            property_setters = frappe.get_all("Property Setter", 
                                            filters={"module": self.app_name},
                                            fields=["name", "doc_type", "property"])
            
            validation_result = {
                "total": len(property_setters),
                "by_doctype": {}
            }
            
            for ps in property_setters:
                if ps.doc_type not in validation_result["by_doctype"]:
                    validation_result["by_doctype"][ps.doc_type] = 0
                validation_result["by_doctype"][ps.doc_type] += 1
            
            print(f"✅ Found {validation_result['total']} property setters in {self.app_name}")
            return validation_result
            
        except Exception as e:
            print(f"❌ Error validating property setters: {e}")
            return {"error": str(e)}
    
    def validate_workspaces(self) -> Dict:
        """Validate workspaces for the app"""
        try:
            workspaces = frappe.get_all("Workspace", 
                                      filters={"module": self.app_name},
                                      fields=["name", "title", "is_standard"])
            
            validation_result = {
                "total": len(workspaces),
                "standard": len([w for w in workspaces if w.is_standard]),
                "custom": len([w for w in workspaces if not w.is_standard])
            }
            
            print(f"✅ Found {validation_result['total']} workspaces in {self.app_name}")
            return validation_result
            
        except Exception as e:
            print(f"❌ Error validating workspaces: {e}")
            return {"error": str(e)}
    
    def generate_report(self) -> str:
        """Generate a comprehensive validation report"""
        if not self.validation_results:
            self.validate_app_schema()
        
        report = []
        report.append(f"📊 SCHEMA VALIDATION REPORT: {self.app_name}")
        report.append("=" * 50)
        
        for section, results in self.validation_results.items():
            report.append(f"\n🔧 {section.upper()}:")
            if "error" in results:
                report.append(f"   ❌ Error: {results['error']}")
            else:
                for key, value in results.items():
                    if key not in ["modules", "by_doctype"]:
                        report.append(f"   ✅ {key}: {value}")
        
        return "\n".join(report)

def validate_app_schema(app_name: str):
    """CLI command to validate app schema"""
    validator = EnhancedSchemaValidator(app_name)
    results = validator.validate_app_schema()
    print(validator.generate_report())
    return results
