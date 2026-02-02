"""
Enhanced App Discovery Tool
Finds and validates apps in the bench environment
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Tuple

class AppDiscovery:
    def __init__(self, bench_path: str = None):
        self.bench_path = bench_path or os.getcwd()
        self.apps_path = os.path.join(self.bench_path, "apps")
        
    def discover_installed_apps(self) -> List[Dict]:
        """Discover apps that are installed in the bench"""
        print("🔍 Discovering installed apps...")
        
        apps = []
        
        # Method 1: Check apps directory
        if os.path.exists(self.apps_path):
            for item in os.listdir(self.apps_path):
                app_path = os.path.join(self.apps_path, item)
                if os.path.isdir(app_path) and not item.startswith('.'):
                    apps.append({
                        "name": item,
                        "path": app_path,
                        "type": "directory",
                        "installed": self._check_app_installed(item)
                    })
        
        # Method 2: Check Python packages
        python_apps = self._discover_python_apps()
        for app in python_apps:
            if app["name"] not in [a["name"] for a in apps]:
                apps.append(app)
        
        return apps
    
    def _check_app_installed(self, app_name: str) -> bool:
        """Check if app is installed in current site"""
        try:
            import frappe
            installed_apps = frappe.get_installed_apps()
            return app_name in installed_apps
        except:
            # Fallback: check if module can be imported
            try:
                __import__(app_name)
                return True
            except ImportError:
                return False
    
    def _discover_python_apps(self) -> List[Dict]:
        """Discover apps via Python package discovery"""
        apps = []
        
        try:
            import site
            import sysconfig
            
            # Check all Python paths
            for path in sys.path:
                if os.path.exists(path):
                    for item in os.listdir(path):
                        if (item.endswith('.egg') or 
                            item.endswith('.egg-link') or 
                            os.path.isdir(os.path.join(path, item))):
                            
                            # Try to extract app name
                            app_name = item.replace('.egg', '').replace('.egg-link', '')
                            if not app_name.startswith('_') and app_name not in ['bin', 'lib', 'include']:
                                apps.append({
                                    "name": app_name,
                                    "path": os.path.join(path, item),
                                    "type": "python_package",
                                    "installed": True
                                })
        except Exception as e:
            print(f"⚠️  Error discovering Python apps: {e}")
        
        return apps
    
    def validate_app_structure(self, app_name: str, app_path: str) -> Dict:
        """Validate app structure and requirements"""
        validation = {
            "app_name": app_name,
            "app_path": app_path,
            "valid": True,
            "issues": [],
            "structure": {}
        }
        
        required_files = ["__init__.py", "hooks.py", "modules.txt"]
        required_dirs = ["public", "templates"]
        
        # Check required files
        for file in required_files:
            file_path = os.path.join(app_path, file)
            if os.path.exists(file_path):
                validation["structure"][file] = "✅"
            else:
                validation["structure"][file] = "❌"
                validation["issues"].append(f"Missing {file}")
                validation["valid"] = False
        
        # Check required directories
        for dir in required_dirs:
            dir_path = os.path.join(app_path, dir)
            if os.path.exists(dir_path):
                validation["structure"][dir] = "✅"
            else:
                validation["structure"][dir] = "❌"
                validation["issues"].append(f"Missing {dir}/ directory")
                validation["valid"] = False
        
        # Check inner module (Frappe standard)
        inner_module_path = os.path.join(app_path, app_name)
        if os.path.exists(inner_module_path):
            validation["structure"]["inner_module"] = "✅"
            
            # Check inner module has __init__.py
            inner_init = os.path.join(inner_module_path, "__init__.py")
            if os.path.exists(inner_init):
                validation["structure"]["inner_init"] = "✅"
            else:
                validation["structure"]["inner_init"] = "❌"
                validation["issues"].append(f"Missing {app_name}/__init__.py")
                validation["valid"] = False
        else:
            validation["structure"]["inner_module"] = "❌"
            validation["issues"].append(f"Missing inner module directory: {app_name}/")
            validation["valid"] = False
        
        return validation
    
    def generate_discovery_report(self) -> str:
        """Generate comprehensive app discovery report"""
        apps = self.discover_installed_apps()
        
        report = []
        report.append("📱 APP DISCOVERY REPORT")
        report.append("=" * 50)
        
        for app in apps:
            report.append(f"\n🏷️  App: {app['name']}")
            report.append(f"   📁 Path: {app['path']}")
            report.append(f"   📦 Type: {app['type']}")
            report.append(f"   🔧 Installed: {'✅' if app['installed'] else '❌'}")
            
            # Validate structure if it's a directory app
            if app['type'] == 'directory':
                validation = self.validate_app_structure(app['name'], app['path'])
                report.append(f"   🏗️  Structure: {'✅ Valid' if validation['valid'] else '❌ Invalid'}")
                
                if not validation['valid']:
                    report.append("   ⚠️  Issues:")
                    for issue in validation['issues']:
                        report.append(f"      - {issue}")
        
        return "\n".join(report)

def discover_apps():
    """CLI command to discover apps"""
    discovery = AppDiscovery()
    print(discovery.generate_discovery_report())

if __name__ == "__main__":
    discover_apps()
