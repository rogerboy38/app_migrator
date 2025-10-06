import click
import frappe
from frappe.utils import get_sites
import os
import shutil

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
        print(f"Analyzing app: {source_app}")
        # Keep existing analyze functionality
        
    elif action == 'migrate':
        print(f"Migrating app: {source_app}")
        # Keep existing migrate functionality
        
    elif action == 'interactive':
        interactive_migration()
        
    elif action == 'select-modules':
        selected_modules, selected_doctypes = select_modules_interactive(source_app, target_app)
        click.echo(f"🎯 Final selection: {len(selected_modules)} modules with doctype-level selection")
        
    else:
        print(f"Unknown action: {action}")
        print("Available actions: analyze, migrate, interactive, select-modules")

def interactive_migration():
    """Interactive wizard for migration - RPD Requested"""
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
    
    click.echo(f"✅ Migration plan: {len(selected_modules)} modules from {origin_app} → {target_app} on {site}")

def select_site_interactive(default_site):
    """Step 1: Site selection"""
    sites = get_sites()
    
    if not sites:
        click.echo("❌ No sites found!")
        return None
        
    click.echo("\n📋 Available Sites:")
    for i, site in enumerate(sites, 1):
        marker = " ← CURRENT" if site == default_site else ""
        click.echo(f"  {i}. {site}{marker}")
    
    try:
        choice = click.prompt(f"Select site (1-{len(sites)})", default=1, type=int)
        selected_site = sites[choice-1] if 1 <= choice <= len(sites) else default_site
        click.echo(f"📍 Selected site: {selected_site}")
        return selected_site
    except Exception as e:
        click.echo(f"❌ Site selection error: {e}")
        return default_site

def select_apps_interactive(site):
    """Step 2: App selection - origin and target"""
    try:
        with frappe.init_site(site):
            frappe.connect(site=site)
            installed_apps = frappe.get_installed_apps()
            frappe.destroy()
    except Exception as e:
        click.echo(f"❌ Error connecting to site: {e}")
        return None, None
    
    click.echo(f"\n📦 Installed Apps on {site}:")
    for i, app in enumerate(installed_apps, 1):
        click.echo(f"  {i}. {app}")
    
    try:
        # Select origin app
        origin_choice = click.prompt("Select ORIGIN app (number)", type=int)
        origin_app = installed_apps[origin_choice-1] if 1 <= origin_choice <= len(installed_apps) else None
        
        # Select target app  
        target_choice = click.prompt("Select TARGET app (number)", type=int)
        target_app = installed_apps[target_choice-1] if 1 <= target_choice <= len(installed_apps) else None
        
        click.echo(f"🎯 Origin: {origin_app} → Target: {target_app}")
        return origin_app, target_app
        
    except Exception as e:
        click.echo(f"❌ App selection error: {e}")
        return None, None

def select_modules_interactive(origin_app, target_app):
    """Step 3: Module discovery and selection - with final summary"""
    click.echo(f"\n🔍 Discovering modules in {origin_app}...")
    
    # Get actual modules from the origin app
    modules = discover_app_modules(origin_app)
    
    if not modules:
        click.echo("❌ No modules with content found in the origin app")
        return [], {}
    
    click.echo("📁 Available Modules:")
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
    
    click.echo(f"  {len(modules)+1}. ALL modules")
    
    try:
        choices_input = click.prompt("Select modules (comma-separated numbers or 'all')", default="all")
        
        selected_modules = []
        if choices_input.lower() == 'all' or choices_input == str(len(modules)+1):
            selected_modules = modules
            click.echo("✅ Selected ALL modules")
        else:
            # Parse individual selections
            for choice in choices_input.split(','):
                choice = choice.strip()
                if choice.isdigit() and 1 <= int(choice) <= len(modules):
                    selected_module = modules[int(choice)-1]
                    selected_modules.append(selected_module)
                    click.echo(f"✅ Selected: {selected_module}")
                else:
                    click.echo(f"⚠️  Invalid selection: {choice}")
            
        # Step 4: Doctype selection for modules that have doctypes
        selected_doctypes = select_doctypes_interactive(origin_app, selected_modules)
        
        # Display final migration summary
        display_migration_summary(origin_app, target_app, selected_modules, selected_doctypes)
        
        click.echo(f"🎯 Total modules selected: {len(selected_modules)}")
        return selected_modules, selected_doctypes
        
    except Exception as e:
        click.echo(f"❌ Module selection error: {e}")
        return [], {}

