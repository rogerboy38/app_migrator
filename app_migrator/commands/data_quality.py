"""
Data Quality Module - V5.0.0
Data quality operations including orphan fixing, restoration, and reference management

Extracted and enhanced from App Migrator V2
Features:
- Fix orphan doctypes
- Restore missing doctypes
- Fix app=None assignments
- Fix all references (Link and Table fields)
- Data integrity verification
"""

import frappe
from frappe.utils import get_sites
import os
import json
from pathlib import Path


def ensure_frappe_connection():
    """Ensure Frappe connection is active - CRITICAL FOR LONG-RUNNING OPERATIONS"""
    try:
        frappe.db.sql("SELECT 1")
        return True
    except Exception:
        try:
            sites = get_sites()
            site = sites[0] if sites else None
            if site:
                frappe.init(site=site)
                frappe.connect()
                print("   🔄 Session reconnected")
                return True
        except Exception as e:
            print(f"   ❌ Failed to reconnect: {e}")
            return False
    return False


def fix_orphan_doctypes(source_app):
    """
    Fix orphan doctypes with enhanced module-based assignment
    
    Orphans are doctypes that:
    1. Have no module assigned
    2. Have a module that doesn't belong to the app
    """
    print(f"🔧 FIXING ORPHAN DOCTYPES: {source_app}")
    print("=" * 70)
    
    try:
        if not ensure_frappe_connection():
            print("❌ Cannot establish Frappe connection")
            return False
        
        # Get all doctypes for the app
        all_app_doctypes = frappe.get_all('DocType', 
            filters={'app': source_app}, 
            fields=['name', 'module', 'app']
        )
        
        # Identify orphans
        orphans = []
        for dt in all_app_doctypes:
            if not dt['module']:
                orphans.append({
                    'doctype': dt['name'],
                    'issue': 'NO_MODULE',
                    'current_module': None
                })
            else:
                # Check if module belongs to the app
                module_check = frappe.get_all('Module Def', 
                    filters={'module_name': dt['module'], 'app_name': source_app}
                )
                if not module_check:
                    orphans.append({
                        'doctype': dt['name'],
                        'issue': 'WRONG_MODULE',
                        'current_module': dt['module']
                    })
        
        print(f"\n📊 Found {len(orphans)} orphan doctypes\n")
        
        if not orphans:
            print("✅ No orphan doctypes found")
            return True
        
        # Display orphans
        print("🔍 Orphan Doctypes:")
        for orphan in orphans[:20]:
            issue_icon = "⚠️" if orphan['issue'] == 'NO_MODULE' else "🔄"
            print(f"  {issue_icon} {orphan['doctype']:<40s} - {orphan['issue']} (module: {orphan['current_module']})")
        
        if len(orphans) > 20:
            print(f"  ... and {len(orphans) - 20} more")
        
        # Confirm action
        confirm = input(f"\n⚠️  Fix {len(orphans)} orphan doctypes? (y/N): ").strip().lower()
        if confirm != 'y':
            print("🚫 Operation cancelled")
            return False
        
        # Get valid modules for the app
        app_modules = frappe.get_all('Module Def', 
            filters={'app_name': source_app}, 
            fields=['module_name']
        )
        module_names = [m['module_name'] for m in app_modules]
        
        if not module_names:
            print(f"❌ No modules found for {source_app}")
            return False
        
        # Fix orphans
        fixed_count = 0
        for orphan in orphans:
            try:
                if orphan['issue'] == 'NO_MODULE' and module_names:
                    frappe.db.set_value('DocType', orphan['doctype'], 'module', module_names[0])
                    print(f"  ✅ Assigned {orphan['doctype']} to module: {module_names[0]}")
                    fixed_count += 1
                elif orphan['issue'] == 'WRONG_MODULE' and module_names:
                    frappe.db.set_value('DocType', orphan['doctype'], 'module', module_names[0])
                    print(f"  ✅ Reassigned {orphan['doctype']} from {orphan['current_module']} to {module_names[0]}")
                    fixed_count += 1
            except Exception as e:
                print(f"  ❌ Failed to fix {orphan['doctype']}: {e}")
        
        frappe.db.commit()
        
        print("\n" + "=" * 70)
        print("📊 ORPHAN FIX SUMMARY")
        print("=" * 70)
        print(f"  ✅ Fixed: {fixed_count}")
        print(f"  📋 Total orphans: {len(orphans)}")
        print("🎉 ORPHAN FIX COMPLETED!")
        
        return True
        
    except Exception as e:
        print(f"❌ Fix orphan doctypes failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def restore_missing_doctypes(source_app):
    """
    Restore missing doctype files for doctypes that exist in database
    Creates basic JSON files for doctypes missing from file system
    """
    print(f"🔧 RESTORING MISSING DOCTYPES: {source_app}")
    print("=" * 70)
    
    try:
        if not ensure_frappe_connection():
            print("❌ Cannot establish Frappe connection")
            return False
        
        # Get all doctypes for the app
        app_doctypes = frappe.get_all('DocType', 
            filters={'app': source_app}, 
            fields=['name', 'module', 'custom']
        )
        
        bench_path = Path('/home/frappe/frappe-bench')
        app_path = bench_path / 'apps' / source_app / source_app
        
        if not app_path.exists():
            print(f"❌ App path not found: {app_path}")
            return False
        
        print(f"\n📊 Checking {len(app_doctypes)} doctypes in {source_app}...\n")
        
        missing_files = []
        
        # Check each doctype for missing file
        for doctype in app_doctypes:
            doctype_name = doctype['name']
            module_name = doctype['module']
            
            if not module_name:
                continue
            
            # Check standard naming
            expected_path = app_path / module_name / f"{doctype_name}.json"
            # Check snake_case naming
            snake_name = frappe.scrub(doctype_name)
            snake_path = app_path / module_name / f"{snake_name}.json"
            
            if not expected_path.exists() and not snake_path.exists():
                missing_files.append({
                    'doctype': doctype_name,
                    'module': module_name,
                    'custom': doctype.get('custom', 0)
                })
        
        print(f"📊 Found {len(missing_files)} missing doctype files\n")
        
        if not missing_files:
            print("✅ All doctype files are present")
            return True
        
        # Display missing files
        print("🔍 Missing Doctype Files:")
        for missing in missing_files[:20]:
            custom_flag = " (CUSTOM)" if missing['custom'] else ""
            print(f"  • {missing['doctype']:<40s} in {missing['module']}{custom_flag}")
        
        if len(missing_files) > 20:
            print(f"  ... and {len(missing_files) - 20} more")
        
        # Confirm action
        confirm = input(f"\n⚠️  Create {len(missing_files)} missing doctype files? (y/N): ").strip().lower()
        if confirm != 'y':
            print("🚫 Operation cancelled")
            return False
        
        created_count = 0
        error_count = 0
        
        # Create missing files
        for missing in missing_files:
            try:
                # Get full doctype definition from database
                doc = frappe.get_doc('DocType', missing['doctype'])
                
                # Create module directory if it doesn't exist
                module_dir = app_path / missing['module']
                module_dir.mkdir(parents=True, exist_ok=True)
                
                # Save doctype JSON
                file_path = module_dir / f"{missing['doctype']}.json"
                with open(file_path, 'w') as f:
                    f.write(doc.as_json())
                
                created_count += 1
                print(f"  ✅ Created: {missing['doctype']}.json")
                
            except Exception as e:
                error_count += 1
                print(f"  ❌ Failed to create {missing['doctype']}: {e}")
        
        print("\n" + "=" * 70)
        print("📊 RESTORATION SUMMARY")
        print("=" * 70)
        print(f"  ✅ Files created: {created_count}")
        print(f"  ❌ Errors: {error_count}")
        
        if created_count > 0:
            print("🎉 Missing doctype files restored successfully!")
        
        return True
        
    except Exception as e:
        print(f"❌ Restore missing doctypes failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def fix_app_none_doctypes(target_app):
    """
    Fix all doctypes with app=None by assigning them to correct app
    Assigns based on module definition
    """
    print(f"🔧 FIXING APP=NONE DOCTYPES: {target_app}")
    print("=" * 70)
    
    try:
        if not ensure_frappe_connection():
            print("❌ Cannot establish Frappe connection")
            return False
        
        # Get all doctypes with app=None
        app_none_doctypes = frappe.get_all('DocType', 
            filters={'app': ['is', 'not set']}, 
            fields=['name', 'module']
        )
        
        print(f"\n📊 Found {len(app_none_doctypes)} doctypes with app=None\n")
        
        if not app_none_doctypes:
            print("✅ No doctypes with app=None found")
            return True
        
        # Display doctypes to be fixed
        print("🔍 Doctypes to be fixed:")
        for dt in app_none_doctypes[:20]:
            print(f"  • {dt['name']:<40s} (module: {dt['module']})")
        
        if len(app_none_doctypes) > 20:
            print(f"  ... and {len(app_none_doctypes) - 20} more")
        
        # Confirm action
        confirm = input(f"\n⚠️  Fix {len(app_none_doctypes)} doctypes with app=None? (y/N): ").strip().lower()
        if confirm != 'y':
            print("🚫 Operation cancelled")
            return False
        
        fixed_count = 0
        error_count = 0
        
        # Fix each doctype
        for dt in app_none_doctypes:
            try:
                # Determine correct app based on module
                if dt['module']:
                    module_def = frappe.get_all('Module Def',
                        filters={'module_name': dt['module']},
                        fields=['app_name'],
                        limit=1
                    )
                    
                    if module_def and module_def[0]['app_name']:
                        app_name = module_def[0]['app_name']
                        frappe.db.set_value('DocType', dt['name'], 'app', app_name)
                        print(f"  ✅ Fixed {dt['name']} → {app_name}")
                        fixed_count += 1
                    else:
                        # Fallback to target app
                        frappe.db.set_value('DocType', dt['name'], 'app', target_app)
                        print(f"  ✅ Fixed {dt['name']} → {target_app} (fallback)")
                        fixed_count += 1
                else:
                    # No module, assign to target app
                    frappe.db.set_value('DocType', dt['name'], 'app', target_app)
                    print(f"  ✅ Fixed {dt['name']} → {target_app} (no module)")
                    fixed_count += 1
                    
            except Exception as e:
                error_count += 1
                print(f"  ❌ Failed to fix {dt['name']}: {e}")
        
        frappe.db.commit()
        
        print("\n" + "=" * 70)
        print("📊 APP=NONE FIX SUMMARY")
        print("=" * 70)
        print(f"  ✅ Fixed: {fixed_count}")
        print(f"  ❌ Errors: {error_count}")
        print("🎉 APP=NONE FIX COMPLETED!")
        
        return True
        
    except Exception as e:
        print(f"❌ Fix app=None doctypes failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def fix_all_references(target_app):
    """
    Analyze and report all Link and Table field references to doctypes in target app
    Helps identify dependencies before migration
    """
    print(f"🔗 ANALYZING REFERENCES: {target_app}")
    print("=" * 70)
    
    try:
        if not ensure_frappe_connection():
            print("❌ Cannot establish Frappe connection")
            return False
        
        # Get all doctypes in target app
        target_doctypes = frappe.get_all('DocType', 
            filters={'app': target_app}, 
            fields=['name']
        )
        target_doctype_names = [dt['name'] for dt in target_doctypes]
        
        print(f"\n📊 Analyzing references to {len(target_doctype_names)} doctypes in {target_app}\n")
        
        # Get all doctypes to check
        all_doctypes = frappe.get_all('DocType', fields=['name', 'app'])
        
        references = {}
        checked_count = 0
        
        for source_dt in all_doctypes:
            try:
                doc = frappe.get_doc('DocType', source_dt['name'])
                doc_references = []
                
                # Check all fields
                for field in doc.fields:
                    if field.fieldtype in ['Link', 'Table'] and field.options in target_doctype_names:
                        doc_references.append({
                            'fieldname': field.fieldname,
                            'fieldtype': field.fieldtype,
                            'target': field.options
                        })
                
                if doc_references:
                    references[source_dt['name']] = {
                        'app': source_dt.get('app', 'Unknown'),
                        'references': doc_references
                    }
                    
                    print(f"  🔗 {source_dt['name']} ({source_dt.get('app', 'Unknown')})")
                    for ref in doc_references:
                        print(f"      → {ref['fieldname']} ({ref['fieldtype']}) → {ref['target']}")
                
                checked_count += 1
                if checked_count % 50 == 0:
                    print(f"\n  📋 Progress: {checked_count}/{len(all_doctypes)} doctypes checked...\n")
                    
            except Exception as e:
                # Skip doctypes that can't be loaded
                pass
        
        print("\n" + "=" * 70)
        print("📊 REFERENCE ANALYSIS SUMMARY")
        print("=" * 70)
        print(f"  📋 Doctypes checked: {checked_count}")
        print(f"  🔗 Doctypes with references: {len(references)}")
        print(f"  🎯 Target doctypes: {len(target_doctype_names)}")
        
        if references:
            print(f"\n⚠️  {len(references)} doctypes have references to {target_app}")
            print("💡 Review these dependencies before migration")
        else:
            print("\n✅ No external references found")
        
        print("🎉 REFERENCE ANALYSIS COMPLETED!")
        
        return True
        
    except Exception as e:
        print(f"❌ Fix references failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_data_integrity(app_name):
    """
    Comprehensive data integrity verification for an app
    Checks for orphans, missing files, app=None, and other issues
    """
    print(f"🔍 DATA INTEGRITY VERIFICATION: {app_name}")
    print("=" * 70)
    
    try:
        if not ensure_frappe_connection():
            print("❌ Cannot establish Frappe connection")
            return False
        
        issues = {
            'orphans': [],
            'missing_files': [],
            'app_none': [],
            'no_module': []
        }
        
        # Get all doctypes for the app
        app_doctypes = frappe.get_all('DocType',
            filters={'app': app_name},
            fields=['name', 'module', 'custom', 'app']
        )
        
        print(f"\n📊 Checking {len(app_doctypes)} doctypes...\n")
        
        bench_path = Path('/home/frappe/frappe-bench')
        app_path = bench_path / 'apps' / app_name / app_name
        
        for dt in app_doctypes:
            # Check for no module
            if not dt['module']:
                issues['no_module'].append(dt['name'])
            else:
                # Check for orphan module
                module_check = frappe.get_all('Module Def',
                    filters={'module_name': dt['module'], 'app_name': app_name}
                )
                if not module_check:
                    issues['orphans'].append(dt['name'])
            
            # Check for app=None
            if not dt['app']:
                issues['app_none'].append(dt['name'])
            
            # Check for missing file
            if app_path.exists() and dt['module']:
                expected_path = app_path / dt['module'] / f"{dt['name']}.json"
                snake_path = app_path / dt['module'] / f"{frappe.scrub(dt['name'])}.json"
                if not expected_path.exists() and not snake_path.exists():
                    issues['missing_files'].append(dt['name'])
        
        # Display results
        print("=" * 70)
        print("📊 DATA INTEGRITY REPORT")
        print("=" * 70)
        
        total_issues = sum(len(v) for v in issues.values())
        
        print(f"\n✅ Doctypes checked: {len(app_doctypes)}")
        print(f"⚠️  Total issues found: {total_issues}\n")
        
        for issue_type, doctype_list in issues.items():
            if doctype_list:
                icon = "⚠️"
                print(f"{icon} {issue_type.upper()}: {len(doctype_list)}")
                for dt in doctype_list[:5]:
                    print(f"    • {dt}")
                if len(doctype_list) > 5:
                    print(f"    ... and {len(doctype_list) - 5} more")
                print()
        
        if total_issues == 0:
            print("🎉 No data integrity issues found!")
        else:
            print("💡 Use data_quality functions to fix these issues:")
            if issues['orphans'] or issues['no_module']:
                print("  • fix_orphan_doctypes(app_name)")
            if issues['missing_files']:
                print("  • restore_missing_doctypes(app_name)")
            if issues['app_none']:
                print("  • fix_app_none_doctypes(app_name)")
        
        print("=" * 70)
        
        return total_issues == 0
        
    except Exception as e:
        print(f"❌ Integrity verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # For testing
    import sys
    if len(sys.argv) > 1:
        app_name = sys.argv[1]
        verify_data_integrity(app_name)
    else:
        print("Usage: python data_quality.py <app_name>")
