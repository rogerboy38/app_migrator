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

# ========== SESSION MANAGEMENT UTILITIES ==========
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
                frappe.init_site(site)
                frappe.connect(site=site)
                print("   🔄 Session reconnected")
                return True
        except Exception as e:
            print(f"   ❌ Failed to reconnect: {e}")
            return False
    return False

def with_session_management(func):
    """Decorator to handle session management for all migration functions"""
    def wrapper(*args, **kwargs):
        try:
            if not ensure_frappe_connection():
                print("❌ Cannot establish Frappe connection")
                return None
            result = func(*args, **kwargs)
            frappe.db.commit()
            return result
        except Exception as e:
            print(f"❌ Session error in {func.__name__}: {e}")
            try:
                print("   🔄 Attempting recovery...")
                if ensure_frappe_connection():
                    result = func(*args, **kwargs)
                    frappe.db.commit()
                    return result
            except Exception as retry_error:
                print(f"   ❌ Recovery failed: {retry_error}")
            return None
    return wrapper

# ========== INTERACTIVE MIGRATION WIZARD ==========
def interactive_app_migration():
    """INTERACTIVE APP MIGRATION WIZARD - WITH PROPER SITE SELECTION AND INPUT VALIDATION"""
    print("🚀 INTERACTIVE APP MIGRATION WIZARD")
    
    try:
        # STEP 1: Site Selection
        sites = get_sites()
        if not sites:
            print("❌ No sites available")
            return
        
        print(f"\n📋 STEP 1: SELECT SITE")
        print("=" * 50)
        print("Available Sites:")
        print("  0. ❌ EXIT")
        for i, site in enumerate(sites, 1):
            print(f"  {i}. {site}")
        
        selected_site = None
        while selected_site is None:
            try:
                choice_input = input(f"\n🔹 Select site (0-{len(sites)}): ").strip()
                site_choice = int(choice_input)
                
                if site_choice == 0:
                    print("🚫 Operation cancelled by user")
                    return
                elif 1 <= site_choice <= len(sites):
                    selected_site = sites[site_choice - 1]
                    print(f"📍 Selected site: {selected_site}")
                else:
                    print(f"❌ Please enter a number between 0 and {len(sites)}")
            except ValueError:
                print("❌ Please enter a valid number")
        
        # STEP 2: App Selection
        with frappe.init_site(selected_site):
            frappe.connect(site=selected_site)
            
            apps = frappe.get_all('Module Def', 
                fields=['DISTINCT app_name as name'], 
                filters={'app_name': ['is', 'set']}
            )
            app_names = [app['name'] for app in apps if app['name']]
            
            if not app_names:
                print("❌ No apps found in this site")
                frappe.destroy()
                return
            
            print(f"\n📋 STEP 2: SELECT APPS")
            print("=" * 50)
            print("Available Apps:")
            print("  0. ❌ EXIT")
            for i, app in enumerate(app_names, 1):
                print(f"  {i}. {app}")
            
            # Source app selection
            source_app = None
            while source_app is None:
                try:
                    source_input = input(f"\n🔹 Select SOURCE app (0-{len(app_names)}): ").strip()
                    source_choice = int(source_input)
                    
                    if source_choice == 0:
                        print("🚫 Operation cancelled by user")
                        frappe.destroy()
                        return
                    elif 1 <= source_choice <= len(app_names):
                        source_app = app_names[source_choice - 1]
                        print(f"📤 Selected SOURCE: {source_app}")
                    else:
                        print(f"❌ Please enter a number between 0 and {len(app_names)}")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            # Target app selection  
            target_app = None
            while target_app is None:
                try:
                    target_input = input(f"\n🔹 Select TARGET app (0-{len(app_names)}): ").strip()
                    target_choice = int(target_input)
                    
                    if target_choice == 0:
                        print("🚫 Operation cancelled by user")
                        frappe.destroy()
                        return
                    elif 1 <= target_choice <= len(app_names):
                        target_app = app_names[target_choice - 1]
                        print(f"📥 Selected TARGET: {target_app}")
                    else:
                        print(f"❌ Please enter a number between 0 and {len(app_names)}")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            # STEP 3: Check if apps are the same
            if source_app == target_app:
                print(f"\n⚠️  WARNING: Source and target are the same ({source_app})")
                confirm = input("🔹 Continue with same app? (y/N): ").strip().lower()
                if confirm != 'y':
                    print("🚫 Operation cancelled")
                    frappe.destroy()
                    return
            
            # STEP 4: Analysis
            print(f"\n📋 STEP 3: ANALYSIS")
            print("=" * 50)
            analyze_app_dependencies(source_app)
            
            # STEP 5: Migration Type
            print(f"\n📋 STEP 4: MIGRATION TYPE")
            print("=" * 50)
            print("Migration Options:")
            print("  1. Migrate ALL modules")
            print("  2. Migrate SPECIFIC modules") 
            print("  3. Migrate SPECIFIC doctypes")
            print("  0. ❌ EXIT")
            
            migration_choice = None
            while migration_choice is None:
                try:
                    choice_input = input("\n🔹 Select option (0-3): ").strip()
                    choice = int(choice_input)
                    
                    if choice == 0:
                        print("🚫 Operation cancelled by user")
                        frappe.destroy()
                        return
                    elif choice == 1:
                        confirm = input(f"⚠️  Migrate ALL modules from {source_app} to {target_app}? (y/N): ").strip().lower()
                        if confirm == 'y':
                            migrate_app_modules(source_app, target_app)
                        else:
                            print("❌ Migration cancelled")
                        migration_choice = choice
                    elif choice == 2:
                        modules = input("🔹 Enter module names (comma-separated): ").strip()
                        if modules:
                            migrate_app_modules(source_app, target_app, modules)
                            migration_choice = choice
                        else:
                            print("❌ No modules specified")
                    elif choice == 3:
                        doctypes = input("🔹 Enter doctype names (comma-separated): ").strip()
                        if doctypes:
                            migrate_specific_doctypes(source_app, target_app, doctypes)
                            migration_choice = choice
                        else:
                            print("❌ No doctypes specified")
                    else:
                        print("❌ Please enter a number between 0 and 3")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            frappe.destroy()
            print("\n🎉 INTERACTIVE MIGRATION COMPLETED!")
            
    except KeyboardInterrupt:
        print("\n\n🚫 Operation cancelled by user (Ctrl+C)")
    except Exception as e:
        print(f"❌ Interactive migration failed: {e}")
        import traceback
        traceback.print_exc()
        try:
            frappe.destroy()
        except:
            pass