def select_doctypes_interactive(origin_app, selected_modules):
    """Step 4: Doctype selection within selected modules - with component type selection"""
    if not selected_modules:
        return {}
    
    selected_doctypes = {}
    
    for module in selected_modules:
        doctypes = discover_doctypes_in_module(origin_app, module)
        
        if not doctypes:
            continue  # Skip modules without doctypes
            
        click.echo(f"\n📋 Doctypes in {module}:")
        for i, doctype in enumerate(doctypes, 1):
            click.echo(f"  {i}. {doctype}")
        
        click.echo(f"  {len(doctypes)+1}. ALL doctypes in {module}")
        
        try:
            doctype_choices = click.prompt(f"Select doctypes for {module} (comma-separated or 'all')", default="all")
            
            module_doctypes = []
            if doctype_choices.lower() == 'all' or doctype_choices == str(len(doctypes)+1):
                module_doctypes = doctypes
                click.echo(f"✅ Selected ALL {len(doctypes)} doctypes in {module}")
            else:
                for choice in doctype_choices.split(','):
                    choice = choice.strip()
                    if choice.isdigit() and 1 <= int(choice) <= len(doctypes):
                        selected_doctype = doctypes[int(choice)-1]
                        module_doctypes.append(selected_doctype)
                        click.echo(f"✅ Selected: {selected_doctype}")
            
            # Step 5: Component type selection for selected doctypes
            selected_components = select_component_types_interactive(origin_app, module, module_doctypes)
            selected_doctypes[module] = {
                'doctypes': module_doctypes,
                'components': selected_components
            }
            
        except Exception as e:
            click.echo(f"❌ Doctype selection error for {module}: {e}")
            selected_doctypes[module] = {'doctypes': [], 'components': {}}
    
    return selected_doctypes

def select_component_types_interactive(origin_app, module_name, selected_doctypes):
    """Step 5: Component type selection for selected doctypes"""
    if not selected_doctypes:
        return {}
    
    available_components = discover_available_component_types(origin_app, module_name)
    
    if not available_components:
        click.echo(f"ℹ️  No additional components found in {module_name}")
        return {}
    
    selected_components = {}
    
    click.echo(f"\n🔧 Available Component Types in {module_name}:")
    for i, comp_type in enumerate(available_components, 1):
        comp_count = count_components_by_type(origin_app, module_name, comp_type)
        click.echo(f"  {i}. {comp_type} ({comp_count} items)")
    
    click.echo(f"  {len(available_components)+1}. ALL component types")
    
    try:
        comp_choices = click.prompt(f"Select component types for {module_name} (comma-separated or 'all')", default="all")
        
        if comp_choices.lower() == 'all' or comp_choices == str(len(available_components)+1):
            selected_components = {comp_type: "all" for comp_type in available_components}
            click.echo(f"✅ Selected ALL component types in {module_name}")
        else:
            for choice in comp_choices.split(','):
                choice = choice.strip()
                if choice.isdigit() and 1 <= int(choice) <= len(available_components):
                    selected_comp = available_components[int(choice)-1]
                    selected_components[selected_comp] = "all"
                    click.echo(f"✅ Selected: {selected_comp}")
    
    except Exception as e:
        click.echo(f"❌ Component selection error for {module_name}: {e}")
    
    return selected_components

