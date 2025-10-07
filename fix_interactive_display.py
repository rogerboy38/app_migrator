import re

# Read the current file
with open('app_migrator/commands/__init__.py', 'r') as f:
    content = f.read()

# Find and replace the problematic part in select_doctypes_interactive
old_code = '''        click.echo(f"\\n📋 Doctypes in {module}:")
        click.echo("  0. ↩️ BACK to module selection")
        for i, doctype in enumerate(doctypes, 1):
            click.echo(f"  {i}. {doctype}")'''

new_code = '''        click.echo(f"\\n📋 Doctypes in {module}:")
        click.echo("  0. ↩️ BACK to module selection")
        
        # Build display names: show directory names but indicate if they'll be fixed
        display_names = []
        for doctype in doctypes:
            json_file = f"/home/frappe/frappe-bench/apps/{origin_app}/{origin_app}/{module}/doctype/{doctype}/{doctype}.json"
            if os.path.exists(json_file):
                with open(json_file, 'r') as f:
                    data = json.load(f)
                json_name = data.get('name', doctype)
                
                # Show both names if they differ (naming fix will happen)
                if json_name != doctype:
                    display_names.append(f"{doctype} → {json_name}")
                else:
                    display_names.append(doctype)
            else:
                display_names.append(doctype)
        
        for i, display_name in enumerate(display_names, 1):
            click.echo(f"  {i}. {display_name}")'''

# Replace the code
content = content.replace(old_code, new_code)

# Write back
with open('app_migrator/commands/__init__.py', 'w') as f:
    f.write(content)

print("✅ Fixed interactive display to show directory names")
print("🎯 Now users will see what will actually be migrated")
