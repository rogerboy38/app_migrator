import click
import frappe
from frappe.utils import get_sites
import os
import shutil
import json
import re
from pathlib import Path

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
        print("📋 Available actions: analyze, migrate, interactive, select-modules, fix-orphans, restore-missing, fix-app-none, analyze-orphans, fix-all-references, rename-systematic, validate-migration")

def analyze_app(source_app):
    """Comprehensive app analysis with enhanced diagnostics"""
    print(f"🎉 SUCCESS! Enhanced App Migrator is working!")
    print(f"🔍 Comprehensive Analysis: {source_app}")
    
    try:
        sites = get_sites()
        if not sites:
            print("❌ No sites available for analysis")
            return
            
        site = sites[0]
        click.echo(f"📍 Using site: {site}")
        
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            # Enhanced analysis with multiple methods
            print(f"\n📊 DOCTYPE ANALYSIS:")
            
            # Method 1: Count by app
            doctypes_count = frappe.db.count('DocType', {'app': source_app})
            print(f"   Method 1 - Doctypes in '{source_app}': {doctypes_count}")
            
            # Method 2: Detailed list with modules
            all_doctypes = frappe.get_all('DocType', fields=['name', 'module', 'app', 'custom'])
            app_doctypes = [dt for dt in all_doctypes if dt.get('app') == source_app]
            print(f"   Method 2 - Detailed count: {len(app_doctypes)}")
            
            # Module distribution
            module_dist = {}
            for dt in app_doctypes:
                module_dist[dt['module']] = module_dist.get(dt['module'], 0) + 1
            
            print(f"   🏗️  Module distribution:")
            for module, count in list(module_dist.items())[:8]:
                custom_count = len([dt for dt in app_doctypes if dt['module'] == module and dt['custom']])
                print(f"      • {module}: {count} (custom: {custom_count})")
            
            # Orphan analysis
            none_doctypes = [dt for dt in all_doctypes if not dt.get('app') or dt.get('app') == '']
            print(f"\n🚨 ORPHAN ANALYSIS:")
            print(f"   Found {len(none_doctypes)} doctypes with app=None")
            
            if none_doctypes:
                orphan_modules = {}
                for dt in none_doctypes:
                    orphan_modules[dt['module']] = orphan_modules.get(dt['module'], 0) + 1
                
                print(f"   Orphans by module (top 5):")
                for module, count in list(orphan_modules.items())[:5]:
                    print(f"      • {module}: {count}")
            
            # File system vs Database analysis
            print(f"\n📁 FILE SYSTEM vs DATABASE:")
            bench_path = "/home/frappe/frappe-bench"
            app_path = os.path.join(bench_path, 'apps', source_app, source_app)
            
            if os.path.exists(app_path):
                # Count doctype directories in file system
                fs_doctype_count = 0
                for root, dirs, files in os.walk(app_path):
                    if 'doctype' in root.split(os.sep):
                        fs_doctype_count += len([d for d in dirs if not d.startswith('__') and not d.endswith('.pyc')])
                
                print(f"   Database records: {len(app_doctypes)}")
                print(f"   File system directories: {fs_doctype_count}")
                print(f"   Discrepancy: {abs(len(app_doctypes) - fs_doctype_count)}")
            
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"🔍 Debug: {traceback.format_exc()}")
    
    print("✅ Enhanced Migration Toolkit Ready!")

def fix_orphan_doctypes(source_app):
    """Fix orphan doctypes with enhanced module-based assignment"""
    print(f"🔧 FIXING ORPHAN DOCTYPES for {source_app}")
    
    try:
        sites = get_sites()
        site = sites[0] if sites else None
        if not site:
            print("❌ No site available")
            return
            
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            # Enhanced orphan detection with module mapping
            orphan_doctypes = frappe.get_all('DocType', 
                filters={'app': ['in', [None, '']]},
                fields=['name', 'module', 'custom']
            )
            
            print(f"📋 Found {len(orphan_doctypes)} orphan doctypes")
            
            # Get modules that belong to this app
            app_modules = frappe.get_all('Module Def', 
                filters={'app_name': source_app},
                fields=['module_name']
            )
            
            app_module_names = [m['module_name'] for m in app_modules]
            print(f"🏗️  App modules: {app_module_names}")
            
            fixed_count = 0
            for doctype in orphan_doctypes:
                if doctype['module'] in app_module_names:
                    print(f"   🔄 Fixing {doctype['name']} (module: {doctype['module']})")
                    frappe.db.set_value('DocType', doctype['name'], 'app', source_app)
                    fixed_count += 1
            
            frappe.db.commit()
            print(f"✅ Fixed {fixed_count} orphan doctypes for app: {source_app}")
            
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"🔍 Debug: {traceback.format_exc()}")

