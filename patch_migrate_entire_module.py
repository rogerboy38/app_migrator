import re

# Read the current file
with open('app_migrator/commands/__init__.py', 'r') as f:
    content = f.read()

# Find the migrate_entire_module function and replace it with enhanced version
old_function = '''def migrate_entire_module(origin_app, target_app, module):
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
    
    return copied, errors'''

new_function = '''def migrate_entire_module(origin_app, target_app, module):
    """Migrate entire module directory"""
    copied = 0
    errors = 0
    fixes_applied = 0
    
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
            
            # ✅ NEW: Check and fix naming conventions for all doctypes in the module
            doctype_path = f"{target_dir}/doctype"
            if os.path.exists(doctype_path):
                for doctype_dir in os.listdir(doctype_path):
                    doctype_dir_path = os.path.join(doctype_path, doctype_dir)
                    if os.path.isdir(doctype_dir_path):
                        doctype_json = os.path.join(doctype_dir_path, f"{doctype_dir}.json")
                        if os.path.exists(doctype_json):
                            with open(doctype_json, 'r') as f:
                                doctype_data = json.load(f)
                            
                            current_name = doctype_data.get('name', '')
                            
                            # Check if naming needs fixing
                            if should_fix_doctype_name(current_name, doctype_dir):
                                correct_name = normalize_doctype_name(doctype_dir)
                                if update_doctype_json_name(doctype_json, correct_name):
                                    click.echo(f"      🔧 Fixed naming: {current_name} → {correct_name}")
                                    fixes_applied += 1
            
            copied = count_files_in_directory(source_dir)
            click.echo(f"      ✅ Copied entire {module} module")
        else:
            click.echo(f"      ⚠️  Module directory not found: {module}")
            errors += 1
            
    except Exception as e:
        click.echo(f"      ❌ Error migrating module {module}: {e}")
        errors += 1
    
    if fixes_applied > 0:
        click.echo(f"      🎯 Applied {fixes_applied} naming fixes in module {module}")
    
    return copied, errors'''

# Replace the function
content = content.replace(old_function, new_function)

# Write back
with open('app_migrator/commands/__init__.py', 'w') as f:
    f.write(content)

print("✅ Enhanced migrate_entire_module function with naming fixes")