def display_migration_summary(origin_app, target_app, selected_modules, selected_doctypes):
    """Display comprehensive migration summary"""
    click.echo("\n" + "="*60)
    click.echo("🚀 MIGRATION PLAN SUMMARY")
    click.echo("="*60)
    click.echo(f"📤 Origin: {origin_app}")
    click.echo(f"📥 Target: {target_app}")
    click.echo(f"📦 Modules: {len(selected_modules)}")
    
    total_doctypes = 0
    total_components = 0
    
    for module in selected_modules:
        module_data = selected_doctypes.get(module, {})
        doctypes = module_data.get('doctypes', [])
        components = module_data.get('components', {})
        
        click.echo(f"\n📁 {module}:")
        if doctypes:
            click.echo(f"   📋 Doctypes: {len(doctypes)} selected")
            for doctype in doctypes:
                click.echo(f"      • {doctype}")
            total_doctypes += len(doctypes)
        
        if components:
            click.echo(f"   🔧 Components: {len(components)} types")
            for comp_type in components:
                click.echo(f"      • {comp_type}")
            total_components += len(components)
        else:
            click.echo("   🔧 Components: All available")
    
    click.echo(f"\n📊 TOTALS:")
    click.echo(f"   • Modules: {len(selected_modules)}")
    click.echo(f"   • Doctypes: {total_doctypes}")
    click.echo(f"   • Component types: {total_components}")
    
    # Ask for confirmation to proceed
    if click.confirm("\n✅ Proceed with this migration plan?"):
        execute_migration_plan(origin_app, target_app, selected_modules, selected_doctypes)
    else:
        click.echo("❌ Migration cancelled by user")

def execute_migration_plan(origin_app, target_app, selected_modules, selected_doctypes):
    """Execute the migration plan - copy files and update references"""
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
            components = module_data.get('components', {})
            
            click.echo(f"\n📦 Processing module: {module}")
            
            # Copy doctypes
            if doctypes:
                copied, errors = migrate_doctypes(origin_app, target_app, module, doctypes)
                total_files_copied += copied
                total_errors += errors
            
            # Copy components
            if components:
                copied, errors = migrate_components(origin_app, target_app, module, components)
                total_files_copied += copied
                total_errors += errors
            
            # If no specific components selected but module has content, copy entire module
            if not doctypes and not components:
                copied, errors = migrate_entire_module(origin_app, target_app, module)
                total_files_copied += copied
                total_errors += errors
        
        # Update target app hooks and configuration
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

def migrate_components(origin_app, target_app, module, components):
    """Migrate specific component types from origin to target app"""
    copied = 0
    errors = 0
    
    # Map component display names to directory names
    comp_map = {
        "Workflows": "workflow",
        "Reports": "report", 
        "Print Formats": "print_format",
        "Dashboards": "dashboard",
        "Pages": "page",
        "Fixtures": "fixtures"
    }
    
    for comp_display in components:
        comp_dir = comp_map.get(comp_display)
        if not comp_dir:
            continue
            
        try:
            click.echo(f"   🔧 Migrating {comp_display}...")
            
            source_dir = f"/home/frappe/frappe-bench/apps/{origin_app}/{origin_app}/{module}/{comp_dir}"
            target_dir = f"/home/frappe/frappe-bench/apps/{target_app}/{target_app}/{module}/{comp_dir}"
            
            if os.path.exists(source_dir):
                # Ensure target directory exists
                os.makedirs(target_dir, exist_ok=True)
                
                # Copy all files in the component directory
                for item in os.listdir(source_dir):
                    if item.startswith('.') or item == '__init__.py':
                        continue
                        
                    source_path = os.path.join(source_dir, item)
                    target_path = os.path.join(target_dir, item)
                    
                    if os.path.isfile(source_path):
                        shutil.copy2(source_path, target_path)
                        copied += 1
                    elif os.path.isdir(source_path):
                        if os.path.exists(target_path):
                            shutil.rmtree(target_path)
                        shutil.copytree(source_path, target_path)
                        copied += count_files_in_directory(source_path)
                
                click.echo(f"      ✅ Copied {comp_display}")
            else:
                click.echo(f"      ⚠️  {comp_display} directory not found")
                
        except Exception as e:
            click.echo(f"      ❌ Error migrating {comp_display}: {e}")
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
            copied = count_files_in_directory(source_dir)
            click.echo(f"      ✅ Copied entire {module} module")
        else:
            click.echo(f"      ⚠️  Module directory not found: {module}")
            errors += 1
            
    except Exception as e:
        click.echo(f"      ❌ Error migrating module {module}: {e}")
        errors += 1
    
    return copied, errors