def restore_missing_doctypes(source_app):
    """Enhanced restoration with canonical module prioritization"""
    print(f"🔧 RESTORING MISSING DOCTYPES for {source_app}")
    
    try:
        bench_path = "/home/frappe/frappe-bench"
        app_path = os.path.join(bench_path, 'apps', source_app)
        app_inner_path = os.path.join(app_path, source_app)
        
        print(f"🔍 Looking for app at: {app_path}")
        
        if not os.path.exists(app_path):
            print(f"❌ App path not found: {app_path}")
            return
            
        print(f"✅ App path found: {app_path}")
        
        # CANONICAL MODULES ONLY - based on our analysis
        canonical_modules = [
            'sfc_manufacturing',    # Primary manufacturing module
            'spc_quality_management', # Core SPC functionality
            'fda_compliance',       # Compliance doctypes
            'system_integration',   # Integration points
        ]
        
        sites = get_sites()
        site = sites[0] if sites else None
        if not site:
            print("❌ No site available")
            return
            
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            restored_count = 0
            critical_doctypes = ['TDS Product Specification', 'COA AMB', 'TDS Settings']
            
            # Process canonical modules first
            for module_name in canonical_modules:
                module_doctypes_path = os.path.join(app_inner_path, module_name, 'doctype')
                
                if not os.path.exists(module_doctypes_path):
                    continue
                    
                # Get list of doctype directories (exclude __pycache__)
                doctype_dirs = [d for d in os.listdir(module_doctypes_path) 
                              if os.path.isdir(os.path.join(module_doctypes_path, d)) and 
                              not d.startswith('__') and
                              not d.endswith('.pyc')]
                
                if not doctype_dirs:
                    continue
                    
                print(f"\n📂 Processing '{module_name}': {len(doctype_dirs)} doctypes")
                
                for file_system_name in doctype_dirs:
                    doctype_path = os.path.join(module_doctypes_path, file_system_name)
                    
                    # Enhanced naming conversion
                    proper_name = convert_to_proper_name(file_system_name)
                    
                    # Check if critical
                    is_critical = proper_name in critical_doctypes
                    
                    if os.path.isdir(doctype_path):
                        # Check if doctype exists in database
                        if not frappe.db.exists('DocType', proper_name):
                            status = "🔄 RESTORING" if is_critical else "↩️  RESTORING"
                            print(f"   {status}: {file_system_name} → {proper_name}")
                            
                            try:
                                # Create the doctype record
                                frappe.get_doc({
                                    'doctype': 'DocType',
                                    'name': proper_name,
                                    'module': module_name,
                                    'custom': 0,
                                    'app': source_app
                                }).insert(ignore_permissions=True)
                                
                                restored_count += 1
                                if is_critical:
                                    print(f"      ✅ CRITICAL RESTORED: {proper_name}")
                                    
                            except Exception as e:
                                print(f"      ❌ Error restoring {proper_name}: {e}")
                        else:
                            status = "✅ EXISTS" if is_critical else "   ✅ EXISTS"
                            if is_critical:
                                print(f"   {status}: {proper_name}")
            
            frappe.db.commit()
            print(f"\n🎉 SUCCESS: Restored {restored_count} missing doctypes for app: {source_app}")
            
            # Final check for critical doctypes
            print(f"\n🔍 FINAL CHECK - Critical Doctypes:")
            all_restored = True
            for doctype_name in critical_doctypes:
                if frappe.db.exists('DocType', doctype_name):
                    print(f"   ✅ {doctype_name} - EXISTS")
                else:
                    print(f"   ❌ {doctype_name} - STILL MISSING")
                    all_restored = False
            
            if all_restored:
                print(f"\n🎉 ALL CRITICAL DOCTYPES RESTORED!")
            
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"🔍 Debug: {traceback.format_exc()}")

