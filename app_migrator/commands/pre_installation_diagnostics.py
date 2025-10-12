#!/usr/bin/env python3
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
    
    # Fix 4: Create requirements.txt if missing
        requirements_file = os.path.join(app_path, "requirements.txt")
        if not os.path.exists(requirements_file):
            with open(requirements_file, 'w') as f:
                f.write("# Add your Python dependencies here\n")
            fixes_applied.append("Created requirements.txt")
    
        return {
            "app_name": app_name,
            "fixes_applied": fixes_applied,
            "total_fixes": len(fixes_applied)
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
            "module_registration": self.check_module_registration(app_path),
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
            "has_init_py": os.path.exists(os.path.join(app_path, "__init__.py")),
            "has_hooks_py": os.path.exists(os.path.join(app_path, "hooks.py")),
            "has_setup_py": os.path.exists(os.path.join(app_path, "setup.py")),
            "has_requirements_txt": os.path.exists(os.path.join(app_path, "requirements.txt")),
            "valid_python_package": self._is_valid_python_package(app_path)
        }
        
        checks["passed_checks"] = sum(checks.values())
        checks["total_checks"] = len(checks) - 1
        checks["structure_score"] = (checks["passed_checks"] / checks["total_checks"]) * 100
        
        return checks
    
    def analyze_hook_files(self, app_path: str) -> Dict[str, Any]:
        """Analyze hook files and conflicts"""
        hook_analysis = {
            "hook_files_found": [],
            "hook_conflicts": [],
            "valid_hooks_py": False,
            "hook_functions": [],
            "version_specific_hooks": []
        }
        
        # Find all hook files
        for root, dirs, files in os.walk(app_path):
            for file in files:
                if file == "hooks.py":
                    hook_path = os.path.join(root, file)
                    hook_analysis["hook_files_found"].append(hook_path)
                    
                    # Analyze hook content
                    hook_content = self._analyze_hook_file(hook_path)
                    if hook_content.get("is_valid"):
                        hook_analysis["valid_hooks_py"] = True
                        hook_analysis["hook_functions"].extend(hook_content.get("functions", []))
        
        return hook_analysis
    
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
                modules_analysis["modules_txt_valid"] = False
                modules_analysis["error"] = str(e)
        
        return modules_analysis
    
    def check_dependencies(self, app_path: str) -> Dict[str, Any]:
        """Check app dependencies"""
        deps_analysis = {
            "requirements_txt_exists": False,
            "dependencies": [],
        }
        
        # Check requirements.txt
        req_path = os.path.join(app_path, "requirements.txt")
        if os.path.exists(req_path):
            deps_analysis["requirements_txt_exists"] = True
            try:
                with open(req_path, 'r') as f:
                    deps_analysis["dependencies"] = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            except Exception as e:
                deps_analysis["error"] = str(e)
        
        return deps_analysis
    
    def diagnose_installation_blockers(self, app_path: str) -> List[str]:
        """Identify specific issues that would block installation"""
        blockers = []
        app_name = os.path.basename(app_path)
        
        # Basic structure checks
        if not os.path.exists(app_path):
            blockers.append(f"App directory does not exist: {app_path}")
            return blockers
        
        if not os.path.exists(os.path.join(app_path, "__init__.py")):
            blockers.append("Missing __init__.py - not a valid Python package")
        
        if not os.path.exists(os.path.join(app_path, "hooks.py")):
            blockers.append("Missing hooks.py - required for Frappe app")
        
        # Module registration
        modules_analysis = self.check_module_registration(app_path)
        if not modules_analysis["modules_txt_exists"]:
            blockers.append("Missing modules.txt - required for app discovery")
        elif not modules_analysis["modules_txt_valid"]:
            blockers.append("modules.txt is empty or invalid")
        
        # Dependencies
        deps_analysis = self.check_dependencies(app_path)
        if not deps_analysis["requirements_txt_exists"]:
            blockers.append("Missing requirements.txt - may cause dependency issues")
        
        return blockers
    
    def _is_valid_python_package(self, app_path: str) -> bool:
        """Check if directory is a valid Python package"""
        init_file = os.path.join(app_path, "__init__.py")
        return os.path.exists(init_file)
    
    def _analyze_hook_file(self, hook_path: str) -> Dict[str, Any]:
        """Analyze content of a hook file"""
        analysis = {
            "path": hook_path,
            "is_valid": False,
            "functions": [],
            "app_name": "",
            "has_get_commands": False
        }
        
        try:
            with open(hook_path, 'r') as f:
                content = f.read()
            
            # Basic validation
            if 'app_name' in content:
                analysis["is_valid"] = True
            
            # Extract function names
            function_pattern = r'def\s+(\w+)\s*\('
            analysis["functions"] = re.findall(function_pattern, content)
            
            # Extract app_name
            app_name_pattern = r'app_name\s*=\s*["\']([^"\']+)["\']'
            app_name_match = re.search(app_name_pattern, content)
            if app_name_match:
                analysis["app_name"] = app_name_match.group(1)
                
        except Exception as e:
            analysis["error"] = str(e)
        
        return analysis
    
    def calculate_health_score(self, analysis: Dict[str, Any]) -> int:
        """Calculate overall health score (0-100)"""
        scores = []
        
        # Structure score (40%)
        structure_score = analysis["structure_validation"].get("structure_score", 0)
        scores.append(structure_score * 0.4)
        
        # Hook score (30%)
        hook_analysis = analysis["hook_analysis"]
        hook_score = 100 if hook_analysis.get("valid_hooks_py") else 30
        scores.append(hook_score * 0.3)
        
        # Module score (20%)
        module_analysis = analysis["module_registration"]
        module_score = 100 if module_analysis.get("modules_txt_valid") else 30
        scores.append(module_score * 0.2)
        
        # Dependency score (10%)
        deps_analysis = analysis["dependency_check"]
        deps_score = 100 if deps_analysis.get("requirements_txt_exists") else 50
        scores.append(deps_score * 0.1)
        
        # Penalty for blockers
        blocker_penalty = len(analysis["installation_blockers"]) * 15
        total_score = sum(scores) - blocker_penalty
        
        return max(0, min(100, int(total_score)))
    
    def generate_fix_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate specific fix recommendations"""
        recommendations = []
        
        # Structure issues
        structure = analysis["structure_validation"]
        if not structure["has_init_py"]:
            recommendations.append("Create __init__.py in app root directory")
        if not structure["has_hooks_py"]:
            recommendations.append("Create hooks.py with app_name definition")
        
        # Module issues
        modules = analysis["module_registration"]
        if not modules["modules_txt_exists"]:
            recommendations.append("Create modules.txt with app module names")
        elif not modules["modules_txt_valid"]:
            recommendations.append("Add module names to modules.txt")
        
        # Dependency issues
        deps = analysis["dependency_check"]
        if not deps["requirements_txt_exists"]:
            recommendations.append("Create requirements.txt (can be empty if no dependencies)")
        
        # Installation blockers
        if analysis["installation_blockers"]:
            recommendations.extend([f"FIX BLOCKER: {blocker}" for blocker in analysis["installation_blockers"]])
        
        return recommendations

# Remove @click.command decorators - handle commands separately
def diagnose_app_function(app_path, fix=False):
    """Diagnose app health without installation"""
    analyzer = PreInstallationAnalyzer()
    
    try:
        analysis = analyzer.analyze_app_health(app_path)
        
        # Display results
        print(f"\n{'='*60}")
        print(f"🩺 APP DIAGNOSIS REPORT: {analysis['app_name']}")
        print(f"{'='*60}")
        print(f"📊 Health Score: {analysis['health_score']}%")
        
        if analysis['installation_blockers']:
            print(f"\n🚫 INSTALLATION BLOCKERS:")
            for blocker in analysis['installation_blockers']:
                print(f"  • {blocker}")
        
        # Auto-fix if requested
        if fix and analysis['installation_blockers']:
            print(f"\n🛠️  Attempting auto-fix...")
            fix_results = analyzer.auto_fix_app_structure(app_path)
            
            print(f"✅ Applied {fix_results['total_fixes']} fixes:")
            for fix_applied in fix_results['fixes_applied']:
                print(f"   • {fix_applied}")
            
            # Re-analyze after fixes
            print(f"\n🔍 Re-analyzing after fixes...")
            updated_analysis = analyzer.analyze_app_health(app_path)
            print(f"📊 Updated Health Score: {updated_analysis['health_score']}%")
            
            return updated_analysis
        
        return analysis
        
    except Exception as e:
        print(f"❌ Diagnosis failed: {str(e)}")


