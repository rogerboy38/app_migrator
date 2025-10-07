import re

# Read the current file
with open('app_migrator/commands/__init__.py', 'r') as f:
    content = f.read()

# Find the select_doctypes_interactive function and replace it completely
old_function_pattern = r'def select_doctypes_interactive\(origin_app, selected_modules\):.*?return selected_doctypes'
new_function = '''def select_doctypes_interactive(origin_app, selected_modules):
    """Step 4: Doctype selection with escape code 0 - FIXED VERSION"""
    if not selected_modules:
        return {}
    
    selected_doctypes = {}
    
    for module in selected_modules:
        # Get the directory names (what we actually migrate)
        doctypes = discover_doctypes_in_module(origin_app, module)
        
        if not doctypes:
            continue  # Skip modules without doctypes
            
        click.echo(f"\\n📋 Doctypes in {module}:")
        click.echo("  0. ↩️ BACK to module selection")
        
        # Display directory names with their JSON names for clarity
        display_info = []
        for doctype in doctypes:
            json_file = f"/home/frappe/frappe-bench/apps/{origin_app}/{origin_app}/{module}/doctype/{doctype}/{doctype}.json"
            if os.path.exists(json_file):
                with open(json_file, 'r') as f:
                    data = json.load(f)
                json_name = data.get('name', doctype)
                # Show both names if they differ (will be fixed during migration)
                if json_name != doctype:
                    display_info.append(f"{doctype} → {json_name}")
                else:
                    display_info.append(doctype)
            else:
                display_info.append(doctype)
        
        for i, display_text in enumerate(display_info, 1):
            click.echo(f"  {i}. {display_text}")
        
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
                        selected_doctype = doctypes[int(choice)-1]  # Use directory name
                        module_doctypes.append(selected_doctype)
                        click.echo(f"✅ Selected: {selected_doctype}")
                    else:
                        click.echo(f"⚠️  Invalid selection: {choice}")
            
            selected_doctypes[module] = {
                'doctypes': module_doctypes,  # Store directory names for migration
                'components': {}
            }
            
        except Exception as e:
            click.echo(f"❌ Doctype selection error for {module}: {e}")
            selected_doctypes[module] = {'doctypes': [], 'components': {}}
    
    return selected_doctypes'''

# Use regex to replace the function
pattern = r'def select_doctypes_interactive\(origin_app, selected_modules\):.*?return selected_doctypes'
content = re.sub(pattern, new_function, content, flags=re.DOTALL)

# Write back
with open('app_migrator/commands/__init__.py', 'w') as f:
    f.write(content)

print("✅ Fixed interactive doctype selection")
print("🎯 Now shows directory names with JSON names for clarity")