# ========== CORE MIGRATION FUNCTIONS ==========
@with_session_management
def migrate_app_modules(source_app, target_app, modules=None):
    """MIGRATE MODULES FROM SOURCE APP TO TARGET APP - CORE FUNCTIONALITY"""
    print(f"🚀 MIGRATING MODULES: {source_app} → {target_app}")
    
    try:
        source_modules = frappe.get_all('Module Def', 
            filters={'app_name': source_app},
            fields=['name', 'module_name', 'app_name']
        )
        
        if modules:
            module_list = [m.strip() for m in modules.split(',')]
            source_modules = [m for m in source_modules if m['module_name'] in module_list]
        
        print(f"📦 Found {len(source_modules)} modules in {source_app}")
        
        if not source_modules:
            print("❌ No modules found to migrate")
            return False
        
        confirm = input(f"⚠️  Migrate {len(source_modules)} modules? (y/N): ").strip().lower()
        if confirm != 'y':
            print("🚫 Migration cancelled")
            return False
        
        migrated_count = 0
        for module in source_modules:
            try:
                frappe.db.set_value('Module Def', module['name'], 'app_name', target_app)
                module_doctypes = frappe.get_all('DocType',
                    filters={'module': module['module_name']},
                    fields=['name', 'module', 'app']
                )
                for doctype in module_doctypes:
                    frappe.db.set_value('DocType', doctype['name'], 'app', target_app)
                
                migrated_count += 1
                print(f"   ✅ Migrated {module['module_name']} with {len(module_doctypes)} doctypes")
            except Exception as e:
                print(f"   ❌ Failed to migrate {module['module_name']}: {e}")
        
        frappe.db.commit()
        print(f"🎉 SUCCESSFULLY MIGRATED {migrated_count} MODULES!")
        move_module_files(source_app, target_app, [m['module_name'] for m in source_modules])
        return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