def update_target_app_config(origin_app, target_app, selected_modules):
    """Update target app configuration (simplified for now)"""
    try:
        click.echo(f"   ⚙️  Updating target app configuration...")
        
        # For now, just create basic app structure
        target_path = f"/home/frappe/frappe-bench/apps/{target_app}/{target_app}"
        
        # Ensure hooks.py exists
        hooks_file = os.path.join(target_path, "hooks.py")
        if not os.path.exists(hooks_file):
            with open(hooks_file, 'w') as f:
                f.write(f"# Auto-generated by App Migrator\n")
                f.write(f"# Migrated from {origin_app}\n")
                f.write(f"app_name = \"{target_app}\"\n")
                f.write(f"app_title = \"{target_app.title()}\"\n")
                f.write(f"app_publisher = \"App Migrator\"\n")
                f.write(f"app_description = \"Migrated from {origin_app}\"\n")
        
        click.echo(f"      ✅ Updated app configuration")
        
    except Exception as e:
        click.echo(f"      ⚠️  Warning updating config: {e}")

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
    """Discover actual modules in a Frappe app - include main app module"""
    try:
        app_path = f"/home/frappe/frappe-bench/apps/{app_name}/{app_name}"
        
        modules = []
        if os.path.exists(app_path):
            # ALWAYS include the main app module (it might have app-level components)
            if has_app_level_components(app_path):
                modules.append(app_name)
            
            for item in os.listdir(app_path):
                item_path = os.path.join(app_path, item)
                if (os.path.isdir(item_path) and not item.startswith('.') and 
                    not item in ['__pycache__', 'patches', 'modules'] and
                    item != app_name):  # Don't duplicate the main module
                    
                    # Only include modules that have actual content
                    if has_actual_content(item_path):
                        modules.append(item)
        
        return sorted(modules)
        
    except Exception as e:
        click.echo(f"❌ Error discovering modules in {app_name}: {e}")
        return []

def has_app_level_components(app_path):
    """Check if the main app directory has app-level components"""
    # Check for app-level component directories
    component_dirs = ["print_format", "workflow", "report", "page", "public", "templates"]
    
    for comp_dir in component_dirs:
        comp_path = os.path.join(app_path, comp_dir)
        if os.path.exists(comp_path) and os.path.isdir(comp_path):
            items = [item for item in os.listdir(comp_path) 
                    if not item.startswith('.') and not item == '__init__.py']
            if items:
                return True
    
    # Check for important app files
    important_files = ["hooks.py", "boot.py", "modules.txt", "patches.txt"]
    for file_name in important_files:
        if os.path.exists(os.path.join(app_path, file_name)):
            return True
            
    return False

def has_actual_content(directory_path):
    """Check if a directory has actual Frappe content (not just empty structure)"""
    # Check for non-empty component directories
    component_dirs = ["doctype", "print_format", "workflow", "report", "page", "fixtures", "scheduler"]
    
    for comp_dir in component_dirs:
        comp_path = os.path.join(directory_path, comp_dir)
        if os.path.exists(comp_path) and os.path.isdir(comp_path):
            # Check if directory has content (not just __init__.py)
            items = [item for item in os.listdir(comp_path) 
                    if not item.startswith('.') and not item == '__init__.py']
            if items:
                return True
    
    # Check for Python files that might be modules (integration code, business logic)
    python_files = [f for f in os.listdir(directory_path) 
                   if f.endswith('.py') and not f.startswith('__') and f not in ['hooks.py', '__init__.py']]
    if python_files:
        return True
        
    return False

def count_doctypes_in_module(app_name, module_name):
    """Count doctypes in module - return 'integration' for modules without doctypes but with other content"""
    try:
        base_path = f"/home/frappe/frappe-bench/apps/{app_name}/{app_name}/{module_name}/doctype"
        
        if not os.path.exists(base_path):
            # If no doctypes but module has other content, indicate it's integration/business logic
            module_path = f"/home/frappe/frappe-bench/apps/{app_name}/{app_name}/{module_name}"
            if has_actual_content(module_path):
                return "integration"  # Special indicator for modules without doctypes but with other content
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
                    
        return doctype_count if doctype_count > 0 else "integration"
        
    except Exception as e:
        return "integration"

