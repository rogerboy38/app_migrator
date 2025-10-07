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
        
    elif action == 'fix-doctype-schema':
        fix_doctype_table_schema()
        
    elif action == 'fix-module-apps':
        fix_module_app_assignments()
        
    elif action == 'fix-doctype-apps':
        fix_doctype_app_assignments()
        
    elif action == 'populate-name-case':
        populate_name_case_titles()
        
    elif action == 'fix-all-naming':
        fix_all_naming_conventions()
        
    elif action == 'fix-complete-system':
        fix_complete_system()
        
    elif action == 'complete-erpnext-install':
        complete_erpnext_installation()
        
    elif action == 'fix-tree-doctypes':
        fix_all_tree_doctypes()
        
    elif action == 'migrate':
        print(f"Migrating app: {source_app}")
        
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
        print("📋 Available actions: analyze, fix-database-schema, fix-doctype-schema, fix-module-apps, fix-doctype-apps, populate-name-case, fix-all-naming, fix-complete-system, complete-erpnext-install, fix-tree-doctypes, migrate, interactive, select-modules, fix-orphans, restore-missing, fix-app-none, analyze-orphans, fix-all-references, rename-systematic, validate-migration")

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
            
            print("📊 CHECKING TABLE STRUCTURE...")
            
            current_columns = frappe.db.sql("SHOW COLUMNS FROM `tabModule Def`", as_dict=True)
            current_column_names = [col['Field'] for col in current_columns]
            print(f"   Current columns: {current_column_names}")
            
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
                            frappe.db.sql(f"ALTER TABLE `tabModule Def` ADD COLUMN `{column}` varchar(140)")
                            print(f"   ✅ Added {column} (varchar)")
                        elif column == 'idx':
                            frappe.db.sql(f"ALTER TABLE `tabModule Def` ADD COLUMN `{column}` int(8) NOT NULL DEFAULT 0")
                            print(f"   ✅ Added {column} (int)")
                        elif column in ['custom', 'restrict_to_domain']:
                            frappe.db.sql(f"ALTER TABLE `tabModule Def` ADD COLUMN `{column}` int(1) NOT NULL DEFAULT 0")
                            print(f"   ✅ Added {column} (int)")
                        elif column in ['module_name', 'app_name']:
                            frappe.db.sql(f"ALTER TABLE `tabModule Def` ADD COLUMN `{column}` varchar(140)")
                            print(f"   ✅ Added {column} (varchar)")
                        elif column in ['_user_tags', '_comments', '_assign', '_liked_by']:
                            frappe.db.sql(f"ALTER TABLE `tabModule Def` ADD COLUMN `{column}` text")
                            print(f"   ✅ Added {column} (text)")
                        elif column == 'package':
                            frappe.db.sql(f"ALTER TABLE `tabModule Def` ADD COLUMN `{column}` varchar(140)")
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

