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
    """App Migrator - Frappe App Migration Toolkit"""
    
    print(f"Migration command called: {action} for {source_app}")
    
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
        
    else:
        print(f"Unknown action: {action}")
        print("Available actions: analyze, migrate, interactive, select-modules")

def analyze_app(source_app):
    """Analyze a Frappe app for migration readiness - FIXED VERSION"""
    print(f"🎉 SUCCESS! App Migrator is working!")
    print(f"🔍 Analyzing: {source_app}")
    
    try:
        # Get current site and connect properly
        sites = get_sites()
        if not sites:
            print("❌ No sites available for analysis")
            return
            
        site = sites[0]
        click.echo(f"📍 Using site: {site}")
        
        with frappe.init_site(site):
            frappe.connect(site=site)
            
            # Method 1: Count doctypes by app
            doctypes_count = frappe.db.count('DocType', {'app': source_app})
            print(f"📊 Method 1 - Doctypes in app '{source_app}': {doctypes_count}")
            
            # Method 2: Get all doctypes and filter by app
            all_doctypes = frappe.get_all('DocType', fields=['name', 'module', 'app'])
            app_doctypes = [dt for dt in all_doctypes if dt.get('app') == source_app]
            print(f"📊 Method 2 - Doctypes in app '{source_app}': {len(app_doctypes)}")
            
            # Show some sample doctypes
            if app_doctypes:
                print(f"📋 Sample doctypes in {source_app}:")
                for dt in app_doctypes[:5]:
                    print(f"   • {dt['name']} (module: {dt['module']})")
                if len(app_doctypes) > 5:
                    print(f"   • ... and {len(app_doctypes) - 5} more")
            
            # Check for app=None issues
            none_doctypes = [dt for dt in all_doctypes if not dt.get('app') or dt.get('app') == '']
            if none_doctypes:
                print(f"⚠️  Found {len(none_doctypes)} doctypes with app=None")
                print(f"💡 Run: bench migrate-app fix-apps {source_app}")
            
            # Also check modules
            modules = frappe.get_all('Module Def', filters={'app_name': source_app}, fields=['module_name'])
            print(f"🏗️  Modules in {source_app}: {len(modules)}")
            for module in modules[:3]:
                print(f"   • {module['module_name']}")
            
            frappe.destroy()
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"🔍 Debug: {traceback.format_exc()}")
    
    print("✅ Migration Hero Toolkit is alive!")

def interactive_migration():
    """Interactive wizard for migration"""
    sites = get_sites()
    current_site = sites[0] if sites else None
    
    click.echo("🚀 App Migrator - Interactive Mode")
    click.echo("=" * 50)
    
    # Step 1: Site selection
    site = select_site_interactive(current_site)
    if not site:
        return
        
    # Step 2: App selection
    origin_app, target_app = select_apps_interactive(site)
    if not origin_app or not target_app:
        click.echo("❌ App selection failed")
        return
        
    # Step 3: Module selection
    selected_modules, selected_doctypes = select_modules_interactive(origin_app, target_app)
    
    if selected_modules:
        click.echo(f"✅ Migration plan: {len(selected_modules)} modules from {origin_app} → {target_app} on {site}")
    else:
        click.echo("❌ No modules selected - migration cancelled")

def select_site_interactive(default_site):
    """Step 1: Site selection with escape code 0"""
    sites = get_sites()
    
    if not sites:
        click.echo("❌ No sites found!")
        return None
        
    click.echo("\n📋 Available Sites:")
    click.echo("  0. ❌ EXIT")
    for i, site in enumerate(sites, 1):
        marker = " ← CURRENT" if site == default_site else ""
        click.echo(f"  {i}. {site}{marker}")
    
    try:
        choice = click.prompt(f"Select site (0-{len(sites)})", default=1, type=int)
        if choice == 0:
            click.echo("🚫 Operation cancelled by user")
            return None
        selected_site = sites[choice-1] if 1 <= choice <= len(sites) else default_site
        click.echo(f"📍 Selected site: {selected_site}")
        return selected_site
    except Exception as e:
        click.echo(f"❌ Site selection error: {e}")
        return default_site