def discover_component_types(app_name, module_name):
    """Discover what types of components exist in a module - comprehensive detection"""
    component_types = []
    
    try:
        if module_name == app_name:
            # Main app module - check app-level components
            module_path = f"/home/frappe/frappe-bench/apps/{app_name}/{app_name}"
        else:
            # Regular module
            module_path = f"/home/frappe/frappe-bench/apps/{app_name}/{app_name}/{module_name}"
        
        if not os.path.exists(module_path):
            return []
            
        # Check for different component types
        component_dirs = {
            "doctype": "doctypes", 
            "print_format": "print formats", 
            "workflow": "workflows",
            "report": "reports",
            "dashboard": "dashboards",
            "page": "pages",
            "fixtures": "fixtures",
            "scheduler": "schedulers",
            "public": "public files",
            "templates": "templates"
        }
        
        for dir_name, display_name in component_dirs.items():
            comp_path = os.path.join(module_path, dir_name)
            if os.path.exists(comp_path) and os.path.isdir(comp_path):
                # Check if directory has actual content
                items = [item for item in os.listdir(comp_path) 
                        if not item.startswith('.') and not item == '__init__.py']
                if items:
                    component_types.append(display_name)
        
        # Check for Python modules (integration code, business logic)
        python_files = [f for f in os.listdir(module_path) 
                       if f.endswith('.py') and not f.startswith('__') and 
                          f not in ['hooks.py', '__init__.py'] and
                          not f.endswith('.pyc')]
        if python_files:
            component_types.append(f"{len(python_files)} Python modules")
            
        # Check for important app files (main module only)
        if module_name == app_name:
            important_files = ["hooks.py", "boot.py", "modules.txt", "patches.txt"]
            for file_name in important_files:
                if os.path.exists(os.path.join(module_path, file_name)):
                    file_size = os.path.getsize(os.path.join(module_path, file_name))
                    if file_size > 100:  # Only count if file has meaningful content
                        component_types.append("app config")
                        break
                        
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

def discover_available_component_types(app_name, module_name):
    """Discover what component types are available in a module"""
    component_types = []
    
    try:
        module_path = f"/home/frappe/frappe-bench/apps/{app_name}/{app_name}/{module_name}"
        
        if not os.path.exists(module_path):
            return []
            
        # Component directories to check
        component_dirs = {
            "workflow": "Workflows",
            "report": "Reports", 
            "print_format": "Print Formats",
            "dashboard": "Dashboards",
            "page": "Pages",
            "fixtures": "Fixtures"
        }
        
        for dir_name, display_name in component_dirs.items():
            comp_path = os.path.join(module_path, dir_name)
            if os.path.exists(comp_path) and os.path.isdir(comp_path):
                items = [item for item in os.listdir(comp_path) 
                        if not item.startswith('.') and not item == '__init__.py']
                if items:
                    component_types.append(display_name)
                    
        return component_types
        
    except Exception as e:
        return []

def count_components_by_type(app_name, module_name, component_type):
    """Count how many items exist for a specific component type"""
    try:
        # Map display names back to directory names
        comp_map = {
            "Workflows": "workflow",
            "Reports": "report",
            "Print Formats": "print_format", 
            "Dashboards": "dashboard",
            "Pages": "page",
            "Fixtures": "fixtures"
        }
        
        dir_name = comp_map.get(component_type)
        if not dir_name:
            return 0
            
        comp_path = f"/home/frappe/frappe-bench/apps/{app_name}/{app_name}/{module_name}/{dir_name}"
        
        if os.path.exists(comp_path):
            items = [item for item in os.listdir(comp_path) 
                    if not item.startswith('.') and not item == '__init__.py']
            return len(items)
            
        return 0
        
    except Exception as e:
        return 0

# Export commands as a list - Frappe auto-discovers this
commands = [migrate_app]
