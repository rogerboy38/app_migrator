import click
import frappe
from frappe.utils import get_sites
import os
import shutil
import json
import re
import subprocess
import sys
from pathlib import Path

__version__ = "1.0.0"

app_name = "app_migrator"
app_title = "App Migrator"
app_publisher = "Frappe Community"
app_description = "Frappe App Migration Toolkit"
app_email = "fcrm@amb-wellness.com"
app_license = "mit"

@click.command('migrate-app')
@click.argument('action')
@click.argument('source_app', required=False)
@click.argument('target_app', required=False)
@click.option('--modules', help='Specific modules to migrate')
@click.option('--site', help='Site name')
def migrate_app(action, source_app=None, target_app=None, modules=None, site=None):
    """App Migrator - Frappe App Migration Toolkit with Enhanced Renaming"""
    
    print(f"🚀 Migration command called: {action} for {source_app}")
    
    if action == 'analyze':
        analyze_app(source_app)
        
    elif action == 'fix-database-schema':
        fix_database_schema()
        
    elif action == 'complete-erpnext-install':
        complete_erpnext_installation()
        
    elif action == 'fix-tree-doctypes':
        fix_all_tree_doctypes()
        
    elif action == 'migrate':
        print(f"Migrating app: {source_app}")
        # Add migrate functionality here
        
    elif action == 'interactive':
        interactive_migration()
        
    elif action == 'select-modules':
        selected_modules, selected_doctypes = select_modules_interactive(source_app, target_app)
        click.echo(f"🎯 Final selection: {len(selected_modules)} modules with doctype-level selection")
        
    elif action == 'fix-orphans':
        fix_orphan_doctypes(source_app)
        
    elif action == 'restore-missing':
        restore_missing_doctypes(source_app)
        
    elif action == 'fix-app-none':
        fix_app_none_doctypes(source_app)
        
    elif action == 'analyze-orphans':
        analyze_orphan_doctypes()
        
    elif action == 'fix-all-references':
        fix_all_references(source_app)
        
    elif action == 'rename-systematic':
        systematic_renaming(source_app, target_app)
        
    elif action == 'validate-migration':
        validate_migration_readiness(source_app)
        
    else:
        print(f"❌ Unknown action: {action}")
        print("📋 Available actions: analyze, fix-database-schema, complete-erpnext-install, fix-tree-doctypes, migrate, interactive, select-modules, fix-orphans, restore-missing, fix-app-none, analyze-orphans, fix-all-references, rename-systematic, validate-migration")