def select_apps_interactive(site):
    """Step 2: App selection - origin and target with escape code 0 and ALL selection"""
    try:
        with frappe.init_site(site):
            frappe.connect(site=site)
            installed_apps = frappe.get_installed_apps()
            frappe.destroy()
    except Exception as e:
        click.echo(f"❌ Error connecting to site: {e}")
        return None, None
    
    click.echo(f"\n📦 Installed Apps on {site}:")
    click.echo("  0. ❌ EXIT")
    for i, app in enumerate(installed_apps, 1):
        click.echo(f"  {i}. {app}")
    click.echo(f"  {len(installed_apps)+1}. ✅ ALL apps")
    
    try:
        # Select origin app
        origin_choice = click.prompt(f"Select ORIGIN app (0=exit, 1-{len(installed_apps)}=specific, {len(installed_apps)+1}=all)", type=int)
        if origin_choice == 0:
            click.echo("🚫 Operation cancelled by user")
            return None, None
        elif origin_choice == len(installed_apps) + 1:
            origin_app = "ALL"
            click.echo("✅ Selected ALL apps as origin")
        else:
            origin_app = installed_apps[origin_choice-1] if 1 <= origin_choice <= len(installed_apps) else None
        
        # Select target app  
        click.echo(f"\n📦 Target Apps on {site}:")
        click.echo("  0. ↩️ BACK to origin selection")
        for i, app in enumerate(installed_apps, 1):
            click.echo(f"  {i}. {app}")
        click.echo(f"  {len(installed_apps)+1}. ✅ ALL apps")
            
        target_choice = click.prompt(f"Select TARGET app (0=back, 1-{len(installed_apps)}=specific, {len(installed_apps)+1}=all)", type=int)
        if target_choice == 0:
            click.echo("↩️ Returning to origin selection...")
            return select_apps_interactive(site)  # Recursive call to go back
        elif target_choice == len(installed_apps) + 1:
            target_app = "ALL"
            click.echo("✅ Selected ALL apps as target")
        else:
            target_app = installed_apps[target_choice-1] if 1 <= target_choice <= len(installed_apps) else None
        
        click.echo(f"🎯 Origin: {origin_app} → Target: {target_app}")
        return origin_app, target_app
        
    except Exception as e:
        click.echo(f"❌ App selection error: {e}")
        return None, None

def select_modules_interactive(origin_app, target_app):
    """Step 3: Module discovery and selection with escape code 0"""
    click.echo(f"\n🔍 Discovering modules in {origin_app}...")
    
    # Get actual modules from the origin app
    modules = discover_app_modules(origin_app)
    
    if not modules:
        click.echo("❌ No modules with content found in the origin app")
        return [], {}
    
    click.echo("📁 Available Modules:")
    click.echo("  0. ❌ EXIT migration")
    for i, module in enumerate(modules, 1):
        component_types = discover_component_types(origin_app, module)
        doctype_count = count_doctypes_in_module(origin_app, module)
        
        # Enhanced display based on content type
        if doctype_count == "integration" or doctype_count == 0:
            # Show component types for integration modules
            display_text = f"{module} - {', '.join(component_types)}"
        else:
            # Show doctype count + component types for modules with doctypes
            display_text = f"{module} ({doctype_count} doctypes) - {', '.join(component_types)}"
            
        click.echo(f"  {i}. {display_text}")
    
    click.echo(f"  {len(modules)+1}. ✅ ALL modules")
    
    try:
        choices_input = click.prompt("Select modules (0=exit, comma-separated numbers, or 'all')", default="all")
        
        # Check for exit
        if choices_input == '0':
            click.echo("🚫 Migration cancelled by user")
            return [], {}
        
        selected_modules = []
        if choices_input.lower() == 'all' or choices_input == str(len(modules)+1):
            selected_modules = modules
            click.echo("✅ Selected ALL modules")
        else:
            # Parse individual selections
            for choice in choices_input.split(','):
                choice = choice.strip()
                if choice == '0':
                    click.echo("🚫 Migration cancelled by user")
                    return [], {}
                elif choice.isdigit() and 1 <= int(choice) <= len(modules):
                    selected_module = modules[int(choice)-1]
                    selected_modules.append(selected_module)
                    click.echo(f"✅ Selected: {selected_module}")
                else:
                    click.echo(f"⚠️  Invalid selection: {choice}")
            
        # Step 4: Doctype selection for modules that have doctypes
        selected_doctypes = select_doctypes_interactive(origin_app, selected_modules)
        if selected_doctypes is None:  # User exited
            return [], {}
        
        # Display final migration summary
        if not display_migration_summary(origin_app, target_app, selected_modules, selected_doctypes):
            return [], {}  # User cancelled
        
        click.echo(f"🎯 Total modules selected: {len(selected_modules)}")
        return selected_modules, selected_doctypes
        
    except Exception as e:
        click.echo(f"❌ Module selection error: {e}")
        return [], {}

