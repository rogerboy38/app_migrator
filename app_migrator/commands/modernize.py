"""
App Migrator Modernize Commands
Upgrade apps from traditional to modern pyproject.toml structure
"""

import click
import os
import json
from datetime import datetime

try:
    from frappe.commands import pass_context
except ImportError:
    pass_context = lambda f: f


@click.command('app-migrator-modernize')
@click.argument('app_name')
@click.option('--dry-run/--apply', default=True, help='Dry run or apply')
@pass_context
def modernize_app(context, app_name, dry_run):
    """Upgrade app from traditional setup.py to modern pyproject.toml structure"""
    mode = "DRY-RUN" if dry_run else "APPLY"
    print(f"🔄 MODERNIZE APP [{mode}]")
    print(f"   App: {app_name}")
    print("=" * 60)
    
    app_path = os.path.expanduser(f"~/frappe-bench/apps/{app_name}")
    
    if not os.path.exists(app_path):
        print(f"❌ App not found: {app_path}")
        return
    
    pkg_path = os.path.join(app_path, app_name)
    hooks_path = os.path.join(pkg_path, "hooks.py")
    
    # Check current state
    has_pyproject = os.path.exists(os.path.join(app_path, "pyproject.toml"))
    has_setup_py = os.path.exists(os.path.join(app_path, "setup.py"))
    has_hooks = os.path.exists(hooks_path)
    
    print(f"\n📋 CURRENT STATE:")
    print(f"   pyproject.toml: {'✅ Already exists' if has_pyproject else '❌ Missing'}")
    print(f"   setup.py: {'✅ Found' if has_setup_py else '❌ Missing'}")
    print(f"   hooks.py: {'✅ Found' if has_hooks else '❌ Missing'}")
    
    if has_pyproject:
        print(f"\n✅ App already has pyproject.toml - no action needed")
        return
    
    if not has_hooks:
        print(f"\n❌ Cannot modernize - hooks.py not found")
        return
    
    # Read app info from hooks.py
    app_info = {
        "name": app_name,
        "title": app_name.replace("_", " ").title(),
        "description": "Frappe Application",
        "publisher": "Unknown",
        "email": "unknown@example.com",
        "license": "MIT"
    }
    
    with open(hooks_path, 'r') as f:
        hooks_content = f.read()
    
    # Parse hooks.py for app info
    import re
    patterns = {
        "title": r'app_title\s*=\s*["\']([^"\']+)["\']',
        "description": r'app_description\s*=\s*["\']([^"\']+)["\']',
        "publisher": r'app_publisher\s*=\s*["\']([^"\']+)["\']',
        "email": r'app_email\s*=\s*["\']([^"\']+)["\']',
        "license": r'app_license\s*=\s*["\']([^"\']+)["\']',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, hooks_content)
        if match:
            app_info[key] = match.group(1)
    
    # Read version from __init__.py if exists
    init_path = os.path.join(pkg_path, "__init__.py")
    version = "0.0.1"
    if os.path.exists(init_path):
        with open(init_path, 'r') as f:
            init_content = f.read()
        version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', init_content)
        if version_match:
            version = version_match.group(1)
    
    print(f"\n📦 DETECTED APP INFO:")
    print(f"   Name: {app_info['name']}")
    print(f"   Title: {app_info['title']}")
    print(f"   Publisher: {app_info['publisher']}")
    print(f"   Version: {version}")
    
    # Generate pyproject.toml content
    pyproject_content = f'''[project]
name = "{app_name}"
version = "{version}"
description = "{app_info['description']}"
authors = [
    {{ name = "{app_info['publisher']}", email = "{app_info['email']}" }}
]
license = {{ text = "{app_info['license']}" }}
requires-python = ">=3.10"
readme = "README.md"

dependencies = [
    "frappe"
]

[build-system]
requires = ["flit_core>=3.4"]
build-backend = "flit_core.buildapi"

[tool.flit.module]
name = "{app_name}"

[tool.bench.frappe-dependencies]
frappe = ">=15.0.0"
'''

    print(f"\n📄 PYPROJECT.TOML TO CREATE:")
    print("-" * 40)
    for line in pyproject_content.split('\n')[:15]:
        print(f"   {line}")
    print("   ...")
    print("-" * 40)
    
    if not dry_run:
        # Create pyproject.toml
        pyproject_path = os.path.join(app_path, "pyproject.toml")
        with open(pyproject_path, 'w') as f:
            f.write(pyproject_content)
        print(f"\n✅ Created: {pyproject_path}")
        
        # Create README.md if missing
        readme_path = os.path.join(app_path, "README.md")
        if not os.path.exists(readme_path):
            readme_content = f"""# {app_info['title']}

{app_info['description']}

## Installation

```bash
bench get-app {app_name}
bench --site your-site install-app {app_name}
```

## License

{app_info['license']}
"""
            with open(readme_path, 'w') as f:
                f.write(readme_content)
            print(f"✅ Created: {readme_path}")
        
        # Backup and optionally keep setup.py
        if has_setup_py:
            setup_path = os.path.join(app_path, "setup.py")
            backup_path = os.path.join(app_path, "setup.py.bak")
            os.rename(setup_path, backup_path)
            print(f"✅ Backed up: setup.py → setup.py.bak")
        
        print(f"\n🎉 APP MODERNIZED SUCCESSFULLY!")
        print(f"\n📋 NEXT STEPS:")
        print(f"   1. Review pyproject.toml and adjust dependencies")
        print(f"   2. Commit changes:")
        print(f"      cd {app_path}")
        print(f"      git add -A && git commit -m 'Upgrade to pyproject.toml structure'")
        print(f"   3. Reinstall app: bench setup requirements")
    else:
        print(f"\n📋 Run with --apply to create pyproject.toml")


commands = [modernize_app]
