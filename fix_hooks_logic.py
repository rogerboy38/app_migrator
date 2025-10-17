"""
Fix for hooks.py handling in enhanced migration engine
"""

import os

def fix_hooks_file(target_app_path, target_app):
    """Completely rewrite hooks.py with proper content"""
    hooks_file = os.path.join(target_app_path, "hooks.py")
    
    proper_hooks_content = f'''from . import __version__ as version

app_name = "{target_app}"
app_title = "{target_app.replace('_', ' ').title()}"
app_publisher = "App Migrator"
app_description = "Migrated app"
app_email = "migration@example.com"
app_license = "MIT"

# Includes in desk
# app_include_js = "/assets/{target_app}/js/app.js"
# app_include_css = "/assets/{target_app}/css/app.css"

# Boot includes
# boot_session = "{target_app}.utils.session.boot_session"
'''
    
    with open(hooks_file, 'w') as f:
        f.write(proper_hooks_content)
    
    print(f"✅ Completely rewrote hooks.py for {target_app}")
    return True

# Test the fix
fix_hooks_file("/home/frappe/frappe-bench-v601/apps/rnd_nutrition_fixed_v4/rnd_nutrition_fixed_v4", "rnd_nutrition_fixed_v4")