def select_doctypes_interactive(origin_app, selected_modules):
    """Step 4: Doctype selection with escape code 0"""
    if not selected_modules:
        return {}
    
    selected_doctypes = {}
    
    for module in selected_modules:
        doctypes = discover_doctypes_in_module(origin_app, module)
        
        if not doctypes:
            continue  # Skip modules without doctypes
            
        click.echo(f"\n📋 Doctypes in {module}:")
        click.echo("  0. ↩️ BACK to module selection")
        for i, doctype in enumerate(doctypes, 1):
            click.echo(f"  {i}. {doctype}")
        
        click.echo(f"  {len(doctypes)+1}. ✅ ALL doctypes in {module}")
        
        try:
            doctype_choices = click.prompt(f"Select doctypes for {module} (0=back, comma-separated, or 'all')", default="all")
            
            # Check for back
            if doctype_choices == '0':
                click.echo("↩️ Returning to module selection...")
                return None  # Signal to go back
            
            module_doctypes = []
            if doctype_choices.lower() == 'all' or doctype_choices == str(len(doctypes)+1):
                module_doctypes = doctypes
                click.echo(f"✅ Selected ALL {len(doctypes)} doctypes in {module}")
            else:
                for choice in doctype_choices.split(','):
                    choice = choice.strip()
                    if choice == '0':
                        click.echo("↩️ Returning to module selection...")
                        return None  # Signal to go back
                    elif choice.isdigit() and 1 <= int(choice) <= len(doctypes):
                        selected_doctype = doctypes[int(choice)-1]
                        module_doctypes.append(selected_doctype)
                        click.echo(f"✅ Selected: {selected_doctype}")
                    else:
                        click.echo(f"⚠️  Invalid selection: {choice}")
            
            selected_doctypes[module] = {
                'doctypes': module_doctypes,
                'components': {}
            }
            
        except Exception as e:
            click.echo(f"❌ Doctype selection error for {module}: {e}")
            selected_doctypes[module] = {'doctypes': [], 'components': {}}
    
    return selected_doctypes