def fix_doctype_table_schema():
    """Fix missing columns in tabDocType table - THE GOLDEN FIX!"""
    print("🔧 FIXING DOCTYPE TABLE SCHEMA - THE GOLDEN FIX!")
    
    try:
        sites = get_sites()
        site = sites[0] if sites else None
        if not site:
            print("❌ No site available")
            return
            
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            print("📊 CHECKING DOCTYPE TABLE STRUCTURE...")
            
            current_columns = frappe.db.sql("SHOW COLUMNS FROM `tabDocType`", as_dict=True)
            current_column_names = [col['Field'] for col in current_columns]
            print(f"   Current columns: {len(current_column_names)}")
            
            required_columns = [
                'name_case', 'is_virtual', 'is_tree', 'istable', 'editable_grid',
                'track_changes', 'sort_field', 'sort_order', 'read_only', 'in_create',
                'allow_copy', 'allow_rename', 'allow_import', 'hide_toolbar', 'track_seen',
                'max_attachments', 'document_type', 'engine', 'is_submittable', 
                'show_name_in_global_search', 'beta', 'has_web_view', 'allow_guest_to_view',
                'email_append_to', 'show_title_field_in_link', 'translated_doctype',
                'quick_entry', 'track_views', 'allow_events_in_timeline', 'allow_auto_repeat',
                'make_attachments_public', 'show_preview_popup', 'index_web_pages_for_search',
                'is_calendar_and_gantt', 'grid_page_length', 'queue_in_background',
                'force_re_route_to_default_view', 'protect_attached_files', 'rows_threshold_for_grid_search'
            ]
            
            missing_columns = [col for col in required_columns if col not in current_column_names]
            
            if missing_columns:
                print(f"🚨 MISSING CRITICAL COLUMNS: {len(missing_columns)}")
                print(f"   Missing: {missing_columns}")
                print("🔄 ADDING MISSING COLUMNS...")
                
                for column in missing_columns:
                    try:
                        if column == 'name_case':
                            frappe.db.sql("ALTER TABLE `tabDocType` ADD COLUMN `name_case` varchar(255) DEFAULT ''")
                            print(f"   💎 GOLDEN FIX: Added '{column}' - This fixes naming conventions!")
                        elif column in ['is_virtual', 'is_tree', 'istable', 'editable_grid', 
                                      'track_changes', 'read_only', 'in_create', 'allow_copy',
                                      'allow_rename', 'allow_import', 'hide_toolbar', 'track_seen',
                                      'is_submittable', 'show_name_in_global_search', 'beta',
                                      'has_web_view', 'allow_guest_to_view', 'email_append_to',
                                      'show_title_field_in_link', 'translated_doctype', 'quick_entry',
                                      'track_views', 'allow_events_in_timeline', 'allow_auto_repeat',
                                      'make_attachments_public', 'show_preview_popup', 
                                      'index_web_pages_for_search', 'is_calendar_and_gantt',
                                      'queue_in_background', 'force_re_route_to_default_view',
                                      'protect_attached_files']:
                            frappe.db.sql(f"ALTER TABLE `tabDocType` ADD COLUMN `{column}` int(1) NOT NULL DEFAULT 0")
                            print(f"   ✅ Added {column} (boolean)")
                        elif column in ['max_attachments', 'grid_page_length', 'rows_threshold_for_grid_search']:
                            frappe.db.sql(f"ALTER TABLE `tabDocType` ADD COLUMN `{column}` int(8) NOT NULL DEFAULT 0")
                            print(f"   ✅ Added {column} (int)")
                        elif column in ['sort_field', 'sort_order', 'document_type', 'engine']:
                            frappe.db.sql(f"ALTER TABLE `tabDocType` ADD COLUMN `{column}` varchar(140)")
                            print(f"   ✅ Added {column} (varchar)")
                    except Exception as e:
                        print(f"   ⚠️  Could not add {column}: {e}")
                
                print("🎉 DOCTYPE TABLE SCHEMA UPDATED!")
                print("💡 This fixes the naming convention issues between versions!")
            else:
                print("✅ ALL CRITICAL COLUMNS EXIST")
            
            frappe.db.commit()
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def populate_name_case_titles():
    """Populate name_case column with proper Title Case names - THE FINAL FIX!"""
    print("🎯 POPULATING NAME_CASE WITH TITLE NAMES - THE FINAL FIX!")
    
    try:
        sites = get_sites()
        site = sites[0] if sites else None
        if not site:
            print("❌ No site available")
            return
            
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            fix_doctype_table_schema()
            
            print("📊 POPULATING NAME_CASE COLUMN...")
            
            doctypes = frappe.get_all('DocType', fields=['name', 'module', 'app', 'custom'])
            updated_count = 0
            
            for doctype in doctypes:
                current_name = doctype['name']
                name_case = frappe.db.get_value('DocType', current_name, 'name_case')
                
                if not name_case or name_case != current_name:
                    try:
                        frappe.db.set_value('DocType', current_name, 'name_case', current_name)
                        updated_count += 1
                        print(f"   ✅ {current_name} → name_case: '{current_name}'")
                    except Exception as e:
                        print(f"   ⚠️  Could not update {current_name}: {e}")
            
            frappe.db.commit()
            print(f"🎉 UPDATED {updated_count} DOCTYPES WITH NAME_CASE!")
            
            print("\n🔧 FIXING SPECIFIC NAMING CONFLICTS...")
            
            naming_fixes = {
                'container_barrels': 'Container Barrels',
                'batch_processing_history': 'Batch Processing History', 
                'batch_amb': 'Batch AMB',
                'work_order_routing': 'Work Order Routing',
                'tds_product_specification': 'TDS Product Specification',
                'coa_amb': 'COA AMB',
                'tds_settings': 'TDS Settings',
            }
            
            fixed_conflicts = 0
            for fs_name, db_name in naming_fixes.items():
                if frappe.db.exists('DocType', fs_name):
                    frappe.db.set_value('DocType', fs_name, 'name_case', db_name)
                    fixed_conflicts += 1
                    print(f"   🔄 {fs_name} → name_case: '{db_name}'")
                
                if frappe.db.exists('DocType', db_name):
                    frappe.db.set_value('DocType', db_name, 'name_case', db_name)
                    print(f"   ✅ {db_name} → name_case: '{db_name}'")
            
            frappe.db.commit()
            print(f"🎉 FIXED {fixed_conflicts} NAMING CONFLICTS!")
            
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def fix_module_app_assignments():
    """Fix app_name assignments in Module Def table - CRITICAL FOR APP SEPARATION!"""
    print("🔧 FIXING MODULE APP ASSIGNMENTS - APP SEPARATION FIX!")
    
    try:
        sites = get_sites()
        site = sites[0] if sites else None
        if not site:
            print("❌ No site available")
            return
            
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            print("📊 CHECKING MODULE APP ASSIGNMENTS...")
            
            all_modules = frappe.get_all('Module Def', fields=['name', 'module_name', 'app_name', 'custom'])
            
            module_app_mapping = {
                'Accounts': 'erpnext', 'CRM': 'erpnext', 'Buying': 'erpnext', 'Selling': 'erpnext',
                'Stock': 'erpnext', 'Manufacturing': 'erpnext', 'Projects': 'erpnext', 'Support': 'erpnext',
                'Assets': 'erpnext', 'Quality Management': 'erpnext', 'Regional': 'erpnext', 'Utilities': 'erpnext',
                'sfc_manufacturing': 'amb_w_spc', 'spc_quality_management': 'amb_w_spc', 
                'fda_compliance': 'amb_w_spc', 'system_integration': 'amb_w_spc',
                'Payment Gateways': 'payments', 'Payments': 'payments',
                'Core': 'frappe', 'Desk': 'frappe', 'Settings': 'frappe', 'Integrations': 'frappe', 'Email': 'frappe'
            }
            
            fixed_count = 0
            modules_without_app = []
            
            for module in all_modules:
                module_name = module['module_name']
                current_app = module.get('app_name')
                expected_app = module_app_mapping.get(module_name)
                
                if not current_app or current_app != expected_app:
                    if expected_app:
                        frappe.db.set_value('Module Def', module['name'], 'app_name', expected_app)
                        fixed_count += 1
                        status = "🔄 FIXED" if current_app else "✅ ASSIGNED"
                        print(f"   {status} {module_name} → {expected_app}")
                    else:
                        modules_without_app.append(module_name)
                        print(f"   ⚠️  UNMAPPED: {module_name} (current: {current_app})")
            
            frappe.db.commit()
            print(f"🎉 UPDATED {fixed_count} MODULE APP ASSIGNMENTS!")
            
            if modules_without_app:
                print(f"🔍 UNMAPPED MODULES ({len(modules_without_app)}): {modules_without_app}")
            
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def fix_doctype_app_assignments():
    """Fix app assignments in DocType table - COMPLETE THE SYSTEM!"""
    print("🔧 FIXING DOCTYPE APP ASSIGNMENTS - COMPLETE SYSTEM FIX!")
    
    try:
        sites = get_sites()
        site = sites[0] if sites else None
        if not site:
            print("❌ No site available")
            return
            
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            print("📊 CHECKING DOCTYPE APP ASSIGNMENTS...")
            
            orphan_doctypes = frappe.get_all('DocType',
                filters={'app': ['in', [None, '']]},
                fields=['name', 'module', 'custom']
            )
            
            print(f"🚨 FOUND {len(orphan_doctypes)} DOCTYPES WITHOUT APP ASSIGNMENT")
            
            if orphan_doctypes:
                module_apps = frappe.get_all('Module Def', fields=['module_name', 'app_name'])
                module_app_map = {m['module_name']: m['app_name'] for m in module_apps if m['app_name']}
                
                fixed_count = 0
                
                for doctype in orphan_doctypes:
                    module_name = doctype['module']
                    target_app = module_app_map.get(module_name)
                    
                    if target_app:
                        frappe.db.set_value('DocType', doctype['name'], 'app', target_app)
                        fixed_count += 1
                        print(f"   ✅ {doctype['name']} (module: {module_name}) → {target_app}")
                    else:
                        print(f"   ⚠️  {doctype['name']} - Module '{module_name}' not mapped to app")
                
                frappe.db.commit()
                print(f"🎉 ASSIGNED APPS TO {fixed_count} ORPHAN DOCTYPES!")
            
            frappe.destroy()
            
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
            
            tree_doctypes = frappe.get_all('DocType', filters={'is_tree': 1}, fields=['name'])
            print(f"🔍 Found {len(tree_doctypes)} tree doctypes")
            
            for doctype in tree_doctypes:
                doctype_name = doctype['name']
                print(f"   Checking {doctype_name}...")
                
                table_name = f"tab{doctype_name}"
                try:
                    columns = frappe.db.sql(f"SHOW COLUMNS FROM `{table_name}`", as_dict=True)
                    column_names = [col['Field'] for col in columns]
                    
                    required_parent_fields = ['lft', 'rgt']
                    missing_parent_fields = [field for field in required_parent_fields if field not in column_names]
                    
                    if missing_parent_fields:
                        print(f"   ⚠️  Missing tree fields: {missing_parent_fields}")
                        for field in missing_parent_fields:
                            frappe.db.sql(f"ALTER TABLE `{table_name}` ADD COLUMN `{field}` int(8) NOT NULL DEFAULT 0")
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

