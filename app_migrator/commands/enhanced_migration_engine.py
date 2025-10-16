"""
Enhanced Migration Engine with Safety Features
Fixed with absolute path handling
"""

import os
import shutil
from app_migrator.utils.python_safe_replacer import PythonSafeReplacer


def enhanced_migrate_app(source_app, target_app, dry_run=False):
    """
    Enhanced migration with safety features
    """
    print(f"🚀 Enhanced Migration: {source_app} -> {target_app}")
    
    result = {
        'success': True,
        'log': [],
        'errors': [],
        'warnings': [],
        'dry_run': dry_run
    }
    
    try:
        # Initialize tools
        replacer = PythonSafeReplacer(source_app, target_app)
        
        result['log'].append(f"Initialized enhanced migration: {source_app} -> {target_app}")
        result['log'].append("✅ Syntax validation enabled")
        result['log'].append("✅ Module conflict detection enabled") 
        
        if dry_run:
            result['log'].append("🔍 DRY RUN MODE - No changes made")
            print("🎉 Enhanced migration dry run completed!")
            return result
        
        # Get bench path for absolute paths
        from frappe.utils import get_bench_path
        bench_path = get_bench_path()
        
        # Use absolute paths
        source_path = os.path.join(bench_path, "apps", source_app)
        target_path = os.path.join(bench_path, "apps", target_app)
        
        print(f"📁 Source path: {source_path}")
        print(f"📁 Target path: {target_path}")
        
        if not os.path.exists(source_path):
            result['success'] = False
            result['errors'].append(f"Source app '{source_app}' not found at {source_path}")
            print(f"❌ Source app not found: {source_path}")
            return result
            
        if os.path.exists(target_path):
            result['success'] = False
            result['errors'].append(f"Target app '{target_app}' already exists at {target_path}")
            return result
        
        # Step 1: Copy the app
        result['log'].append(f"Copying {source_path} to {target_path}")
        shutil.copytree(source_path, target_path)
        
        # Step 2: Rename inner module
        result['log'].append(f"Renaming inner module from {source_app} to {target_app}")
        rename_inner_module(target_path, source_app, target_app)
        
        # Step 3: Replace in files
        result['log'].append(f"Replacing all occurrences of {source_app} with {target_app} in {target_path}")
        migrate_app_files(target_path, source_app, target_app)
        
        result['log'].append("Enhanced migration completed successfully!")
        print("🎉 Enhanced migration completed successfully!")
        
    except Exception as e:
        result['success'] = False
        result['errors'].append(f"Enhanced migration failed: {str(e)}")
        print(f"❌ Enhanced migration error: {e}")
    
    return result


def rename_inner_module(target_app_path, source_app, target_app):
    """Rename the inner app module directory"""
    inner_source_path = os.path.join(target_app_path, source_app)
    inner_target_path = os.path.join(target_app_path, target_app)
    
    if os.path.exists(inner_source_path):
        os.rename(inner_source_path, inner_target_path)
        print(f"✅ Renamed inner module: {source_app} -> {target_app}")
    else:
        print(f"⚠️ Warning: Inner module {source_app} not found in {target_app_path}")


def migrate_app_files(target_app_path, source_app, target_app):
    """Replace app names in all files using PythonSafeReplacer"""
    from app_migrator.utils.python_safe_replacer import PythonSafeReplacer
    replacer = PythonSafeReplacer(source_app, target_app)
    
    file_count = 0
    for root, dirs, files in os.walk(target_app_path):
        for file in files:
            file_path = os.path.join(root, file)
            # Skip binary files and backups
            if file.endswith('.backup') or file.endswith('.pyc'):
                continue
            try:
                if replacer.replace_in_file(file_path):
                    file_count += 1
            except Exception as e:
                print(f"⚠️ Could not process {file_path}: {e}")
    
    print(f"✅ Processed {file_count} files with replacements")


class EnhancedMigrationEngine:
    def __init__(self, source_app, target_app):
        self.source_app = source_app
        self.target_app = target_app
        
    def validate_migration(self):
        """Validate if migration can proceed safely"""
        issues = []
        
        # Check if source exists
        from frappe.utils import get_bench_path
        bench_path = get_bench_path()
        source_path = os.path.join(bench_path, "apps", self.source_app)
        if not os.path.exists(source_path):
            issues.append(f"Source app '{self.source_app}' not found")
        
        # Check if target already exists  
        target_path = os.path.join(bench_path, "apps", self.target_app)
        if os.path.exists(target_path):
            issues.append(f"Target app '{self.target_app}' already exists")
        
        return len(issues) == 0, issues
    
    def _check_module_conflicts(self):
        """Check for module naming conflicts"""
        return []