def display_migration_summary(origin_app, target_app, selected_modules, selected_doctypes):
    """Display comprehensive migration summary with confirmation"""
    click.echo("\n" + "="*60)
    click.echo("🚀 MIGRATION PLAN SUMMARY")
    click.echo("="*60)
    click.echo(f"📤 Origin: {origin_app}")
    click.echo(f"📥 Target: {target_app}")
    click.echo(f"📦 Modules: {len(selected_modules)}")
    
    total_doctypes = 0
    
    for module in selected_modules:
        module_data = selected_doctypes.get(module, {})
        doctypes = module_data.get('doctypes', [])
        
        click.echo(f"\n📁 {module}:")
        if doctypes:
            click.echo(f"   📋 Doctypes: {len(doctypes)} selected")
            for doctype in doctypes[:3]:  # Show first 3 to avoid clutter
                click.echo(f"      • {doctype}")
            if len(doctypes) > 3:
                click.echo(f"      • ... and {len(doctypes) - 3} more")
            total_doctypes += len(doctypes)
        else:
            click.echo("   🔧 Components: All available")
    
    click.echo(f"\n📊 TOTALS:")
    click.echo(f"   • Modules: {len(selected_modules)}")
    click.echo(f"   • Doctypes: {total_doctypes}")
    
    # Ask for confirmation to proceed with escape option
    click.echo(f"\nOptions:")
    click.echo(f"  y - ✅ PROCEED with migration")
    click.echo(f"  n - ❌ CANCEL migration")
    click.echo(f"  0 - ↩️ BACK to module selection")
    
    choice = click.prompt("Select option (y/n/0)", default="y")
    
    if choice.lower() == 'y':
        execute_migration_plan(origin_app, target_app, selected_modules, selected_doctypes)
        return True
    elif choice == '0':
        click.echo("↩️ Returning to module selection...")
        return False
    else:
        click.echo("❌ Migration cancelled by user")
        return False

def execute_migration_plan(origin_app, target_app, selected_modules, selected_doctypes):
    """Execute the migration plan"""
    click.echo("\n🔄 Starting migration execution...")
    
    try:
        # Create target app directory structure if needed
        ensure_target_app_structure(target_app)
        
        total_files_copied = 0
        total_errors = 0
        
        # Process each selected module
        for module in selected_modules:
            module_data = selected_doctypes.get(module, {})
            doctypes = module_data.get('doctypes', [])
            
            click.echo(f"\n📦 Processing module: {module}")
            
            # Copy doctypes
            if doctypes:
                copied, errors = migrate_doctypes(origin_app, target_app, module, doctypes)
                total_files_copied += copied
                total_errors += errors
            else:
                # Copy entire module if no specific doctypes selected
                copied, errors = migrate_entire_module(origin_app, target_app, module)
                total_files_copied += copied
                total_errors += errors
        
        # Update target app configuration
        update_target_app_config(origin_app, target_app, selected_modules)
        
        click.echo(f"\n✅ MIGRATION COMPLETED!")
        click.echo(f"📊 Results:")
        click.echo(f"   • Files copied: {total_files_copied}")
        click.echo(f"   • Errors: {total_errors}")
        click.echo(f"   • Modules migrated: {len(selected_modules)}")
        
        if total_errors == 0:
            click.echo(f"🎉 Successfully migrated from {origin_app} to {target_app}")
            click.echo(f"💡 Remember to run: bench --site [site] install-app {target_app} --force")
        else:
            click.echo(f"⚠️  Migration completed with {total_errors} errors")
            click.echo(f"🔧 Check the logs above for details")
            
    except Exception as e:
        click.echo(f"❌ Migration failed: {e}")
        import traceback
        click.echo(f"🔍 Debug: {traceback.format_exc()}")

def migrate_doctypes(origin_app, target_app, module, doctypes):
    """Migrate specific doctypes from origin to target app"""
    copied = 0
    errors = 0
    
    for doctype in doctypes:
        try:
            click.echo(f"   📋 Migrating doctype: {doctype}")
            
            # Source and target paths
            source_base = f"/home/frappe/frappe-bench/apps/{origin_app}/{origin_app}/{module}/doctype/{doctype}"
            target_base = f"/home/frappe/frappe-bench/apps/{target_app}/{target_app}/{module}/doctype/{doctype}"
            
            # Ensure target directory exists
            os.makedirs(os.path.dirname(target_base), exist_ok=True)
            
            # ✅ FIX: Ensure module has __init__.py file when migrating doctypes
            module_dir = f"/home/frappe/frappe-bench/apps/{target_app}/{target_app}/{module}"
            ensure_module_init_py(module_dir)
            
            # Copy entire doctype directory
            if os.path.exists(source_base):
                if os.path.exists(target_base):
                    shutil.rmtree(target_base)  # Remove existing
                shutil.copytree(source_base, target_base)
                copied += count_files_in_directory(source_base)
                click.echo(f"      ✅ Copied {doctype}")
            else:
                click.echo(f"      ⚠️  Doctype not found: {doctype}")
                errors += 1
                
        except Exception as e:
            click.echo(f"      ❌ Error migrating {doctype}: {e}")
            errors += 1
    
    return copied, errors

