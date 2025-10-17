#!/usr/bin/env python3
"""
Migration Manager with Boot Issue Prevention
Integrated boot fixing into the migration process
"""

import os
import sys
from pathlib import Path

# Add boot_fixer to path
sys.path.insert(0, str(Path(__file__).parent))

from boot_fixer import BootFixer

class MigrationManager:
    def __init__(self, bench_path):
        self.bench_path = Path(bench_path)
        self.boot_fixer = BootFixer(bench_path)
        
    def pre_migration_checks(self):
        """Run pre-migration checks and fixes"""
        print("🔍 Running pre-migration checks...")
        
        # Check for boot issues
        issues = self.boot_fixer.diagnose_boot_issues()
        if issues:
            print("❌ Found boot issues that need fixing before migration:")
            for issue in issues:
                print(f"   - {issue}")
            
            # Auto-fix boot issues
            print("🔧 Auto-fixing boot issues...")
            fixes = self.boot_fixer.fix_boot_issues(issues)
            
            if fixes:
                print("✅ Fixed boot issues:")
                for fix in fixes:
                    print(f"   - {fix}")
            else:
                print("⚠️  Could not auto-fix all issues, manual intervention may be needed")
                return False
        else:
            print("✅ No boot issues found - ready for migration")
        
        return True
    
    def post_migration_cleanup(self, migrated_apps):
        """Run post-migration cleanup"""
        print("🧹 Running post-migration cleanup...")
        
        # Remove any .pth files for old app versions
        self.cleanup_old_pth_files(migrated_apps)
        
        # Clean up site configurations
        self.cleanup_site_configs(migrated_apps)
        
        print("✅ Post-migration cleanup completed")
    
    def cleanup_old_pth_files(self, migrated_apps):
        """Clean up .pth files for old app versions"""
        env_path = self.bench_path / "env"
        
        if env_path.exists():
            pth_files = list(env_path.glob("**/*.pth"))
            for pth_file in pth_files:
                try:
                    with open(pth_file, 'r') as f:
                        content = f.read()
                    
                    # Check if this .pth file points to an old version of migrated app
                    for app_name in migrated_apps:
                        if app_name in content and not self.is_current_app_version(app_name, content):
                            print(f"   Removing old .pth file: {pth_file.name}")
                            os.remove(pth_file)
                            break
                except:
                    pass
    
    def is_current_app_version(self, app_name, pth_content):
        """Check if .pth file points to current app version"""
        current_app_path = self.bench_path / "apps" / app_name
        return str(current_app_path) in pth_content
    
    def cleanup_site_configs(self, migrated_apps):
        """Clean up site configurations after migration"""
        sites_path = self.bench_path / "sites"
        
        for site_dir in sites_path.iterdir():
            if site_dir.is_dir():
                # Clean apps.txt
                apps_file = site_dir / "apps.txt"
                if apps_file.exists():
                    self.clean_apps_txt_file(apps_file, migrated_apps)
                
                # Clean site_config.json
                site_config = site_dir / "site_config.json"
                if site_config.exists():
                    self.clean_site_config_file(site_config, migrated_apps)
    
    def clean_apps_txt_file(self, apps_file, migrated_apps):
        """Clean apps.txt file"""
        with open(apps_file, 'r') as f:
            lines = f.readlines()
        
        cleaned_lines = []
        for line in lines:
            app_name = line.strip()
            if not self.is_old_app_version(app_name, migrated_apps):
                cleaned_lines.append(line)
        
        with open(apps_file, 'w') as f:
            f.writelines(cleaned_lines)
    
    def clean_site_config_file(self, site_config_file, migrated_apps):
        """Clean site_config.json file"""
        import json
        
        with open(site_config_file, 'r') as f:
            config = json.load(f)
        
        if 'installed_apps' in config:
            config['installed_apps'] = [app for app in config['installed_apps'] 
                                      if not self.is_old_app_version(app, migrated_apps)]
        
        with open(site_config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def is_old_app_version(self, app_name, migrated_apps):
        """Check if app name is an old version of a migrated app"""
        for current_app in migrated_apps:
            if app_name.startswith(current_app.replace('_fixed_v', '_')) and app_name != current_app:
                return True
        return False

def main():
    """Test the migration manager"""
    import sys
    
    if len(sys.argv) > 1:
        bench_path = sys.argv[1]
    else:
        bench_path = os.getcwd()
    
    manager = MigrationManager(bench_path)
    
    if manager.pre_migration_checks():
        print("🎉 Ready for migration!")
    else:
        print("❌ Migration blocked due to boot issues")

if __name__ == "__main__":
    main()
