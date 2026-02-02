"""
🩺 PRE-INSTALLATION DIAGNOSTICS TOOL
Analyze app health WITHOUT requiring installation
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any

class PreInstallationAnalyzer:
    """Comprehensive app analysis before installation"""
    
    def __init__(self):
        import os
        self.bench_path = os.getenv('BENCH_PATH', os.path.expanduser('~/frappe-bench'))
        self.checks_performed = []

    def auto_fix_app_structure(self, app_path: str) -> Dict[str, Any]:
        """Automatically fix common app structure issues"""
        fixes_applied = []
        app_name = os.path.basename(app_path)
    
        # Fix 1: Create __init__.py if missing
        init_file = os.path.join(app_path, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write(f'# {app_name} app\n__version__ = "1.0.0"\n')
            fixes_applied.append("Created __init__.py")
    
        # Fix 2: Create hooks.py if missing
        hooks_file = os.path.join(app_path, "hooks.py")
        if not os.path.exists(hooks_file):
            with open(hooks_file, 'w') as f:
                f.write(f'''app_name = "{app_name}"
app_title = "{app_name.title()}"
app_publisher = "Your Name"
app_description = "Description for {app_name}"
app_email = "your.email@example.com"
app_license = "mit"

# Required apps
required_apps = ["frappe"]
''')
            fixes_applied.append("Created hooks.py")
    
        # Fix 3: Create modules.txt if missing
        modules_file = os.path.join(app_path, "modules.txt")
        if not os.path.exists(modules_file):
            with open(modules_file, 'w') as f:
                f.write(f"{app_name.title()}\n")
            fixes_applied.append("Created modules.txt")
    
        return {
            "fixes_applied": fixes_applied,
            "app_name": app_name,
            "app_path": app_path
        }

    def analyze_app_health(self, app_path: str) -> Dict[str, Any]:
        """
        Comprehensive app health analysis without installation
        """
        app_name = os.path.basename(app_path)
        
        print(f"🔍 Analyzing {app_name} at {app_path}...")
        
        analysis = {
            "app_name": app_name,
            "app_path": app_path,
            "exists": os.path.exists(app_path),
            "structure_validation": self.validate_app_structure(app_path),
            "hook_analysis": self.analyze_hook_files(app_path),
            "module_registration": self.enhance_module_registration_check(app_path),
            "dependency_check": self.check_dependencies(app_path),
            "installation_blockers": self.diagnose_installation_blockers(app_path),
            "health_score": 0,
            "fix_recommendations": []
        }
        
        # Calculate health score
        analysis["health_score"] = self.calculate_health_score(analysis)
        analysis["fix_recommendations"] = self.generate_fix_recommendations(analysis)
        
        return analysis
    
    def validate_app_structure(self, app_path: str) -> Dict[str, Any]:
        """Validate basic app structure"""
        checks = {
            "app_directory_exists": os.path.exists(app_path),
            "has_init_file": os.path.exists(os.path.join(app_path, "__init__.py")),
            "has_hooks_file": os.path.exists(os.path.join(app_path, "hooks.py")),
            "has_modules_file": os.path.exists(os.path.join(app_path, "modules.txt")),
            "has_pyproject_toml": os.path.exists(os.path.join(app_path, "pyproject.toml")),
            "has_app_json": os.path.exists(os.path.join(app_path, "app.json")),
        }
        
        return {
            "checks": checks,
            "passed_checks": sum(checks.values()),
            "total_checks": len(checks),
            "structure_score": int((sum(checks.values()) / len(checks)) * 100)
        }

    def analyze_hook_files(self, app_path: str) -> Dict[str, Any]:
        """Analyze hook files for completeness"""
        hooks_analysis = {
            "hooks_file_exists": False,
            "hooks_file_path": "",
            "required_variables": {},
            "hooks_valid": False
        }
        
        hooks_file = os.path.join(app_path, "hooks.py")
        if os.path.exists(hooks_file):
            hooks_analysis["hooks_file_exists"] = True
            hooks_analysis["hooks_file_path"] = hooks_file
            
            # Check for required variables
            try:
                with open(hooks_file, 'r') as f:
                    content = f.read()
                
                required_vars = {
                    "app_name": "app_name" in content,
                    "app_title": "app_title" in content,
                    "app_publisher": "app_publisher" in content,
                    "app_description": "app_description" in content
                }
                
                hooks_analysis["required_variables"] = required_vars
                hooks_analysis["hooks_valid"] = all(required_vars.values())
                
            except Exception as e:
                hooks_analysis["error"] = str(e)
        
        return hooks_analysis

    def check_module_registration(self, app_path: str) -> Dict[str, Any]:
        """Check module registration files"""
        modules_analysis = {
            "modules_txt_exists": False,
            "modules_txt_path": "",
            "modules_list": [],
            "modules_txt_valid": False,
        }
        
        # Check modules.txt
        modules_txt_path = os.path.join(app_path, "modules.txt")
        if os.path.exists(modules_txt_path):
            modules_analysis["modules_txt_exists"] = True
            modules_analysis["modules_txt_path"] = modules_txt_path
            
            try:
                with open(modules_txt_path, 'r') as f:
                    modules = [line.strip() for line in f.readlines() if line.strip()]
                modules_analysis["modules_list"] = modules
                modules_analysis["modules_txt_valid"] = len(modules) > 0
            except Exception as e:
                modules_analysis["error"] = str(e)
        
        return modules_analysis

    def check_dependencies(self, app_path: str) -> Dict[str, Any]:
        """Check app dependencies"""
        dependency_analysis = {
            "dependencies_found": False,
            "dependency_sources": [],
            "dependencies": [],
            "potential_issues": []
        }
        
        # Check requirements.txt
        requirements_path = os.path.join(app_path, "requirements.txt")
        if os.path.exists(requirements_path):
            dependency_analysis["dependency_sources"].append("requirements.txt")
            try:
                with open(requirements_path, 'r') as f:
                    deps = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('#')]
                dependency_analysis["dependencies"].extend(deps)
            except:
                pass
        
        # Check pyproject.toml for dependencies
        pyproject_path = os.path.join(app_path, "pyproject.toml")
        if os.path.exists(pyproject_path):
            dependency_analysis["dependency_sources"].append("pyproject.toml")
        
        dependency_analysis["dependencies_found"] = len(dependency_analysis["dependencies"]) > 0
        
        return dependency_analysis

    def diagnose_installation_blockers(self, app_path: str) -> List[str]:
        """Identify potential installation blockers"""
        blockers = []
        app_name = os.path.basename(app_path)
        
        if not os.path.exists(app_path):
            blockers.append(f"App directory does not exist: {app_path}")
            return blockers
        
        # Check for basic structure
        if not os.path.exists(os.path.join(app_path, "__init__.py")):
            blockers.append("Missing __init__.py file")
        
        if not os.path.exists(os.path.join(app_path, "hooks.py")):
            blockers.append("Missing hooks.py file")
        
        # Check for module registration
        if not os.path.exists(os.path.join(app_path, "modules.txt")):
            blockers.append("Missing modules.txt file")
        
        return blockers

    def calculate_health_score(self, analysis: Dict[str, Any]) -> int:
        """Calculate overall health score (0-100)"""
        score = 0
        
        # Structure validation (30%)
        structure_score = analysis["structure_validation"]["structure_score"]
        score += structure_score * 0.3
        
        # Hook analysis (20%)
        hook_score = 100 if analysis["hook_analysis"]["hooks_valid"] else 0
        score += hook_score * 0.2
        
        # Module registration (20%)
        module_score = 100 if analysis["module_registration"]["modules_txt_valid"] else 0
        score += module_score * 0.2
        
        # Dependencies (15%)
        dep_score = 100 if analysis["dependency_check"]["dependencies_found"] else 50
        score += dep_score * 0.15
        
        # Installation blockers (15%)
        blocker_score = 100 if len(analysis["installation_blockers"]) == 0 else 0
        score += blocker_score * 0.15
        
        return int(score)

    def generate_fix_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations to fix identified issues"""
        recommendations = []
        
        # Structure issues
        structure_checks = analysis["structure_validation"]["checks"]
        if not structure_checks["has_init_file"]:
            recommendations.append("Create __init__.py file")
        if not structure_checks["has_hooks_file"]:
            recommendations.append("Create hooks.py with required variables")
        if not structure_checks["has_modules_file"]:
            recommendations.append("Create modules.txt with module names")
        
        # Hook issues
        if not analysis["hook_analysis"]["hooks_valid"]:
            recommendations.append("Add missing required variables to hooks.py")
        
        # Module issues
        if not analysis["module_registration"]["modules_txt_valid"]:
            recommendations.append("Add module names to modules.txt")
        
        # Installation blockers
        for blocker in analysis["installation_blockers"]:
            recommendations.append(f"Fix: {blocker}")
        
        return recommendations

    # ========== MODERN APP STRUCTURE DETECTION ==========
    
    def detect_modern_app_structure(self, app_path: str) -> Dict[str, Any]:
        """Detect and analyze modern Frappe app structure"""
        analysis = {
            "is_modern_structure": False,
            "has_pyproject_toml": False,
            "has_nested_package": False,
            "detected_modules": [],
            "app_metadata": {}
        }
        
        # Check for modern indicators
        pyproject_path = os.path.join(app_path, "pyproject.toml")
        app_name = os.path.basename(app_path)
        nested_package_path = os.path.join(app_path, app_name)
        
        analysis["has_pyproject_toml"] = os.path.exists(pyproject_path)
        analysis["has_nested_package"] = os.path.exists(nested_package_path) and os.path.exists(os.path.join(nested_package_path, "__init__.py"))
        analysis["is_modern_structure"] = analysis["has_pyproject_toml"] or analysis["has_nested_package"]
        
        if analysis["is_modern_structure"]:
            # Use our modern module detector
            analysis["detected_modules"] = self._detect_python_modules_modern(app_path)
            analysis["app_metadata"] = self._detect_app_metadata_modern(app_path)
        
        return analysis
    
    def _detect_python_modules_modern(self, app_path: str) -> List[str]:
        """Detect Python modules in modern app structure"""
        modules = []
        app_name = os.path.basename(app_path)
        
        # Look for nested directory with same name as app
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
        
        # Also check for traditional modules in root
        for item in os.listdir(app_path):
            item_path = os.path.join(app_path, item)
            if (os.path.isdir(item_path) and 
                os.path.exists(os.path.join(item_path, "__init__.py")) and
                item != app_name):  # Avoid duplicating the nested package
                modules.append(f"{app_name}.{item}")
        
        return list(set(modules))  # Remove duplicates
    
    def _detect_app_metadata_modern(self, app_path: str) -> Dict[str, Any]:
        """Detect app metadata from modern sources"""
        metadata = {}
        
        # Check for pyproject.toml
        pyproject_path = os.path.join(app_path, "pyproject.toml")
        if os.path.exists(pyproject_path):
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

    def enhance_module_registration_check(self, app_path: str) -> Dict[str, Any]:
        """Enhanced module registration that handles modern structures"""
        basic_analysis = self.check_module_registration(app_path)
        modern_analysis = self.detect_modern_app_structure(app_path)
        
        enhanced_analysis = {
            **basic_analysis,
            "modern_structure_detected": modern_analysis["is_modern_structure"],
            "modern_modules_detected": modern_analysis["detected_modules"],
            "total_modules_detected": len(basic_analysis["modules_list"]) + len(modern_analysis["detected_modules"]),
            "app_metadata": modern_analysis["app_metadata"]
        }
        
        return enhanced_analysis