def migrate_entire_module(origin_app, target_app, module):
    """Migrate entire module directory"""
    copied = 0
    errors = 0
    
    try:
        click.echo(f"   📦 Migrating entire module: {module}")
        
        source_dir = f"/home/frappe/frappe-bench/apps/{origin_app}/{origin_app}/{module}"
        target_dir = f"/home/frappe/frappe-bench/apps/{target_app}/{target_app}/{module}"
        
        if os.path.exists(source_dir):
            # Ensure target directory exists
            os.makedirs(os.path.dirname(target_dir), exist_ok=True)
            
            # Copy entire module directory
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            shutil.copytree(source_dir, target_dir)
            
            # ✅ FIX: Ensure module has __init__.py file
            ensure_module_init_py(target_dir)
            
            copied = count_files_in_directory(source_dir)
            click.echo(f"      ✅ Copied entire {module} module")
        else:
            click.echo(f"      ⚠️  Module directory not found: {module}")
            errors += 1
            
    except Exception as e:
        click.echo(f"      ❌ Error migrating module {module}: {e}")
        errors += 1
    
    return copied, errors

def ensure_module_init_py(module_path):
    """Ensure every module directory has an __init__.py file"""
    init_file = os.path.join(module_path, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("# Auto-generated by app_migrator\n")
        click.echo(f"      ✅ Created __init__.py for module")
        return True
    return False

def update_target_app_config(origin_app, target_app, selected_modules):
    """Update target app configuration files"""
    try:
        click.echo(f"\n⚙️  Updating {target_app} configuration...")
        
        # Update modules.txt
        modules_path = f"/home/frappe/frappe-bench/apps/{target_app}/{target_app}/modules.txt"
        if os.path.exists(modules_path):
            with open(modules_path, 'r') as f:
                existing_modules = [line.strip() for line in f.readlines() if line.strip()]
            
            # Add new modules
            updated_modules = list(set(existing_modules + selected_modules))
            
            with open(modules_path, 'w') as f:
                f.write("\n".join(updated_modules) + "\n")
            
            click.echo(f"   ✅ Updated modules.txt: {len(updated_modules)} modules")
        else:
            # Create new modules.txt
            with open(modules_path, 'w') as f:
                f.write("\n".join(selected_modules) + "\n")
            click.echo(f"   ✅ Created modules.txt with {len(selected_modules)} modules")
        
        # Ensure all module directories have __init__.py
        for module in selected_modules:
            module_dir = f"/home/frappe/frappe-bench/apps/{target_app}/{target_app}/{module}"
            if os.path.exists(module_dir):
                ensure_module_init_py(module_dir)
        
        click.echo(f"   ✅ Configuration update completed")
            
    except Exception as e:
        click.echo(f"   ❌ Error updating config: {e}")

def count_files_in_directory(directory):
    """Count files in a directory recursively"""
    count = 0
    for root, dirs, files in os.walk(directory):
        count += len(files)
    return count

def ensure_target_app_structure(target_app):
    """Ensure target app has basic Frappe structure"""
    target_path = f"/home/frappe/frappe-bench/apps/{target_app}/{target_app}"
    os.makedirs(target_path, exist_ok=True)
    
    # Create basic __init__.py if it doesn't exist
    init_file = os.path.join(target_path, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write("")

# ===== DISCOVERY FUNCTIONS =====

def discover_app_modules(app_name):
    """Discover actual modules in a Frappe app"""
    try:
        app_path = f"/home/frappe/frappe-bench/apps/{app_name}/{app_name}"
        
        modules = []
        if os.path.exists(app_path):
            for item in os.listdir(app_path):
                item_path = os.path.join(app_path, item)
                if (os.path.isdir(item_path) and not item.startswith('.') and 
                    not item in ['__pycache__', 'patches', 'modules']):
                    
                    # Only include modules that have actual content
                    if has_actual_content(item_path):
                        modules.append(item)
        
        return sorted(modules)
        
    except Exception as e:
        click.echo(f"❌ Error discovering modules in {app_name}: {e}")
        return []

def has_actual_content(directory_path):
    """Check if a directory has actual Frappe content"""
    # Check for non-empty component directories
    component_dirs = ["doctype", "print_format", "workflow", "report", "page", "fixtures"]
    
    for comp_dir in component_dirs:
        comp_path = os.path.join(directory_path, comp_dir)
        if os.path.exists(comp_path) and os.path.isdir(comp_path):
            # Check if directory has content (not just __init__.py)
            items = [item for item in os.listdir(comp_path) 
                    if not item.startswith('.') and not item == '__init__.py']
            if items:
                return True
    
    # Check for Python files that might be modules
    python_files = [f for f in os.listdir(directory_path) 
                   if f.endswith('.py') and not f.startswith('__') and f not in ['hooks.py', '__init__.py']]
    if python_files:
        return True
        
    return False

def count_doctypes_in_module(app_name, module_name):
    """Count doctypes in module"""
    try:
        base_path = f"/home/frappe/frappe-bench/apps/{app_name}/{app_name}/{module_name}/doctype"
        
        if not os.path.exists(base_path):
            return 0
            
        doctype_count = 0
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            
            # Only count directories that have actual doctype content
            if (os.path.isdir(item_path) and not item.startswith('.') and
                not item == '__pycache__'):
                
                # Check if this looks like a real doctype (has JSON files or other content)
                doctype_files = [f for f in os.listdir(item_path) 
                               if not f.startswith('.') and not f == '__init__.py']
                if doctype_files:
                    doctype_count += 1
                    
        return doctype_count
        
    except Exception as e:
        return 0

def discover_component_types(app_name, module_name):
    """Discover what types of components exist in a module"""
    component_types = []
    
    try:
        module_path = f"/home/frappe/frappe-bench/apps/{app_name}/{app_name}/{module_name}"
        
        if not os.path.exists(module_path):
            return []
            
        # Check for different component types
        component_dirs = {
            "doctype": "doctypes", 
            "print_format": "print formats", 
            "workflow": "workflows",
            "report": "reports",
            "page": "pages",
            "fixtures": "fixtures"
        }
        
        for dir_name, display_name in component_dirs.items():
            comp_path = os.path.join(module_path, dir_name)
            if os.path.exists(comp_path) and os.path.isdir(comp_path):
                # Check if directory has actual content
                items = [item for item in os.listdir(comp_path) 
                        if not item.startswith('.') and not item == '__init__.py']
                if items:
                    component_types.append(display_name)
        
        # Check for Python modules
        python_files = [f for f in os.listdir(module_path) 
                       if f.endswith('.py') and not f.startswith('__') and 
                          f not in ['hooks.py', '__init__.py']]
        if python_files:
            component_types.append(f"{len(python_files)} Python modules")
                        
    except Exception as e:
        click.echo(f"⚠️  Error discovering components for {module_name}: {e}")
    
    return component_types if component_types else ["app components"]

def discover_doctypes_in_module(app_name, module_name):
    """Discover actual doctype names in a module"""
    try:
        base_path = f"/home/frappe/frappe-bench/apps/{app_name}/{app_name}/{module_name}/doctype"
        
        if not os.path.exists(base_path):
            return []
            
        doctypes = []
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            
            # Only include directories that have actual doctype content
            if (os.path.isdir(item_path) and not item.startswith('.') and
                not item == '__pycache__'):
                
                # Check if this looks like a real doctype (has JSON files or other content)
                doctype_files = [f for f in os.listdir(item_path) 
                               if not f.startswith('.') and not f == '__init__.py']
                if doctype_files:
                    doctypes.append(item)
                    
        return sorted(doctypes)
        
    except Exception as e:
        return []

# Export commands as a list - Frappe auto-discovers this
commands = [migrate_app]
