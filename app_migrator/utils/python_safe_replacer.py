# apps/app_migrator/app_migrator/utils/python_safe_replacer.py
"""
Python Safe Replacer - Prevents syntax errors during string replacement
Enhanced with directory traversal
"""

import ast
import os
import shutil
from pathlib import Path


class PythonSafeReplacer:
    def __init__(self, source_app, target_app):
        self.source_app = source_app
        self.target_app = target_app
        self.processed_files = 0
        self.skipped_files = 0
    
    def _validate_python_syntax(self, content, filename):
        """Validate Python syntax without executing"""
        try:
            ast.parse(content, filename=filename)
            return True
        except SyntaxError as e:
            print(f"❌ Syntax error in {filename}:")
            print(f"   {e.msg} (line {e.lineno})")
            if e.text:
                print(f"   Text: {e.text.strip()}")
            return False
    
    def replace_in_file(self, filepath):
        """Safely replace strings in a file"""
        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            return False
        
        try:
            # Read original content
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                original_content = f.read()
            
            # Skip if no replacements needed
            if self.source_app not in original_content:
                return True
            
            # For Python files, validate syntax before and after
            is_python_file = filepath.endswith('.py')
            
            if is_python_file:
                if not self._validate_python_syntax(original_content, filepath):
                    print(f"❌ Original file has syntax errors: {filepath}")
                    return False
            
            # Perform replacement
            new_content = original_content.replace(self.source_app, self.target_app)
            
            # For Python files, validate new syntax
            if is_python_file:
                if not self._validate_python_syntax(new_content, filepath):
                    print(f"❌ Replacement would create syntax errors: {filepath}")
                    return False
            
            # Create backup and write new content
            backup_path = filepath + '.backup'
            shutil.copy2(filepath, backup_path)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"✅ Successfully replaced in: {filepath}")
            self.processed_files += 1
            return True
            
        except UnicodeDecodeError:
            print(f"⚠️ Skipping binary file: {filepath}")
            self.skipped_files += 1
            return False
        except Exception as e:
            print(f"❌ Error processing {filepath}: {e}")
            # Restore backup if it exists
            if 'backup_path' in locals() and os.path.exists(backup_path):
                shutil.copy2(backup_path, filepath)
                os.remove(backup_path)
            self.skipped_files += 1
            return False

    def replace_in_directory(self, directory_path):
        """Replace source_app with target_app in all files in directory"""
        print(f"🔍 Processing directory: {directory_path}")
        
        if not os.path.exists(directory_path):
            print(f"❌ Directory not found: {directory_path}")
            return 0

        # Skip certain directories
        skip_dirs = {'.git', '__pycache__', 'node_modules', 'dist', 'build'}
        
        for root, dirs, files in os.walk(directory_path):
            # Remove skipped directories from traversal
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
            
            for file in files:
                file_path = os.path.join(root, file)
                self.replace_in_file(file_path)

        print(f"✅ Processed {self.processed_files} files, skipped {self.skipped_files} files")
        return self.processed_files


class ModuleRenamer:
    def __init__(self, source_app, target_app):
        self.source_app = source_app
        self.target_app = target_app
    
    def get_module_mapping(self):
        """Get mapping of modules to rename"""
        return {
            self.source_app: self.target_app,
            f"{self.source_app}.modules": f"{self.target_app}.modules",
            f"{self.source_app}.hooks": f"{self.target_app}.hooks",
        }
    
    def rename_modules_file(self, modules_file_path):
        """Rename app in modules.txt file"""
        if not os.path.exists(modules_file_path):
            return False
        
        with open(modules_file_path, 'r') as f:
            content = f.read()
        
        new_content = content.replace(self.source_app, self.target_app)
        
        with open(modules_file_path, 'w') as f:
            f.write(new_content)
        
        return True