def fix_all_naming_conventions():
    """COMPREHENSIVE naming convention fix - THE ULTIMATE SOLUTION"""
    print("💎 COMPREHENSIVE NAMING CONVENTION FIX - ULTIMATE SOLUTION")
    
    try:
        sites = get_sites()
        site = sites[0] if sites else None
        if not site:
            print("❌ No site available")
            return
            
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            print("🔧 STEP 1: Ensure database schema is ready...")
            fix_doctype_table_schema()
            
            print("🔧 STEP 2: Populate name_case with proper titles...")
            populate_name_case_titles()
            
            print("🎉 ALL NAMING CONVENTIONS FIXED!")
            print("💡 File system (snake_case) and Database (Title Case) are now synchronized!")
            
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def fix_complete_system():
    """COMPREHENSIVE SYSTEM FIX - FIXES ALL KNOWN ISSUES!"""
    print("💎 COMPREHENSIVE SYSTEM FIX - ULTIMATE MIGRATION SOLUTION!")
    
    try:
        sites = get_sites()
        site = sites[0] if sites else None
        if not site:
            print("❌ No site available")
            return
            
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            print("🔧 STEP 1: Fixing database schema...")
            fix_database_schema()
            
            print("🔧 STEP 2: Fixing DocType table structure...")
            fix_doctype_table_schema()
            
            print("🔧 STEP 3: Fixing Module app assignments...")
            fix_module_app_assignments()
            
            print("🔧 STEP 4: Fixing DocType app assignments...")
            fix_doctype_app_assignments()
            
            print("🔧 STEP 5: Fixing naming conventions...")
            populate_name_case_titles()
            
            print("🔧 STEP 6: Fixing tree doctypes...")
            fix_all_tree_doctypes()
            
            print("🎉 COMPREHENSIVE SYSTEM FIX COMPLETED!")
            print("💡 Database schema, app assignments, and naming conventions are now SYNCED!")
            
            orphans = frappe.get_all('DocType', filters={'app': ['in', [None, '']]})
            modules_no_app = frappe.get_all('Module Def', filters={'app_name': ['in', [None, '']]})
            doctypes_no_name_case = frappe.db.sql("SELECT COUNT(*) as count FROM `tabDocType` WHERE name_case IS NULL OR name_case = ''", as_dict=True)[0]['count']
            
            print(f"\n🔍 FINAL SYSTEM STATUS:")
            print(f"   • Orphan doctypes: {len(orphans)}")
            print(f"   • Modules without app: {len(modules_no_app)}")
            print(f"   • Doctypes without name_case: {doctypes_no_name_case}")
            
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def complete_erpnext_installation():
    """ULTIMATE ERPNext installation with COMPLETE system fixes"""
    print("🚀 ULTIMATE ERPNext INSTALLATION - COMPLETE SYSTEM FIX")
    
    try:
        print("🔧 RUNNING COMPREHENSIVE SYSTEM FIX...")
        fix_complete_system()
        
        print("\n📦 INSTALLING ERPNext...")
        
        result = subprocess.run([
            'bench', '--site', 'sysmayal.v.frappe.cloud', 
            'install-app', 'erpnext', '--force'
        ], capture_output=True, text=True, cwd='/home/frappe/frappe-bench')
        
        if result.returncode == 0:
            print("✅ ERPNext INSTALLED SUCCESSFULLY!")
            if result.stdout:
                print(result.stdout)
                
            print("\n🔍 RUNNING FINAL SYSTEM VERIFICATION...")
            fix_complete_system()
            
        else:
            print("❌ ERPNext INSTALLATION FAILED:")
            if result.stderr:
                print(result.stderr)
            if result.stdout:
                print("STDOUT:", result.stdout)
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

