"""
Modern Module Detector for Frappe Apps
Handles both traditional and modern app structures
"""

import os
import ast
from pathlib import Path
from typing import List, Dict, Any

def detect_python_modules(app_path: str) -> List[str]:
    """
    Detect Python modules in Frappe app, handling both traditional and modern structures
    """
    modules = []
    app_name = os.path.basename(app_path)
    
    # Check for traditional structure (hooks.py in root)
    traditional_structure = os.path.exists(os.path.join(app_path, "hooks.py"))
    
    # Check for modern structure (pyproject.toml in root, nested Python package)
    modern_structure = os.path.exists(os.path.join(app_path, "pyproject.toml"))
    
    if traditional_structure:
        # Traditional structure: modules are direct subdirectories with __init__.py
        modules = _find_modules_traditional(app_path, app_name)
    elif modern_structure:
        # Modern structure: look for nested Python package
        modules = _find_modules_modern(app_path, app_name)
    else:
        # Hybrid or unknown structure - try both approaches
        modules = _find_modules_hybrid(app_path, app_name)
    
    return modules

def _find_modules_traditional(app_path: str, app_name: str) -> List[str]:
    """Find modules in traditional Frappe app structure"""
    modules = []
    for item in os.listdir(app_path):
        item_path = os.path.join(app_path, item)
        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, "__init__.py")):
            modules.append(f"{app_name}.{item}")
    return modules

def _find_modules_modern(app_path: str, app_name: str) -> List[str]:
    """Find modules in modern Frappe app structure with nested Python package"""
    modules = []
    
    # Look for nested directory with same name as app (common in modern structure)
    nested_app_path = os.path.join(app_path, app_name)
    if os.path.exists(nested_app_path) and os.path.exists(os.path.join(nested_app_path, "__init__.py")):
        # This is the main package
        modules.append(app_name)
        
        # Find submodules within the nested package
        for root, dirs, files in os.walk(nested_app_path):
            if "__init__.py" in files:
                rel_path = os.path.relpath(root, app_path)
                module_name = rel_path.replace('/', '.')
                if module_name != '.':
                    modules.append(module_name)
    
    return modules

def _find_modules_hybrid(app_path: str, app_name: str) -> List[str]:
    """Find modules in hybrid or unknown structure"""
    modules = []
    
    # Walk through all directories looking for Python packages
    for root, dirs, files in os.walk(app_path):
        if "__init__.py" in files:
            rel_path = os.path.relpath(root, app_path)
            if rel_path == '.':
                modules.append(app_name)
            else:
                module_name = f"{app_name}.{rel_path.replace('/', '.')}"
                modules.append(module_name)
    
    return modules

def detect_app_metadata(app_path: str) -> Dict[str, Any]:
    """Detect app metadata from various sources (app.json, pyproject.toml, hooks.py)"""
    metadata = {}
    
    # Check for traditional app.json
    app_json_path = os.path.join(app_path, "app.json")
    if os.path.exists(app_json_path):
        try:
            with open(app_json_path, 'r') as f:
                import json
                metadata.update(json.load(f))
        except:
            pass
    
    # Check for modern pyproject.toml
    pyproject_path = os.path.join(app_path, "pyproject.toml")
    if os.path.exists(pyproject_path):
        metadata.update(_parse_pyproject_toml(pyproject_path))
    
    # Check for hooks.py
    hooks_path = os.path.join(app_path, "hooks.py")
    if os.path.exists(hooks_path):
        metadata.update(_parse_hooks_py(hooks_path))
    
    return metadata

def _parse_pyproject_toml(pyproject_path: str) -> Dict[str, Any]:
    """Parse pyproject.toml for app metadata"""
    metadata = {}
    try:
        import tomli
        with open(pyproject_path, 'rb') as f:
            data = tomli.load(f)
            
        if 'project' in data:
            project = data['project']
            metadata.update({
                'app_name': project.get('name', ''),
                'app_title': project.get('name', '').title(),
                'app_description': project.get('description', ''),
                'app_publisher': ', '.join([author.get('name', '') for author in project.get('authors', [])]),
                'app_version': '1.0.0',  # pyproject.toml uses dynamic version
                'dependencies': project.get('dependencies', [])
            })
    except ImportError:
        # Fallback: simple string parsing
        with open(pyproject_path, 'r') as f:
            content = f.read()
            if 'name = "' in content:
                import re
                name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
                if name_match:
                    metadata['app_name'] = name_match.group(1)
    except:
        pass
    
    return metadata

def _parse_hooks_py(hooks_path: str) -> Dict[str, Any]:
    """Parse hooks.py for basic app metadata"""
    metadata = {}
    try:
        with open(hooks_path, 'r') as f:
            content = f.read()
            
        # Simple string extraction for common variables
        import re
        patterns = {
            'app_name': r'app_name\s*=\s*["\']([^"\']+)["\']',
            'app_title': r'app_title\s*=\s*["\']([^"\']+)["\']',
            'app_publisher': r'app_publisher\s*=\s*["\']([^"\']+)["\']',
            'app_description': r'app_description\s*=\s*["\']([^"\']+)["\']'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, content)
            if match:
                metadata[key] = match.group(1)
                
    except:
        pass
    
    return metadata

# Test the functions
if __name__ == "__main__":
    test_path = "/home/frappe/frappe-bench-v533/apps/payments"
    if os.path.exists(test_path):
        modules = detect_python_modules(test_path)
        metadata = detect_app_metadata(test_path)
        print(f"Detected modules: {modules}")
        print(f"Detected metadata: {metadata}")