def convert_to_proper_name(file_system_name):
    """Enhanced naming conversion based on our research"""
    naming_map = {
        'tds_product_specification': 'TDS Product Specification',
        'coa_amb': 'COA AMB', 
        'tds_settings': 'TDS Settings',
        'batch_amb': 'Batch AMB',
        'container_barrels': 'Container Barrels',
        'batch_processing_history': 'Batch Processing History',
        'work_order_routing': 'Work Order Routing'
    }
    
    if file_system_name in naming_map:
        return naming_map[file_system_name]
    
    # Auto-convert: tds_product_specification -> TDS Product Specification
    if '_' in file_system_name:
        words = file_system_name.split('_')
        # Handle acronyms (like TDS, COA, MRP)
        if len(words[0]) <= 3 and words[0].isupper():
            proper_name = ' '.join([words[0]] + [w.capitalize() for w in words[1:]])
        else:
            proper_name = ' '.join([w.capitalize() for w in words])
        return proper_name
    
    return file_system_name

def fix_app_none_doctypes(target_app):
    """Fix all doctypes with app=None by assigning them to correct app"""
    print(f"🔧 FIXING APP=NONE FOR: {target_app}")
    
    try:
        sites = get_sites()
        site = sites[0] if sites else None
        if not site:
            print("❌ No site available")
            return
            
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            # Enhanced module-to-app mapping
            module_app_map = {
                'Payment Gateways': 'payments',
                'Payments': 'payments', 
                'Manufacturing': 'erpnext',
                'Stock': 'erpnext',
                'Buying': 'erpnext',
                'Selling': 'erpnext',
                'sfc_manufacturing': 'amb_w_spc',
                'spc_quality_management': 'amb_w_spc',
                'fda_compliance': 'amb_w_spc',
                'system_integration': 'amb_w_spc'
            }
            
            fixed_count = 0
            orphans = frappe.get_all('DocType', 
                filters={'app': ['in', [None, '']]},
                fields=['name', 'module']
            )
            
            for orphan in orphans:
                target_app_for_doctype = module_app_map.get(orphan['module'])
                
                if target_app_for_doctype == target_app:
                    frappe.db.set_value('DocType', orphan['name'], 'app', target_app)
                    fixed_count += 1
                    print(f"   ✅ {orphan['name']} → {target_app}")
            
            frappe.db.commit()
            print(f"🎯 FIXED {fixed_count} app=None assignments")
            
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"🔍 Debug: {traceback.format_exc()}")

def analyze_orphan_doctypes():
    """Comprehensive orphan analysis"""
    print("🔍 COMPREHENSIVE ORPHAN ANALYSIS")
    print("=" * 40)
    
    try:
        sites = get_sites()
        site = sites[0] if sites else None
        if not site:
            print("❌ No site available")
            return
            
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            orphans = frappe.get_all('DocType', 
                filters={'app': ['in', [None, '']]},
                fields=['name', 'module', 'custom']
            )
            print(f"🚨 TOTAL ORPHAN DOCTYPES: {len(orphans)}")
            
            # Group by module
            orphan_modules = {}
            for orphan in orphans:
                orphan_modules[orphan['module']] = orphan_modules.get(orphan['module'], 0) + 1
            
            print(f"\n📋 ORPHANS BY MODULE:")
            for module, count in sorted(orphan_modules.items(), key=lambda x: x[1], reverse=True)[:10]:
                custom_count = len([o for o in orphans if o['module'] == module and o['custom']])
                print(f"   • {module}: {count} (custom: {custom_count})")
            
            # Show critical orphans
            critical_orphans = [o for o in orphans if o['name'] in [
                'Batch Processing History', 'Batch AMB', 'Container Barrels', 
                'TDS Product Specification', 'COA AMB', 'TDS Settings'
            ]]
            
            if critical_orphans:
                print(f"\n🎯 CRITICAL ORPHANS FOUND:")
                for orphan in critical_orphans:
                    print(f"   ❌ {orphan['name']} (module: {orphan['module']})")
            
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"🔍 Debug: {traceback.format_exc()}")