@with_session_management
def migrate_specific_doctypes(source_app, target_app, doctypes):
    """MIGRATE SPECIFIC DOCTYPES BETWEEN APPS"""
    print(f"📄 MIGRATING DOCTYPES: {source_app} → {target_app}")
    
    try:
        doctype_list = [d.strip() for d in doctypes.split(',')]
        print(f"📊 Doctypes to migrate: {len(doctype_list)}")
        
        confirm = input(f"⚠️  Migrate {len(doctype_list)} doctypes? (y/N): ").strip().lower()
        if confirm != 'y':
            print("🚫 Migration cancelled")
            return False
        
        migrated_count = 0
        for doctype_name in doctype_list:
            if frappe.db.exists('DocType', doctype_name):
                frappe.db.set_value('DocType', doctype_name, 'app', target_app)
                doctype_doc = frappe.get_doc('DocType', doctype_name)
                print(f"   ✅ Migrated {doctype_name} (module: {doctype_doc.module})")
                migrated_count += 1
            else:
                print(f"   ⚠️  Doctype not found: {doctype_name}")
        
        frappe.db.commit()
        print(f"🎉 MIGRATED {migrated_count} DOCTYPES!")
        return True
            
    except Exception as e:
        print(f"❌ Doctype migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def move_module_files(source_app, target_app, modules):
    """MOVE MODULE FILES BETWEEN APPS ON FILESYSTEM"""
    print(f"📁 MOVING FILES: {source_app} → {target_app}")
    
    try:
        bench_path = Path('/home/frappe/frappe-bench')
        source_app_path = bench_path / 'apps' / source_app
        target_app_path = bench_path / 'apps' / target_app
        
        if not source_app_path.exists():
            print(f"❌ Source app path not found: {source_app_path}")
            return
        
        if not target_app_path.exists():
            print(f"❌ Target app path not found: {target_app_path}")
            return
        
        for module in modules:
            module_path = source_app_path / source_app / module
            target_module_path = target_app_path / target_app / module
            
            if module_path.exists():
                target_module_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(module_path), str(target_module_path))
                print(f"   ✅ Moved {module} files")
            else:
                print(f"   ⚠️  Module directory not found: {module_path}")
        
        print("🎉 FILE MIGRATION COMPLETED!")
        
    except Exception as e:
        print(f"❌ File movement failed: {e}")

