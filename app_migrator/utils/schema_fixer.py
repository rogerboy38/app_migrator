"""
Schema Fixer - Database Schema Repair Tool
Fixed with proper database connection handling
"""

import frappe
import os


class SchemaFixer:
    def __init__(self, app_name):
        self.app_name = app_name
    
    def fix_module_def_schema(self):
        """Fix Module Def table schema issues"""
        print(f"🔧 Fixing schema for {self.app_name}...")
        
        try:
            # Ensure we have a database connection
            if not frappe.db:
                print("❌ No database connection available")
                return False
            
            # Check current schema
            columns = frappe.db.sql("DESC `tabModule Def`", as_dict=True)
            column_names = [col['Field'] for col in columns]
            
            fixes_applied = []
            
            # Add missing parent columns if they don't exist
            if 'parent' not in column_names:
                frappe.db.sql("ALTER TABLE `tabModule Def` ADD COLUMN `parent` varchar(255)")
                fixes_applied.append("Added 'parent' column")
                print("✅ Added 'parent' column")
                
            if 'parentfield' not in column_names:
                frappe.db.sql("ALTER TABLE `tabModule Def` ADD COLUMN `parentfield` varchar(255)")
                fixes_applied.append("Added 'parentfield' column")
                print("✅ Added 'parentfield' column")
                
            if 'parenttype' not in column_names:
                frappe.db.sql("ALTER TABLE `tabModule Def` ADD COLUMN `parenttype` varchar(255)")
                fixes_applied.append("Added 'parenttype' column")
                print("✅ Added 'parenttype' column")
            
            if fixes_applied:
                print(f"✅ Schema fixes applied: {', '.join(fixes_applied)}")
                frappe.db.commit()
                return True
            else:
                print("✅ No schema fixes needed")
                return True
                
        except Exception as e:
            print(f"❌ Schema fix failed: {e}")
            return False
    
    def repair_app_installation(self):
        """Comprehensive app installation repair"""
        print(f"🛠️ Repairing {self.app_name} installation...")
        
        try:
            # Step 1: Fix schema
            if not self.fix_module_def_schema():
                return False
            
            # Step 2: Check if app is already installed
            installed_apps = frappe.get_installed_apps()
            if self.app_name in installed_apps:
                print(f"✅ {self.app_name} is already installed")
                
                # Try to verify the installation
                try:
                    modules = frappe.get_all("Module Def", filters={"app_name": self.app_name})
                    print(f"✅ Found {len(modules)} modules for {self.app_name}")
                    
                    # Try to import the app
                    try:
                        __import__(self.app_name)
                        print(f"✅ {self.app_name} module imports successfully")
                        return True
                    except ImportError as e:
                        print(f"⚠️ {self.app_name} import failed: {e}")
                        return False
                        
                except Exception as e:
                    print(f"⚠️ Module check failed: {e}")
                    return False
            else:
                print(f"📦 {self.app_name} not installed, attempting installation...")
                from frappe.installer import install_app
                install_app(self.app_name, force=True)
                print(f"✅ {self.app_name} installed successfully!")
                return True
            
        except Exception as e:
            print(f"❌ Installation repair failed: {e}")
            return False


def fix_app_schema(app_name):
    """Convenience function to fix app schema"""
    fixer = SchemaFixer(app_name)
    return fixer.fix_module_def_schema()


def repair_app_installation(app_name):
    """Convenience function to repair app installation"""
    fixer = SchemaFixer(app_name)
    return fixer.repair_app_installation()
