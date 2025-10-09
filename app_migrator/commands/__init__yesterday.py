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

__version__ = "2.1.0"  # Added Safe Copy Strategy

app_name = "app_migrator"
app_title = "App Migrator"
app_publisher = "Frappe Community"
app_description = "Frappe App Migration Toolkit - SAFE COPY STRATEGY"
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

# ========== SAFE COPY MIGRATION FUNCTIONS ==========
@with_session_management
def migrate_app_modules_copy(source_app, target_app, modules=None):
    """🛡️ SAFE COPY: Copy modules from source to target WITHOUT modifying source"""
    print(f"🛡️ SAFE COPY MODULES: {source_app} → {target_app}")
    print("💡 SOURCE APP WILL REMAIN UNCHANGED")
    
    try:
        # Get source modules (READ ONLY - don't modify source)
        source_modules = frappe.get_all('Module Def', 
            filters={'app_name': source_app},
            fields=['name', 'module_name', 'app_name']
        )
        
        if modules:
            module_list = [m.strip() for m in modules.split(',')]
            source_modules = [m for m in source_modules if m['module_name'] in module_list]
        
        print(f"📦 Found {len(source_modules)} modules in {source_app} to COPY")
        
        if not source_modules:
            print("❌ No modules found to copy")
            return False
        
        # PRE-FLIGHT CHECK: Detect duplicates and issues BEFORE copying
        duplicate_modules = []
        core_modules = []
        safe_to_copy_modules = []
        
        for module in source_modules:
            module_name = module['module_name']
            
            # Check for Core modules (should never be copied)
            if module_name.lower() == 'core':
                core_modules.append(module_name)
                continue
                
            # Check for duplicates
            if frappe.db.exists('Module Def', {'module_name': module_name, 'app_name': target_app}):
                duplicate_modules.append(module_name)
            else:
                safe_to_copy_modules.append(module)
        
        # Show pre-flight analysis
        if duplicate_modules:
            print(f"⚠️  DUPLICATES FOUND ({len(duplicate_modules)} will be skipped): {', '.join(duplicate_modules)}")
        
        if core_modules:
            print(f"🚫 CORE MODULES ({len(core_modules)} will be skipped): {', '.join(core_modules)}")
        
        print(f"✅ SAFE TO COPY: {len(safe_to_copy_modules)} modules")
        
        if not safe_to_copy_modules:
            print("🚫 No modules to copy (all are duplicates or Core modules)")
            return False
            
        # Show what will be copied
        if safe_to_copy_modules:
            copy_list = [m['module_name'] for m in safe_to_copy_modules]
            print(f"📋 WILL COPY: {', '.join(copy_list)}")
        
        # IMPORTANT: Confirm this is a COPY operation
        confirm = input(f"⚠️  COPY {len(safe_to_copy_modules)} modules from {source_app} to {target_app}? (y/N): ").strip().lower()
        if confirm != 'y':
            print("🚫 Copy operation cancelled")
            return False
        
        copied_count = 0
        skipped_count = len(duplicate_modules) + len(core_modules)
        
        # COPY ONLY safe modules
        for module in safe_to_copy_modules:
            try:
                # COPY BEHAVIOR: Create new modules in target app
                new_module = frappe.get_doc({
                    'doctype': 'Module Def',
                    'module_name': module['module_name'],
                    'app_name': target_app
                })
                new_module.insert(ignore_permissions=True)
                print(f"   ✅ COPIED module: {module['module_name']} to {target_app}")
                copied_count += 1
                    
            except Exception as e:
                print(f"   ❌ Failed to copy module '{module['module_name']}': {str(e)[:100]}...")
                skipped_count += 1
        
        frappe.db.commit()
        print(f"🎉 SAFE COPY COMPLETED: {copied_count} copied, {skipped_count} skipped")
        print(f"💡 Source app {source_app} remains UNCHANGED")
        
        # Copy module files (safe copy) - only for successfully copied modules
        successful_modules = [m['module_name'] for m in safe_to_copy_modules if frappe.db.exists('Module Def', {'module_name': m['module_name'], 'app_name': target_app})]
        if successful_modules:
            copy_module_files_safe(source_app, target_app, successful_modules)
        else:
            print("💡 No module files to copy")
            
        return copied_count > 0
            
    except Exception as e:
        print(f"❌ Copy migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def copy_module_files_safe(source_app, target_app, modules):
    """🛡️ SAFE COPY: Copy module files without removing from source"""
    print(f"📁 SAFE COPY FILES: {source_app} → {target_app}")
    
    try:
        bench_path = Path('/home/frappe/frappe-bench')
        source_app_path = bench_path / 'apps' / source_app / source_app
        target_app_path = bench_path / 'apps' / target_app / target_app
        
        if not source_app_path.exists():
            print(f"❌ Source app path not found: {source_app_path}")
            return
        
        if not target_app_path.exists():
            print(f"❌ Target app path not found: {target_app_path}")
            return
        
        copied_count = 0
        skipped_count = 0
        
        for module in modules:
            # SKIP Core module files
            if module.lower() == 'core':
                print(f"   🚫 SKIPPED: Core module files should not be copied")
                skipped_count += 1
                continue
                
            module_path = source_app_path / module
            target_module_path = target_app_path / module
            
            if module_path.exists():
                # COPY instead of MOVE
                if target_module_path.exists():
                    print(f"   ⚠️  Target module exists, skipping: {module}")
                    skipped_count += 1
                else:
                    shutil.copytree(str(module_path), str(target_module_path))
                    print(f"   ✅ COPIED {module} files")
                    copied_count += 1
            else:
                print(f"   ⚠️  Module directory not found: {module_path}")
                skipped_count += 1
        
        print(f"🎉 SAFE FILE COPY COMPLETED: {copied_count} copied, {skipped_count} skipped")
        print(f"💡 Source app {source_app} remains UNCHANGED")
        
    except Exception as e:
        print(f"❌ Safe file copy failed: {e}")

@with_session_management
def analyze_safe_copy_compatibility(source_app, target_app):
    """🔍 ANALYZE: Check if apps are compatible for safe copy"""
    print(f"🔍 SAFE COPY COMPATIBILITY: {source_app} → {target_app}")
    
    try:
        source_modules = frappe.get_all('Module Def', 
            filters={'app_name': source_app},
            fields=['module_name']
        )
        
        target_modules = frappe.get_all('Module Def',
            filters={'app_name': target_app}, 
            fields=['module_name']
        )
        
        source_module_names = [m['module_name'] for m in source_modules]
        target_module_names = [m['module_name'] for m in target_modules]
        
        # Find conflicts
        conflicts = set(source_module_names) & set(target_module_names)
        
        # Find Core modules (should never be copied)
        core_modules = [m for m in source_module_names if m.lower() == 'core']
        
        print(f"📊 COMPATIBILITY ANALYSIS:")
        print(f"   • Source modules: {len(source_modules)}")
        print(f"   • Target modules: {len(target_modules)}")
        print(f"   • Module conflicts: {len(conflicts)}")
        print(f"   • Core modules found: {len(core_modules)}")
        
        if conflicts:
            print(f"   ⚠️  CONFLICTS (will be skipped):")
            for conflict in sorted(conflicts):
                print(f"     • {conflict}")
        
        if core_modules:
            print(f"   🚫 CORE MODULES (will be skipped):")
            for core_mod in core_modules:
                print(f"     • {core_mod} - Should not be copied (belongs to Frappe)")
        
        safe_to_copy = len(source_modules) - len(conflicts) - len(core_modules)
        print(f"   ✅ SAFE TO COPY: {safe_to_copy} modules")
        
        return safe_to_copy > 0
        
    except Exception as e:
        print(f"❌ Compatibility analysis failed: {e}")
        return False

# ========== EXISTING FUNCTIONS (keep all your existing functions here) ==========
# ... [ALL YOUR EXISTING FUNCTIONS REMAIN UNCHANGED] ...
# ... [fix_module_app_assignments, fix_doctype_app_assignments, etc.] ...

# ========== ENHANCED COMMAND HANDLER ==========
@click.command('migrate-app')
@click.argument('action')
@click.argument('source_app', required=False)
@click.argument('target_app', required=False)
@click.option('--modules', help='Specific modules to migrate')
@click.option('--doctypes', help='Specific doctypes to migrate')
@click.option('--site', help='Site name')
def migrate_app(action, source_app=None, target_app=None, modules=None, doctypes=None, site=None):
    """App Migrator - Frappe App Migration Toolkit with SAFE COPY Strategy"""
    
    print(f"🚀 Migration command called: {action} for {source_app}")
    
    # NEW SAFE COPY COMMANDS
    if action == 'safe-copy-modules':
        if not source_app or not target_app:
            print("❌ Source and target app required")
            return
        migrate_app_modules_copy(source_app, target_app, modules)
        
    elif action == 'analyze-copy-compatibility':
        if not source_app or not target_app:
            print("❌ Source and target app required")
            return
        analyze_safe_copy_compatibility(source_app, target_app)
    
    # ... [ALL YOUR EXISTING COMMAND HANDLING REMAINS] ...
    elif action == 'ultimate-system-fix':
        if not target_app:
            print("❌ Target app required for system fix")
            return
        run_complete_system_fix(target_app)
        
    elif action == 'fix-module-apps':
        if not target_app:
            print("❌ Target app required")
            return
        fix_module_app_assignments(target_app)
        
    # ... [REST OF YOUR EXISTING COMMAND HANDLER] ...

# Export commands
commands = [migrate_app]