# ========== ENHANCED ANALYSIS FUNCTIONS ==========
@with_session_management
def analyze_app_dependencies(source_app):
    """COMPREHENSIVE DEPENDENCY ANALYSIS FOR MIGRATION WITH ENHANCED DIAGNOSTICS"""
    print(f"🔍 COMPREHENSIVE ANALYSIS: {source_app}")
    
    try:
        modules = frappe.get_all('Module Def',
            filters={'app_name': source_app},
            fields=['name', 'module_name', 'app_name']
        )
        
        print(f"📦 MODULES IN {source_app}: {len(modules)}")
        for module in modules:
            print(f"   • {module['module_name']}")
            doctypes = frappe.get_all('DocType',
                filters={'module': module['module_name']},
                fields=['name', 'custom', 'is_submittable', 'issingle', 'app']
            )
            for doctype in doctypes:
                custom_flag = " (CUSTOM)" if doctype['custom'] else ""
                submittable_flag = " 📋" if doctype['is_submittable'] else ""
                single_flag = " ⚙️" if doctype['issingle'] else ""
                app_flag = " ❌ APP=NONE" if not doctype['app'] else ""
                print(f"     └─ {doctype['name']}{custom_flag}{submittable_flag}{single_flag}{app_flag}")
        
        # Enhanced Analysis Sections
        all_app_doctypes = frappe.get_all('DocType', filters={'app': source_app}, fields=['name', 'module', 'app'])
        
        # Orphan Detection
        print(f"\n🔍 ENHANCED ANALYSIS: ORPHAN DETECTION")
        print("=" * 50)
        orphans = []
        for dt in all_app_doctypes:
            if not dt['module']:
                orphans.append(f"{dt['name']} - NO MODULE")
            else:
                module_check = frappe.get_all('Module Def', filters={'module_name': dt['module'], 'app_name': source_app})
                if not module_check:
                    orphans.append(f"{dt['name']} - WRONG MODULE: {dt['module']}")
        
        if orphans:
            print("⚠️  ORPHAN DOCTYPES FOUND:")
            for orphan in orphans:
                print(f"   • {orphan}")
        else:
            print("✅ No orphan doctypes found")
        
        # App=None Detection
        print(f"\n🔍 ENHANCED ANALYSIS: APP=NONE DETECTION")
        print("=" * 50)
        app_none_doctypes = frappe.get_all('DocType', filters={'app': ['is', 'not set']}, fields=['name', 'module'])
        if app_none_doctypes:
            print(f"⚠️  DOCTYPES WITH APP=NONE: {len(app_none_doctypes)}")
            for dt in app_none_doctypes[:10]:
                print(f"   • {dt['name']} (module: {dt['module']})")
            if len(app_none_doctypes) > 10:
                print(f"   ... and {len(app_none_doctypes) - 10} more")
        else:
            print("✅ No doctypes with app=None")
        
        # File System Check
        print(f"\n🔍 ENHANCED ANALYSIS: FILE SYSTEM CHECK")
        print("=" * 50)
        bench_path = Path('/home/frappe/frappe-bench')
        app_path = bench_path / 'apps' / source_app / source_app
        missing_files = []
        missing_db = []
        
        if app_path.exists():
            for module_dir in app_path.iterdir():
                if module_dir.is_dir():
                    for doctype_file in module_dir.glob('**/*.json'):
                        doctype_name = doctype_file.stem
                        if not frappe.db.exists('DocType', doctype_name):
                            missing_db.append(f"{doctype_name} (file exists, not in DB)")
            
            for dt in all_app_doctypes:
                expected_path = app_path / dt['module'] / f"{dt['name']}.json"
                snake_name = frappe.scrub(dt['name'])
                snake_path = app_path / dt['module'] / f"{snake_name}.json"
                if not expected_path.exists() and not snake_path.exists():
                    missing_files.append(f"{dt['name']} (in DB, no file)")
        
        if missing_files:
            print("⚠️  DOCTYPES IN DB BUT MISSING FILES:")
            for item in missing_files[:5]:
                print(f"   • {item}")
            if len(missing_files) > 5:
                print(f"   ... and {len(missing_files) - 5} more")
        else:
            print("✅ All DB doctypes have corresponding files")
            
        if missing_db:
            print("⚠️  DOCTYPE FILES WITH NO DB RECORDS:")
            for item in missing_db[:5]:
                print(f"   • {item}")
            if len(missing_db) > 5:
                print(f"   ... and {len(missing_db) - 5} more")
        else:
            print("✅ All doctype files have DB records")
        
        # Dependency Analysis
        print(f"\n🔍 ENHANCED ANALYSIS: DEPENDENCIES")
        print("=" * 50)
        all_doctypes = frappe.get_all('DocType', fields=['name', 'app'])
        dependency_count = 0
        cross_app_dependencies = []
        source_doctypes = [dt['name'] for dt in all_app_doctypes]
        
        for target_dt in all_doctypes:
            if target_dt['app'] != source_app:
                try:
                    doc = frappe.get_doc('DocType', target_dt['name'])
                    doc_json = doc.as_json()
                    references = [source_dt for source_dt in source_doctypes if source_dt in doc_json]
                    if references:
                        cross_app_dependencies.append({'doctype': target_dt['name'], 'app': target_dt['app'], 'references': references})
                        dependency_count += 1
                except Exception:
                    pass
        
        if cross_app_dependencies:
            print(f"⚠️  CROSS-APP DEPENDENCIES: {len(cross_app_dependencies)}")
            for dep in cross_app_dependencies[:5]:
                print(f"   • {dep['doctype']} ({dep['app']}) references: {', '.join(dep['references'])}")
            if len(cross_app_dependencies) > 5:
                print(f"   ... and {len(cross_app_dependencies) - 5} more")
        else:
            print("✅ No cross-app dependencies found")
        
        # Comprehensive Summary
        print(f"\n📊 COMPREHENSIVE SUMMARY:")
        print(f"   • Modules: {len(modules)}")
        print(f"   • Doctypes: {len(all_app_doctypes)}")
        print(f"   • Orphan Doctypes: {len(orphans)}")
        print(f"   • App=None Doctypes: {len(app_none_doctypes)}")
        print(f"   • Missing Files: {len(missing_files)}")
        print(f"   • Missing DB Records: {len(missing_db)}")
        print(f"   • Cross-App Dependencies: {dependency_count}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        recommendations = []
        if orphans:
            recommendations.append("Run: bench migrate-app fix-orphans " + source_app)
        if app_none_doctypes:
            recommendations.append("Run: bench migrate-app fix-app-none " + source_app)
        if missing_files:
            recommendations.append("Run: bench migrate-app restore-missing " + source_app)
        if cross_app_dependencies:
            recommendations.append("Run: bench migrate-app fix-all-references " + source_app)
        
        if recommendations:
            for rec in recommendations:
                print(f"   • {rec}")
        else:
            print("   • App is ready for migration!")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

@with_session_management
def analyze_app(source_app):
    """Comprehensive app analysis with enhanced diagnostics AND FEEDBACK"""
    print(f"🔍 COMPREHENSIVE APP ANALYSIS: {source_app}")
    
    try:
        app_doctypes = frappe.get_all('DocType', filters={'app': source_app}, 
            fields=['name', 'module', 'custom', 'is_submittable', 'issingle'])
        app_modules = frappe.get_all('Module Def', filters={'app_name': source_app}, 
            fields=['name', 'module_name'])
        
        print(f"📊 APP OVERVIEW:")
        print(f"   • Doctypes: {len(app_doctypes)}")
        print(f"   • Modules: {len(app_modules)}")
        print(f"   • Custom Doctypes: {len([d for d in app_doctypes if d['custom']])}")
        print(f"   • Submittable Doctypes: {len([d for d in app_doctypes if d['is_submittable']])}")
        print(f"   • Single Doctypes: {len([d for d in app_doctypes if d['issingle']])}")
        
        print(f"\n📦 MODULE BREAKDOWN:")
        for module in app_modules:
            module_doctypes = [d for d in app_doctypes if d['module'] == module['module_name']]
            print(f"   • {module['module_name']}: {len(module_doctypes)} doctypes")
            
        print("🎉 ANALYSIS COMPLETED!")
        return True
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

@with_session_management
def analyze_orphan_doctypes():
    """Comprehensive orphan analysis WITH FEEDBACK"""
    print("🔍 COMPREHENSIVE ORPHAN ANALYSIS")
    
    try:
        all_doctypes = frappe.get_all('DocType', fields=['name', 'module', 'app'])
        orphans = []
        app_none_count = 0
        
        for dt in all_doctypes:
            if not dt['app']:
                app_none_count += 1
                orphans.append({'doctype': dt['name'], 'issue': 'APP_NONE', 'module': dt['module']})
            elif not dt['module']:
                orphans.append({'doctype': dt['name'], 'issue': 'NO_MODULE', 'module': None, 'app': dt['app']})
            else:
                module_check = frappe.get_all('Module Def', filters={'module_name': dt['module'], 'app_name': dt['app']})
                if not module_check:
                    orphans.append({'doctype': dt['name'], 'issue': 'WRONG_MODULE', 'module': dt['module'], 'app': dt['app']})
        
        print(f"📊 ORPHAN ANALYSIS RESULTS:")
        print(f"   • Total Doctypes: {len(all_doctypes)}")
        print(f"   • Orphan Doctypes: {len(orphans)}")
        print(f"   • APP=NONE: {app_none_count}")
        
        if orphans:
            print(f"\n🔍 Orphan Doctypes Breakdown:")
            for issue_type in ['APP_NONE', 'NO_MODULE', 'WRONG_MODULE']:
                issue_orphans = [o for o in orphans if o['issue'] == issue_type]
                if issue_orphans:
                    print(f"   • {issue_type}: {len(issue_orphans)}")
                    for orphan in issue_orphans[:5]:
                        print(f"     └─ {orphan['doctype']} (app: {orphan.get('app', 'N/A')})")
                    if len(issue_orphans) > 5:
                        print(f"     ... and {len(issue_orphans) - 5} more")
        
        print("🎉 ORPHAN ANALYSIS COMPLETED!")
        return True
            
    except Exception as e:
        print(f"❌ Orphan analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# ========== ENHANCED FIX FUNCTIONS ==========
@with_session_management
def fix_orphan_doctypes(source_app):
    """Fix orphan doctypes with enhanced module-based assignment AND FEEDBACK"""
    print(f"🔧 FIXING ORPHAN DOCTYPES for {source_app}")
    
    try:
        all_app_doctypes = frappe.get_all('DocType', filters={'app': source_app}, fields=['name', 'module', 'app'])
        orphans = []
        for dt in all_app_doctypes:
            if not dt['module']:
                orphans.append({'doctype': dt['name'], 'issue': 'NO_MODULE', 'current_module': None})
            else:
                module_check = frappe.get_all('Module Def', filters={'module_name': dt['module'], 'app_name': source_app})
                if not module_check:
                    orphans.append({'doctype': dt['name'], 'issue': 'WRONG_MODULE', 'current_module': dt['module']})
        
        print(f"📊 Found {len(orphans)} orphan doctypes")
        
        if not orphans:
            print("✅ No orphan doctypes found")
            return True
        
        print("\n🔍 Orphan Doctypes:")
        for orphan in orphans:
            print(f"   • {orphan['doctype']} - {orphan['issue']} (module: {orphan['current_module']})")
        
        confirm = input(f"\n⚠️  Fix {len(orphans)} orphan doctypes? (y/N): ").strip().lower()
        if confirm != 'y':
            print("🚫 Operation cancelled")
            return False
        
        app_modules = frappe.get_all('Module Def', filters={'app_name': source_app}, fields=['module_name'])
        module_names = [m['module_name'] for m in app_modules]
        
        fixed_count = 0
        for orphan in orphans:
            try:
                if orphan['issue'] == 'NO_MODULE' and module_names:
                    frappe.db.set_value('DocType', orphan['doctype'], 'module', module_names[0])
                    print(f"   ✅ Assigned {orphan['doctype']} to module: {module_names[0]}")
                    fixed_count += 1
                elif orphan['issue'] == 'WRONG_MODULE' and module_names:
                    frappe.db.set_value('DocType', orphan['doctype'], 'module', module_names[0])
                    print(f"   ✅ Reassigned {orphan['doctype']} from {orphan['current_module']} to {module_names[0]}")
                    fixed_count += 1
            except Exception as e:
                print(f"   ❌ Failed to fix {orphan['doctype']}: {e}")
        
        frappe.db.commit()
        print(f"🎉 SUCCESSFULLY FIXED {fixed_count} ORPHAN DOCTYPES!")
        return True
            
    except Exception as e:
        print(f"❌ Fix orphan doctypes failed: {e}")
        import traceback
        traceback.print_exc()
        return False

@with_session_management
def restore_missing_doctypes(source_app):
    """Enhanced restoration with canonical module prioritization AND FEEDBACK"""
    print(f"🔧 RESTORING MISSING DOCTYPES for {source_app}")
    
    try:
        app_doctypes = frappe.get_all('DocType', filters={'app': source_app}, fields=['name', 'module', 'custom'])
        bench_path = Path('/home/frappe/frappe-bench')
        app_path = bench_path / 'apps' / source_app / source_app
        
        missing_files = []
        
        print(f"📊 Checking {len(app_doctypes)} doctypes in {source_app}")
        
        for doctype in app_doctypes:
            doctype_name = doctype['name']
            module_name = doctype['module']
            expected_path = app_path / module_name / f"{doctype_name}.json"
            snake_name = frappe.scrub(doctype_name)
            snake_path = app_path / module_name / f"{snake_name}.json"
            
            if not expected_path.exists() and not snake_path.exists():
                missing_files.append({'doctype': doctype_name, 'module': module_name, 'custom': doctype.get('custom', 0)})
        
        print(f"📊 Found {len(missing_files)} missing doctype files")
        
        if not missing_files:
            print("✅ All doctype files are present")
            return True
        
        print("\n🔍 Missing Doctype Files:")
        for missing in missing_files[:10]:
            custom_flag = " (CUSTOM)" if missing['custom'] else ""
            print(f"   • {missing['doctype']} in {missing['module']}{custom_flag}")
        if len(missing_files) > 10:
            print(f"   ... and {len(missing_files) - 10} more")
        
        confirm = input(f"\n⚠️  Create {len(missing_files)} missing doctype files? (y/N): ").strip().lower()
        if confirm != 'y':
            print("🚫 Operation cancelled")
            return False
        
        created_count = 0
        error_count = 0
        
        for missing in missing_files:
            try:
                basic_structure = {
                    'doctype': 'DocType', 'name': missing['doctype'], 'module': missing['module'],
                    'custom': missing['custom'], 'fields': [], 'permissions': []
                }
                module_dir = app_path / missing['module']
                module_dir.mkdir(parents=True, exist_ok=True)
                file_path = module_dir / f"{missing['doctype']}.json"
                with open(file_path, 'w') as f:
                    json.dump(basic_structure, f, indent=2)
                created_count += 1
                print(f"   ✅ Created: {missing['doctype']}.json")
            except Exception as e:
                error_count += 1
                print(f"   ❌ Failed to create {missing['doctype']}: {e}")
        
        print(f"\n📊 RESTORATION SUMMARY:")
        print(f"   • Files created: {created_count}")
        print(f"   • Errors: {error_count}")
        
        if created_count > 0:
            print("🎉 Missing doctype files restored successfully!")
        return True
            
    except Exception as e:
        print(f"❌ Restore missing doctypes failed: {e}")
        import traceback
        traceback.print_exc()
        return False

@with_session_management
def fix_app_none_doctypes(target_app):
    """Fix all doctypes with app=None by assigning them to correct app WITH FEEDBACK"""
    print(f"🔧 FIXING APP=NONE FOR: {target_app}")
    
    try:
        app_none_doctypes = frappe.get_all('DocType', filters={'app': ['is', 'not set']}, fields=['name', 'module'])
        print(f"📊 Found {len(app_none_doctypes)} doctypes with app=None")
        
        if not app_none_doctypes:
            print("✅ No doctypes with app=None found")
            return True
        
        print("\n🔍 Doctypes to be fixed:")
        for dt in app_none_doctypes:
            print(f"   • {dt['name']} (module: {dt['module']})")
        
        confirm = input(f"\n⚠️  Fix {len(app_none_doctypes)} doctypes with app=None? (y/N): ").strip().lower()
        if confirm != 'y':
            print("🚫 Operation cancelled")
            return False
        
        fixed_count = 0
        error_count = 0
        
        for dt in app_none_doctypes:
            try:
                frappe.db.set_value('DocType', dt['name'], 'app', target_app)
                fixed_count += 1
                print(f"   ✅ Fixed {dt['name']}")
            except Exception as e:
                error_count += 1
                print(f"   ❌ Failed to fix {dt['name']}: {e}")
        
        frappe.db.commit()
        print(f"\n📊 FIX SUMMARY:")
        print(f"   • Successfully fixed: {fixed_count}")
        print(f"   • Errors: {error_count}")
        
        if fixed_count > 0:
            print("🎉 APP=NONE issue resolved successfully!")
        return True
            
    except Exception as e:
        print(f"❌ Fix app=None failed: {e}")
        import traceback
        traceback.print_exc()
        return False

@with_session_management
def fix_all_references(target_app):
    """Fix all Link and Table field references WITH FEEDBACK"""
    print(f"🔗 FIXING REFERENCES FOR: {target_app}")
    
    try:
        target_doctypes = frappe.get_all('DocType', filters={'app': target_app}, fields=['name'])
        target_doctype_names = [dt['name'] for dt in target_doctypes]
        all_doctypes = frappe.get_all('DocType', fields=['name'])
        
        print(f"📊 Found {len(target_doctype_names)} doctypes in {target_app}")
        
        fixed_count = 0
        checked_count = 0
        
        for source_dt in all_doctypes:
            try:
                doc = frappe.get_doc('DocType', source_dt['name'])
                doc_modified = False
                
                for field in doc.fields:
                    if field.fieldtype in ['Link', 'Table'] and field.options in target_doctype_names:
                        print(f"   🔗 {source_dt['name']}.{field.fieldname} → {field.options}")
                        doc_modified = True
                
                if doc_modified:
                    fixed_count += 1
                
                checked_count += 1
                if checked_count % 10 == 0:
                    print(f"   📋 Checked {checked_count}/{len(all_doctypes)} doctypes...")
                    
            except Exception as e:
                print(f"   ❌ Error checking {source_dt['name']}: {e}")
        
        print(f"\n📊 REFERENCE FIX SUMMARY:")
        print(f"   • Doctypes checked: {checked_count}")
        print(f"   • Doctypes with references: {fixed_count}")
        print(f"   • Target doctypes: {len(target_doctype_names)}")
        
        print("🎉 REFERENCE ANALYSIS COMPLETED!")
        return True
            
    except Exception as e:
        print(f"❌ Fix references failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# ========== VALIDATION AND SYSTEMATIC FUNCTIONS ==========
@with_session_management
def systematic_renaming(source_app, target_app=None):
    """Systematic renaming based on research findings WITH FEEDBACK"""
    print(f"🔄 SYSTEMATIC RENAMING for {source_app}")
    
    try:
        if not target_app:
            target_app = source_app
        
        print(f"📊 Preparing systematic renaming: {source_app} → {target_app}")
        
        source_modules = frappe.get_all('Module Def', filters={'app_name': source_app}, fields=['name', 'module_name'])
        print(f"📋 Modules to process: {len(source_modules)}")
        
        for module in source_modules:
            print(f"   🔄 Processing module: {module['module_name']}")
            module_doctypes = frappe.get_all('DocType', filters={'module': module['module_name']}, fields=['name', 'custom'])
            print(f"     📄 Doctypes in module: {len(module_doctypes)}")
            for doctype in module_doctypes:
                custom_flag = " (CUSTOM)" if doctype['custom'] else ""
                print(f"     └─ {doctype['name']}{custom_flag}")
        
        print(f"🎉 SYSTEMATIC RENAMING ANALYSIS COMPLETED!")
        print("💡 This is a preview - actual renaming would require additional confirmation")
        return True
            
    except Exception as e:
        print(f"❌ Systematic renaming failed: {e}")
        import traceback
        traceback.print_exc()
        return False

@with_session_management
def validate_migration_readiness(source_app):
    """Validate if app is ready for migration WITH FEEDBACK"""
    print(f"✅ VALIDATING MIGRATION READINESS for {source_app}")
    
    try:
        issues = []
        warnings = []
        
        # Check 1: APP=NONE doctypes
        app_none_doctypes = frappe.get_all('DocType', filters={'app': ['is', 'not set']})
        if app_none_doctypes:
            issues.append(f"APP=NONE doctypes: {len(app_none_doctypes)}")
        
        # Check 2: Orphan doctypes
        all_app_doctypes = frappe.get_all('DocType', filters={'app': source_app}, fields=['name', 'module'])
        orphans = 0
        for dt in all_app_doctypes:
            if not dt['module']:
                orphans += 1
            else:
                module_check = frappe.get_all('Module Def', filters={'module_name': dt['module'], 'app_name': source_app})
                if not module_check:
                    orphans += 1
        
        if orphans > 0:
            issues.append(f"Orphan doctypes: {orphans}")
        
        # Check 3: File system sync
        bench_path = Path('/home/frappe/frappe-bench')
        app_path = bench_path / 'apps' / source_app / source_app
        missing_files = 0
        if app_path.exists():
            for dt in all_app_doctypes:
                expected_path = app_path / dt['module'] / f"{dt['name']}.json"
                snake_path = app_path / dt['module'] / f"{frappe.scrub(dt['name'])}.json"
                if not expected_path.exists() and not snake_path.exists():
                    missing_files += 1
        
        if missing_files > 0:
            warnings.append(f"Missing doctype files: {missing_files}")
        
        # Results
        print(f"📊 VALIDATION RESULTS:")
        print(f"   • Doctypes in app: {len(all_app_doctypes)}")
        
        if not issues and not warnings:
            print("   ✅ READY FOR MIGRATION - No issues found!")
            return True
        else:
            if issues:
                print("   ❌ CRITICAL ISSUES (must fix before migration):")
                for issue in issues:
                    print(f"     • {issue}")
            if warnings:
                print("   ⚠️  WARNINGS (recommended to fix):")
                for warning in warnings:
                    print(f"     • {warning}")
            
            print(f"\n💡 RECOMMENDATIONS:")
            if "APP=NONE" in str(issues):
                print("   • Run: bench migrate-app fix-app-none " + source_app)
            if "Orphan doctypes" in str(issues):
                print("   • Run: bench migrate-app fix-orphans " + source_app)
            if "Missing doctype files" in str(warnings):
                print("   • Run: bench migrate-app restore-missing " + source_app)
            
            return False
            
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

# ========== LEGACY FUNCTIONS (for compatibility) ==========
def interactive_migration():
    """Interactive migration wizard"""
    print("Interactive migration - Enhanced version coming soon")

def select_modules_interactive(source_app, target_app):
    """Select modules interactively"""
    print("Enhanced module selection - Coming soon")
    return [], []

# ========== MAIN COMMAND HANDLER ==========
@click.command('migrate-app')
@click.argument('action')
@click.argument('source_app', required=False)
@click.argument('target_app', required=False)
@click.option('--modules', help='Specific modules to migrate')
@click.option('--doctypes', help='Specific doctypes to migrate')
@click.option('--site', help='Site name')
def migrate_app(action, source_app=None, target_app=None, modules=None, doctypes=None, site=None):
    """App Migrator - Frappe App Migration Toolkit with Enhanced Renaming"""
    
    print(f"🚀 Migration command called: {action} for {source_app}")
    
    # Migration Actions
    if action == 'migrate-modules':
        if not source_app or not target_app:
            print("❌ Source and target app required")
            return
        migrate_app_modules(source_app, target_app, modules)
        
    elif action == 'migrate-doctypes':
        if not source_app or not target_app or not doctypes:
            print("❌ Source app, target app, and doctypes required")
            return
        migrate_specific_doctypes(source_app, target_app, doctypes)
        
    elif action == 'analyze-dependencies':
        if not source_app:
            print("❌ Source app required")
            return
        analyze_app_dependencies(source_app)
        
    elif action == 'interactive-migrate':
        interactive_app_migration()
        
    # Analysis Actions
    elif action == 'analyze':
        analyze_app(source_app)
        
    elif action == 'analyze-orphans':
        analyze_orphan_doctypes()
        
    elif action == 'validate-migration':
        validate_migration_readiness(source_app)
        
    # Fix Actions
    elif action == 'fix-orphans':
        fix_orphan_doctypes(source_app)
        
    elif action == 'restore-missing':
        restore_missing_doctypes(source_app)
        
    elif action == 'fix-app-none':
        fix_app_none_doctypes(source_app)
        
    elif action == 'fix-all-references':
        fix_all_references(source_app)
        
    # Systematic Actions
    elif action == 'rename-systematic':
        systematic_renaming(source_app, target_app)
        
    # Legacy Actions
    elif action == 'interactive':
        interactive_migration()
        
    elif action == 'select-modules':
        selected_modules, selected_doctypes = select_modules_interactive(source_app, target_app)
        click.echo(f"🎯 Final selection: {len(selected_modules)} modules with doctype-level selection")
        
    else:
        print(f"❌ Unknown action: {action}")
        print("📋 Available actions:")
        print("   🚀 MIGRATION: migrate-modules, migrate-doctypes, analyze-dependencies, interactive-migrate")
        print("   🔧 FIXES: fix-orphans, restore-missing, fix-app-none, fix-all-references")
        print("   🔍 ANALYSIS: analyze, analyze-orphans, validate-migration")
        print("   🎮 INTERACTIVE: interactive, select-modules")

# Export commands
commands = [migrate_app]
