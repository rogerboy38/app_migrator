"""
Enhanced Migration Engine with Safety Features
Final comprehensive version - Best of both worlds
"""

import os
import shutil
import ast
from pathlib import Path
from app_migrator.utils.python_safe_replacer import PythonSafeReplacer


class EnhancedMigrationEngine:
    """Enhanced migration engine with comprehensive safety features"""
    
    def __init__(self, source_app, target_app):
        self.source_app = source_app
        self.target_app = target_app
        self.bench_path = self._find_bench_path()
        self.source_path = os.path.join(self.bench_path, "apps", source_app)
        self.target_path = os.path.join(self.bench_path, "apps", target_app)
        self.results = {
            'success': False,
            'log': [],
            'errors': [],
            'files_processed': 0,
            'warnings': []
        }
    
    def _find_bench_path(self):
        """Robust bench path detection with multiple fallbacks"""
        # Try frappe's method first (from GitHub version)
        try:
            from frappe.utils import get_bench_path
            bench_path = get_bench_path()
            if os.path.exists(bench_path):
                return bench_path
        except ImportError:
            pass
        
        # Fallback methods (our robust approach)
        possible_paths = [
            os.getcwd(),
            os.path.abspath(os.path.join(os.getcwd(), "..", "..")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),
            os.environ.get('BENCH_PATH', ''),
            '/home/frappe/frappe-bench-v601',
        ]
        
        for path in possible_paths:
            if path and os.path.exists(os.path.join(path, "apps")) and os.path.exists(os.path.join(path, "sites")):
                return path
        
        return os.getcwd()
    
    def log(self, message):
        """Add log message"""
        self.results['log'].append(message)
        print(f"📝 {message}")
    
    def error(self, message):
        """Add error message"""
        self.results['errors'].append(message)
        print(f"❌ {message}")
    
    def warn(self, message):
        """Add warning message"""
        self.results['warnings'].append(message)
        print(f"⚠️ {message}")
    
    def validate_migration(self):
        """Validate if migration can proceed safely (from GitHub)"""
        issues = []
        
        # Check if source exists
        if not os.path.exists(self.source_path):
            issues.append(f"Source app '{self.source_app}' not found at {self.source_path}")
        
        # Check if target already exists  
        if os.path.exists(self.target_path):
            issues.append(f"Target app '{self.target_app}' already exists at {self.target_path}")
        
        return len(issues) == 0, issues
    
    def validate_source(self):
        """Enhanced source validation"""
        self.log(f"🔍 Looking for source app at: {self.source_path}")
        self.log(f"🏠 Using bench path: {self.bench_path}")
        
        if not os.path.exists(self.source_path):
            self.error(f"Source app '{self.source_app}' not found at {self.source_path}")
            apps_dir = os.path.join(self.bench_path, "apps")
            if os.path.exists(apps_dir):
                available_apps = [d for d in os.listdir(apps_dir) 
                                if os.path.isdir(os.path.join(apps_dir, d)) and not d.startswith('.')]
                self.log(f"📁 Available apps: {', '.join(available_apps)}")
            return False
        
        # Check basic structure
        checks = [
            ("app directory", os.path.exists(self.source_path)),
            ("setup.py", os.path.exists(os.path.join(self.source_path, "setup.py"))),
            ("inner module", os.path.exists(os.path.join(self.source_path, self.source_app))),
        ]
        
        all_valid = True
        for check_name, check_result in checks:
            if check_result:
                self.log(f"✅ {check_name}: Found")
            else:
                self.warn(f"⚠️ {check_name}: Missing")
                if check_name == "inner module":
                    all_valid = False
        
        return all_valid
    
    def prepare_target(self, dry_run=False):
        """Prepare target directory"""
        if os.path.exists(self.target_path) and not dry_run:
            self.error(f"Target app '{self.target_app}' already exists at {self.target_path}")
            return False
        
        if dry_run:
            self.log("🔍 DRY RUN - Target would be created")
            return True
        
        return True
    
    def copy_app_structure(self):
        """Copy source app to target"""
        try:
            self.log(f"📋 Copying {self.source_path} to {self.target_path}")
            shutil.copytree(self.source_path, self.target_path)
            return True
        except Exception as e:
            self.error(f"Failed to copy app structure: {e}")
            return False
    
    def rename_inner_module(self):
        """Rename inner module directory (from GitHub)"""
        inner_source_path = os.path.join(self.target_path, self.source_app)
        inner_target_path = os.path.join(self.target_path, self.target_app)
        
        if os.path.exists(inner_source_path):
            self.log(f"🔄 Renaming inner module: {self.source_app} -> {self.target_app}")
            shutil.move(inner_source_path, inner_target_path)
            return True
        else:
            self.warn(f"Inner module {self.source_app} not found, creating standard structure")
            os.makedirs(inner_target_path, exist_ok=True)
            return True
    
    def create_proper_setup_py(self):
        """Create proper setup.py for target app"""
        try:
            self.log("📦 Creating proper setup.py...")
            
            # Delete old setup.py to avoid double replacement
            old_setup_path = os.path.join(self.target_path, "setup.py")
            if os.path.exists(old_setup_path):
                os.remove(old_setup_path)
            
            # Create fresh setup.py
            setup_content = f'''from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\\n")

with open("{self.target_app}/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"').strip("'")
            break

setup(
    name="{self.target_app}",
    version=version,
    description="Migrated from {self.source_app}",
    author="App Migrator",
    author_email="migration@example.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)'''
            
            with open(old_setup_path, "w") as f:
                f.write(setup_content)
            
            self.log(f"✅ Created fresh setup.py for {self.target_app}")
            return True
        except Exception as e:
            self.error(f"Failed to create setup.py: {e}")
            return False
    
    def create_missing_files(self):
        """Create missing essential files"""
        inner_target_path = os.path.join(self.target_path, self.target_app)
        
        # Create __init__.py if missing
        init_file = os.path.join(inner_target_path, "__init__.py")
        if not os.path.exists(init_file):
            self.log("📄 Creating missing __init__.py")
            with open(init_file, "w") as f:
                f.write('__version__ = "1.0.0"\n')
        
        # Create proper hooks.py
        hooks_file = os.path.join(inner_target_path, "hooks.py")
        self.log("📄 Ensuring proper hooks.py content")
        hooks_content = f'''from . import __version__ as version

app_name = "{self.target_app}"
app_title = "{self.target_app.replace('_', ' ').title()}"
app_publisher = "App Migrator"
app_description = "Migrated from {self.source_app}"
app_email = "migration@example.com"
app_license = "MIT"

# Includes in desk
# app_include_js = "/assets/{self.target_app}/js/app.js"
# app_include_css = "/assets/{self.target_app}/css/app.css"

# Boot includes
# boot_session = "{self.target_app}.utils.session.boot_session"
'''
        with open(hooks_file, "w") as f:
            f.write(hooks_content)
        
        # Create modules.txt - CRITICAL FOR FRAPPE
        modules_file = os.path.join(inner_target_path, "modules.txt")
        self.log("📄 Creating/updating modules.txt")
        with open(modules_file, "w") as f:
            f.write(f"{self.target_app}\n")
        
        return True
    
    def update_site_apps_txt(self):
        """Add target app to site's apps.txt - CRITICAL FOR FRAPPE INSTALLATION"""
        try:
            self.log("🏠 Updating site apps.txt...")
            
            sites_dir = os.path.join(self.bench_path, "sites")
            if not os.path.exists(sites_dir):
                self.warn("Sites directory not found, skipping apps.txt update")
                return True
            
            updated_sites = 0
            for site in os.listdir(sites_dir):
                site_path = os.path.join(sites_dir, site)
                if os.path.isdir(site_path):
                    apps_txt_path = os.path.join(site_path, "apps.txt")
                    
                    if os.path.exists(apps_txt_path):
                        with open(apps_txt_path, 'r') as f:
                            apps = [app.strip() for app in f.read().strip().split('\n') if app.strip()]
                        
                        # Remove duplicates and add target app
                        apps = [app for app in apps if app != self.target_app]
                        apps.append(self.target_app)
                        
                        with open(apps_txt_path, 'w') as f:
                            f.write("\n".join(apps) + "\n")
                        self.log(f"✅ Updated {site}/apps.txt with {self.target_app}")
                        updated_sites += 1
                    else:
                        with open(apps_txt_path, 'w') as f:
                            f.write(f"{self.target_app}\n")
                        self.log(f"✅ Created apps.txt for {site} with {self.target_app}")
                        updated_sites += 1
            
            if updated_sites > 0:
                self.log(f"✅ Updated apps.txt in {updated_sites} sites")
            else:
                self.warn("⚠️ No sites found to update apps.txt")
            
            return True
        except Exception as e:
            self.error(f"Failed to update site apps.txt: {e}")
            return False
    
    def migrate_app_files(self):
        """Replace app names in all files (from GitHub)"""
        try:
            self.log("🔄 Replacing occurrences in files...")
            replacer = PythonSafeReplacer(self.source_app, self.target_app)
            
            # Process files (excluding setup.py which we already created fresh)
            processed_count = 0
            skip_dirs = {'.git', '__pycache__', 'node_modules', 'dist', 'build'}
            
            for root, dirs, files in os.walk(self.target_path):
                dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Skip setup.py and binary files
                    if file == "setup.py" or file.endswith(('.pyc', '.backup')):
                        continue
                    
                    # Skip modules.txt to avoid double replacement
                    if file == "modules.txt":
                        continue
                    
                    if replacer.replace_in_file(file_path):
                        processed_count += 1
            
            self.results['files_processed'] = processed_count
            self.log(f"📊 Processed {processed_count} files with replacements")
            return True
        except Exception as e:
            self.error(f"Failed to replace occurrences: {e}")
            return False
    
    def cleanup_nested_directories(self):
        """Clean up any nested directories from original app"""
        self.log("🧹 Cleaning up nested directories...")
        inner_target_path = os.path.join(self.target_path, self.target_app)
        
        nested_dirs_to_clean = [
            os.path.join(inner_target_path, self.source_app),
            os.path.join(self.target_path, "apps", self.source_app),
        ]
        
        cleaned_count = 0
        for nested_dir in nested_dirs_to_clean:
            if os.path.exists(nested_dir):
                self.log(f"🗑️ Removing nested directory: {nested_dir}")
                shutil.rmtree(nested_dir)
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.log(f"🧹 Cleaned {cleaned_count} nested directories")
        
        return True
    
    def migrate(self, dry_run=False):
        """Execute the complete migration process"""
        self.log(f"🚀 ENHANCED MIGRATION: {self.source_app} -> {self.target_app}")
        
        # Use GitHub's validation approach
        is_valid, issues = self.validate_migration()
        if not is_valid:
            for issue in issues:
                self.error(issue)
            return self.results
        
        if dry_run:
            self.log("🔍 DRY RUN COMPLETED - No changes made")
            self.results['success'] = True
            return self.results
        
        # Execution phase
        steps = [
            self.copy_app_structure,
            self.rename_inner_module,
            self.create_proper_setup_py,
            self.create_missing_files,
            self.update_site_apps_txt,
            self.migrate_app_files,
            self.cleanup_nested_directories,
        ]
        
        for step in steps:
            if not step():
                self.error(f"Migration failed at step: {step.__name__}")
                if os.path.exists(self.target_path):
                    shutil.rmtree(self.target_path)
                return self.results
        
        self.log("🎉 Enhanced migration completed successfully!")
        self.results['success'] = True
        return self.results


def enhanced_migrate_app(source_app, target_app, dry_run=False):
    """
    Enhanced app migration with safety features and proper structure handling
    Returns: dict with success, log, errors keys
    """
    engine = EnhancedMigrationEngine(source_app, target_app)
    return engine.migrate(dry_run=dry_run)


def validate_migration_readiness(source_app):
    """
    Validate if source app is ready for migration
    """
    engine = EnhancedMigrationEngine(source_app, "dummy_target")
    return engine.validate_source()