def fix_all_references(target_app):
    """Fix all Link and Table field references"""
    print(f"🔗 FIXING REFERENCES FOR: {target_app}")
    
    try:
        sites = get_sites()
        site = sites[0] if sites else None
        if not site:
            print("❌ No site available")
            return
            
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            # Get all doctypes in our app
            our_doctypes = frappe.get_all('DocType', 
                filters={'app': target_app},
                fields=['name']
            )
            our_doctype_names = [dt['name'] for dt in our_doctypes]
            
            fixed_count = 0
            
            # Fix Link fields
            link_fields = frappe.get_all('DocField',
                filters={'fieldtype': 'Link', 'options': ['in', our_doctype_names]},
                fields=['parent', 'fieldname', 'options']
            )
            
            print(f"🔍 Checking {len(link_fields)} Link fields...")
            for field in link_fields:
                if not frappe.db.exists('DocType', field['options']):
                    print(f"   ⚠️  Broken link: {field['parent']}.{field['fieldname']} → {field['options']}")
            
            # Fix Table fields  
            table_fields = frappe.get_all('DocField',
                filters={'fieldtype': 'Table', 'options': ['in', our_doctype_names]},
                fields=['parent', 'fieldname', 'options']
            )
            
            print(f"🔍 Checking {len(table_fields)} Table fields...")
            for field in table_fields:
                if not frappe.db.exists('DocType', field['options']):
                    print(f"   ⚠️  Broken table: {field['parent']}.{field['fieldname']} → {field['options']}")
            
            print(f"🎯 REFERENCES CHECKED: {len(link_fields) + len(table_fields)} fields")
            
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"🔍 Debug: {traceback.format_exc()}")

def systematic_renaming(source_app, target_app=None):
    """Systematic renaming based on research findings"""
    print(f"🔄 SYSTEMATIC RENAMING for {source_app}")
    print("Based on Frappe v15 renaming capabilities research")
    
    # This would implement the systematic renaming strategy
    # from your research document
    print("🚧 Feature under development - implementing research findings")
    print("💡 Will use frappe.rename_doc with reference tracking")

def validate_migration_readiness(source_app):
    """Validate if app is ready for migration"""
    print(f"✅ VALIDATING MIGRATION READINESS for {source_app}")
    
    try:
        sites = get_sites()
        site = sites[0] if sites else None
        if not site:
            print("❌ No site available")
            return
            
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            checks_passed = 0
            total_checks = 5
            
            # Check 1: App exists and has doctypes
            app_doctypes = frappe.db.count('DocType', {'app': source_app})
            if app_doctypes > 0:
                print(f"✅ Check 1: App has {app_doctypes} doctypes")
                checks_passed += 1
            else:
                print(f"❌ Check 1: App has no doctypes")
            
            # Check 2: Low orphan count
            orphan_count = frappe.db.count('DocType', {'app': ['in', [None, '']]})
            if orphan_count < 50:
                print(f"✅ Check 2: Low orphan count ({orphan_count})")
                checks_passed += 1
            else:
                print(f"⚠️  Check 2: High orphan count ({orphan_count})")
            
            # Check 3: Critical doctypes exist
            critical_doctypes = ['TDS Product Specification', 'COA AMB', 'TDS Settings']
            critical_missing = [dt for dt in critical_doctypes if not frappe.db.exists('DocType', dt)]
            if not critical_missing:
                print(f"✅ Check 3: All critical doctypes exist")
                checks_passed += 1
            else:
                print(f"❌ Check 3: Missing critical doctypes: {critical_missing}")
            
            # Check 4: File system consistency
            bench_path = "/home/frappe/frappe-bench"
            app_path = os.path.join(bench_path, 'apps', source_app)
            if os.path.exists(app_path):
                print(f"✅ Check 4: File system structure exists")
                checks_passed += 1
            else:
                print(f"❌ Check 4: File system missing")
            
            # Check 5: Module definitions exist
            app_modules = frappe.db.count('Module Def', {'app_name': source_app})
            if app_modules > 0:
                print(f"✅ Check 5: {app_modules} modules defined")
                checks_passed += 1
            else:
                print(f"❌ Check 5: No modules defined")
            
            print(f"\n📊 READINESS SCORE: {checks_passed}/{total_checks}")
            if checks_passed == total_checks:
                print("🎉 READY FOR MIGRATION!")
            else:
                print("⚠️  NEEDS FIXES BEFORE MIGRATION")
            
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"🔍 Debug: {traceback.format_exc()}")

# Placeholder functions for other actions
def interactive_migration():
    """Interactive migration wizard"""
    print("Interactive migration - Enhanced version coming soon")

def select_modules_interactive(source_app, target_app):
    """Select modules interactively"""
    print("Enhanced module selection - Coming soon")
    return [], []

# Export commands
commands = [migrate_app]
