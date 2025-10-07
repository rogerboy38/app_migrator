import re

# Read the current file
with open('app_migrator/commands/__init__.py', 'r') as f:
    content = f.read()

# Find the migrate_doctypes function and replace it with enhanced version
old_function = '''def migrate_doctypes(origin_app, target_app, module, doctypes):
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
    
    return copied, errors'''

new_function = '''def migrate_doctypes(origin_app, target_app, module, doctypes):
    """Migrate specific doctypes from origin to target app"""
    copied = 0
    errors = 0
    fixes_applied = 0
    
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
                
                # ✅ NEW: Check and fix naming conventions in copied files
                target_json = f"{target_base}/{doctype}.json"
                if os.path.exists(target_json):
                    with open(target_json, 'r') as f:
                        doctype_data = json.load(f)
                    
                    current_name = doctype_data.get('name', '')
                    
                    # Check if naming needs fixing
                    if should_fix_doctype_name(current_name, doctype):
                        correct_name = normalize_doctype_name(doctype)
                        if update_doctype_json_name(target_json, correct_name):
                            click.echo(f"      🔧 Fixed naming: {current_name} → {correct_name}")
                            fixes_applied += 1
                
                copied += count_files_in_directory(source_base)
                click.echo(f"      ✅ Copied {doctype}")
            else:
                click.echo(f"      ⚠️  Doctype not found: {doctype}")
                errors += 1
                
        except Exception as e:
            click.echo(f"      ❌ Error migrating {doctype}: {e}")
            errors += 1
    
    if fixes_applied > 0:
        click.echo(f"      🎯 Applied {fixes_applied} naming fixes")
    
    return copied, errors'''

# Replace the function
content = content.replace(old_function, new_function)

# Write back
with open('app_migrator/commands/__init__.py', 'w') as f:
    f.write(content)

print("✅ Enhanced migrate_doctypes function with naming fixes")