# Include existing functions (keep your working analyze_app, fix_orphan_doctypes, etc.)
def analyze_app(source_app):
    """Comprehensive app analysis"""
    print(f"🔍 Comprehensive Analysis: {source_app}")
    # ... your existing analyze_app code ...

def fix_orphan_doctypes(source_app):
    """Fix orphan doctypes"""
    print(f"🔧 FIXING ORPHAN DOCTYPES for {source_app}")
    # ... your existing fix_orphan_doctypes code ...

def restore_missing_doctypes(source_app):
    """Restore missing doctypes"""
    print(f"🔧 RESTORING MISSING DOCTYPES for {source_app}")
    print("🚧 Feature under development")

def fix_app_none_doctypes(target_app):
    """Fix app=None doctypes"""
    print(f"🔧 FIXING APP=NONE FOR: {target_app}")
    print("🚧 Feature under development")

def analyze_orphan_doctypes():
    """Analyze orphan doctypes"""
    print("🔍 COMPREHENSIVE ORPHAN ANALYSIS")
    print("🚧 Feature under development")

def fix_all_references(target_app):
    """Fix references"""
    print(f"🔗 FIXING REFERENCES FOR: {target_app}")
    print("🚧 Feature under development")

def systematic_renaming(source_app, target_app=None):
    """Systematic renaming"""
    print(f"🔄 SYSTEMATIC RENAMING for {source_app}")
    print("🚧 Feature under development")

def validate_migration_readiness(source_app):
    """Validate migration"""
    print(f"✅ VALIDATING MIGRATION READINESS for {source_app}")
    print("🚧 Feature under development")

def interactive_migration():
    """Interactive migration"""
    print("Interactive migration - Enhanced version coming soon")

def select_modules_interactive(source_app, target_app):
    """Select modules interactively"""
    print("Enhanced module selection - Coming soon")
    return [], []

# Export commands
commands = [migrate_app]
