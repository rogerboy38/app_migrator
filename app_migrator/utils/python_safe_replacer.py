"""
Python Safe Replacer - Import-Safe Version
"""

import ast
import os
import shutil


class PythonSafeReplacer:
    def __init__(self, source_app, target_app):
        self.source_app = source_app
        self.target_app = target_app
    
    def _validate_python_syntax(self, content, filename):
        """Validate Python syntax without executing"""
        try:
            ast.parse(content, filename=filename)
            return True
        except SyntaxError as e:
            print(f"❌ Syntax error in {filename}: {e.msg} (line {e.lineno})")
            return False
    
    def replace_in_file(self, filepath):
        """Safely replace strings in a Python file"""
        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            return False
        
        try:
            # Read original content
            with open(filepath, 'r') as f:
                original_content = f.read()
            
            # Validate original syntax
            if not self._validate_python_syntax(original_content, filepath):
                print(f"❌ Original file has syntax errors: {filepath}")
                return False
            
            # Perform replacement
            new_content = original_content.replace(self.source_app, self.target_app)
            
            # Validate new syntax
            if not self._validate_python_syntax(new_content, filepath):
                print(f"❌ Replacement would create syntax errors: {filepath}")
                return False
            
            # Create backup and write new content
            backup_path = filepath + '.backup'
            shutil.copy2(filepath, backup_path)
            
            with open(filepath, 'w') as f:
                f.write(new_content)
                
            print(f"✅ Successfully replaced in: {filepath}")
            return True
            
        except Exception as e:
            print(f"❌ Error in file replacement: {e}")
            return False


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