def fix_database_schema():
    """Fix missing database columns that prevent app installation"""
    print("🔧 FIXING DATABASE SCHEMA FOR MODULE DEF TABLE")
    
    try:
        sites = get_sites()
        site = sites[0] if sites else None
        if not site:
            print("❌ No site available")
            return
            
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            # Check current table structure
            print("📊 CHECKING TABLE STRUCTURE...")
            
            # Get current columns in tabModule Def
            current_columns = frappe.db.sql("""
                SHOW COLUMNS FROM `tabModule Def`
            """, as_dict=True)
            
            current_column_names = [col['Field'] for col in current_columns]
            print(f"   Current columns: {current_column_names}")
            
            # Required columns for Frappe v15
            required_columns = [
                'parent', 'parentfield', 'parenttype', 'idx',
                'module_name', 'custom', 'app_name', 'restrict_to_domain',
                '_user_tags', '_comments', '_assign', '_liked_by', 'package'
            ]
            
            missing_columns = [col for col in required_columns if col not in current_column_names]
            
            if missing_columns:
                print(f"🚨 MISSING COLUMNS: {missing_columns}")
                print("🔄 ADDING MISSING COLUMNS...")
                
                for column in missing_columns:
                    try:
                        if column in ['parent', 'parentfield', 'parenttype']:
                            frappe.db.sql(f"""
                                ALTER TABLE `tabModule Def` 
                                ADD COLUMN `{column}` varchar(140)
                            """)
                            print(f"   ✅ Added {column} (varchar)")
                            
                        elif column == 'idx':
                            frappe.db.sql(f"""
                                ALTER TABLE `tabModule Def` 
                                ADD COLUMN `{column}` int(8) NOT NULL DEFAULT 0
                            """)
                            print(f"   ✅ Added {column} (int)")
                            
                        elif column in ['custom', 'restrict_to_domain']:
                            frappe.db.sql(f"""
                                ALTER TABLE `tabModule Def` 
                                ADD COLUMN `{column}` int(1) NOT NULL DEFAULT 0
                            """)
                            print(f"   ✅ Added {column} (int)")
                            
                        elif column in ['module_name', 'app_name']:
                            frappe.db.sql(f"""
                                ALTER TABLE `tabModule Def` 
                                ADD COLUMN `{column}` varchar(140)
                            """)
                            print(f"   ✅ Added {column} (varchar)")
                            
                        elif column in ['_user_tags', '_comments', '_assign', '_liked_by']:
                            frappe.db.sql(f"""
                                ALTER TABLE `tabModule Def` 
                                ADD COLUMN `{column}` text
                            """)
                            print(f"   ✅ Added {column} (text)")
                            
                        elif column == 'package':
                            frappe.db.sql(f"""
                                ALTER TABLE `tabModule Def` 
                                ADD COLUMN `{column}` varchar(140)
                            """)
                            print(f"   ✅ Added {column} (varchar)")
                            
                    except Exception as e:
                        print(f"   ⚠️  Could not add {column}: {e}")
                
                print("🎉 DATABASE SCHEMA UPDATED!")
                
            else:
                print("✅ ALL REQUIRED COLUMNS EXIST")
            
            frappe.db.commit()
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def complete_erpnext_installation():
    """Complete ERPNext installation after fixing schema"""
    print("🚀 COMPLETING ERPNext INSTALLATION")
    
    try:
        # First fix the database schema
        fix_database_schema()
        
        # Then install ERPNext
        print("\n📦 INSTALLING ERPNext...")
        
        result = subprocess.run([
            sys.executable, '-m', 'bench', '--site', 'sysmayal.v.frappe.cloud', 
            'install-app', 'erpnext', '--force'
        ], capture_output=True, text=True, cwd='/home/frappe/frappe-bench')
        
        if result.returncode == 0:
            print("✅ ERPNext INSTALLED SUCCESSFULLY!")
            print(result.stdout)
        else:
            print("❌ ERPNext INSTALLATION FAILED:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def fix_all_tree_doctypes():
    """Fix tree doctypes that need parent fields"""
    print("🌳 FIXING TREE DOCTYPE STRUCTURES")
    
    try:
        sites = get_sites()
        site = sites[0] if sites else None
        if not site:
            print("❌ No site available")
            return
            
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            # Get all tree doctypes
            tree_doctypes = frappe.get_all('DocType', 
                filters={'is_tree': 1},
                fields=['name']
            )
            
            print(f"🔍 Found {len(tree_doctypes)} tree doctypes")
            
            for doctype in tree_doctypes:
                doctype_name = doctype['name']
                print(f"   Checking {doctype_name}...")
                
                # Check if parent fields exist in the table
                table_name = f"tab{doctype_name}"
                try:
                    columns = frappe.db.sql(f"SHOW COLUMNS FROM `{table_name}`", as_dict=True)
                    column_names = [col['Field'] for col in columns]
                    
                    required_parent_fields = ['lft', 'rgt']  # Tree structure fields
                    missing_parent_fields = [field for field in required_parent_fields if field not in column_names]
                    
                    if missing_parent_fields:
                        print(f"   ⚠️  Missing tree fields: {missing_parent_fields}")
                        # Add missing tree fields
                        for field in missing_parent_fields:
                            frappe.db.sql(f"""
                                ALTER TABLE `{table_name}` 
                                ADD COLUMN `{field}` int(8) NOT NULL DEFAULT 0
                            """)
                        print(f"   ✅ Added missing tree fields to {doctype_name}")
                        
                except Exception as e:
                    print(f"   ❌ Error checking {doctype_name}: {e}")
            
            frappe.db.commit()
            print("🎉 TREE DOCTYPE FIXES COMPLETED!")
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

# Include all the existing functions (they should be below this point)
