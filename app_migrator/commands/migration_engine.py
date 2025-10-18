"""
Migration Engine Module - V5.0.0
Merges V4 progress tracking base with V2 core migration functions

Features:
- Core migration functions (migrate modules, doctypes)
- Progress tracking with visual feedback
- File system operations
- Local bench-to-bench migration
- Validation and readiness checks
"""

import frappe
from frappe.utils import get_sites
import os
import subprocess
import time
import shutil
from pathlib import Path
from .session_manager import ensure_frappe_connection, with_session_management


# ========== PROGRESS TRACKING SYSTEM (V4) ==========

class ProgressTracker:
    """Enterprise progress tracking with visual feedback"""
    
    def __init__(self, app_name, total_steps=4):
        self.app_name = app_name
        self.total_steps = total_steps
        self.current_step = 0
        self.steps = [
            "🔍 Validating migration",
            "📥 Downloading app", 
            "⚙️ Installing app",
            "✅ Finalizing"
        ]
        self.start_time = time.time()
    
    def update(self, message=None):
        """Update progress with optional custom message"""
        self.current_step += 1
        elapsed = int(time.time() - self.start_time)
        
        if message:
            print(f"\r🔄 [{self.current_step}/{self.total_steps}] {message} ({elapsed}s)", end="", flush=True)
        else:
            if self.current_step <= len(self.steps):
                print(f"\r🔄 [{self.current_step}/{self.total_steps}] {self.steps[self.current_step-1]} ({elapsed}s)", end="", flush=True)
    
    def complete(self):
        """Mark as completed"""
        elapsed = int(time.time() - self.start_time)
        print(f"\r✅ [{self.total_steps}/{self.total_steps}] {self.app_name} completed! ({elapsed}s)")
    
    def fail(self, error):
        """Mark as failed"""
        elapsed = int(time.time() - self.start_time)
        print(f"\r❌ [{self.current_step}/{self.total_steps}] {self.app_name} failed: {error} ({elapsed}s)")


def run_command_with_progress(command, description, timeout=600):
    """Run command with progress feedback"""
    print(f"🔄 {description}...")
    
    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        start_time = time.time()
        while process.poll() is None:
            if time.time() - start_time > timeout:
                process.terminate()
                return False, f"Timeout after {timeout}s"
            
            elapsed = int(time.time() - start_time)
            print(f"\r⏳ {description}... ({elapsed}s)", end="", flush=True)
            time.sleep(2)
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            print(f"\r✅ {description} completed!")
            return True, stdout
        else:
            print(f"\r❌ {description} failed!")
            return False, stderr
            
    except Exception as e:
        return False, str(e)


def monitor_directory_creation(app_name, timeout=600, check_interval=5):
    """Monitor app directory creation with progress"""
    target_path = f"/home/frappe/frappe-bench/apps/{app_name}"
    print(f"👀 Monitoring directory: {target_path}")
    
    for i in range(timeout // check_interval):
        if os.path.exists(target_path):
            try:
                result = subprocess.run(
                    f"du -sh {target_path}",
                    shell=True, capture_output=True, text=True
                )
                size = result.stdout.strip().split()[0]
            except:
                size = "unknown size"
            print(f"✅ Directory created: {app_name} ({size})")
            return True
        
        dots = "." * (i % 4)
        print(f"\r⏳ Waiting for {app_name} directory{dots} ({i*check_interval}s)", end="", flush=True)
        time.sleep(check_interval)
    
    print(f"\r❌ Timeout: {app_name} directory not created after {timeout}s")
    return False


# ========== VALIDATION FUNCTIONS ==========

def validate_migration_readiness(source_app, target_app):
    """
    Validate migration readiness with comprehensive checks
    Returns: (ready: bool, issues: list)
    """
    print(f"🔍 VALIDATING MIGRATION READINESS: {source_app} → {target_app}")
    print("=" * 70)
    
    issues = []
    
    try:
        if not ensure_frappe_connection():
            issues.append("Cannot establish Frappe connection")
            return False, issues
        
        # Check 1: Source app exists
        source_modules = frappe.get_all('Module Def', filters={'app_name': source_app})
        if not source_modules:
            issues.append(f"Source app '{source_app}' not found or has no modules")
        else:
            print(f"  ✅ Source app has {len(source_modules)} modules")
        
        # Check 2: Target app exists
        target_modules = frappe.get_all('Module Def', filters={'app_name': target_app})
        if not target_modules:
            issues.append(f"Target app '{target_app}' not found")
        else:
            print(f"  ✅ Target app exists with {len(target_modules)} modules")
        
        # Check 3: Check for naming conflicts
        source_doctypes = frappe.get_all('DocType', 
            filters={'app': source_app}, 
            pluck='name'
        )
        target_doctypes = frappe.get_all('DocType', 
            filters={'app': target_app}, 
            pluck='name'
        )
        
        conflicts = set(source_doctypes) & set(target_doctypes)
        if conflicts:
            issues.append(f"{len(conflicts)} DocType naming conflicts found")
            print(f"  ⚠️  {len(conflicts)} naming conflicts")
        else:
            print(f"  ✅ No naming conflicts")
        
        # Check 4: File system paths
        bench_path = Path('/home/frappe/frappe-bench')
        source_path = bench_path / 'apps' / source_app
        target_path = bench_path / 'apps' / target_app
        
        if not source_path.exists():
            issues.append(f"Source app path not found: {source_path}")
        else:
            print(f"  ✅ Source path exists: {source_path}")
        
        if not target_path.exists():
            issues.append(f"Target app path not found: {target_path}")
        else:
            print(f"  ✅ Target path exists: {target_path}")
        
        # Check 5: Disk space
        try:
            result = subprocess.run(
                "df /home/frappe --output=avail | tail -1",
                shell=True, capture_output=True, text=True
            )
            free_space = int(result.stdout.strip()) / 1024 / 1024  # Convert to GB
            if free_space < 2:
                issues.append(f"Low disk space: {free_space:.1f}GB free")
            else:
                print(f"  ✅ Disk space: {free_space:.1f}GB free")
        except:
            print("  ⚠️  Could not check disk space")
        
        # Summary
        print("\n" + "=" * 70)
        if issues:
            print("⚠️  VALIDATION ISSUES FOUND:")
            for issue in issues:
                print(f"  • {issue}")
            return False, issues
        else:
            print("✅ ALL VALIDATION CHECKS PASSED!")
            return True, []
        
    except Exception as e:
        issues.append(f"Validation error: {e}")
        return False, issues


# ========== CORE MIGRATION FUNCTIONS (V2) ==========

@with_session_management
def migrate_app_modules(source_app, target_app, modules=None):
    """
    MIGRATE MODULES FROM SOURCE APP TO TARGET APP - CORE FUNCTIONALITY
    V2-style migration with enhanced feedback
    """
    print(f"🚀 MIGRATING MODULES: {source_app} → {target_app}")
    print("=" * 70)
    
    try:
        # Get source modules
        source_modules = frappe.get_all('Module Def', 
            filters={'app_name': source_app},
            fields=['name', 'module_name', 'app_name']
        )
        
        # Filter specific modules if requested
        if modules:
            if isinstance(modules, str):
                module_list = [m.strip() for m in modules.split(',')]
            else:
                module_list = modules
            source_modules = [m for m in source_modules if m['module_name'] in module_list]
        
        print(f"\n📦 Found {len(source_modules)} modules to migrate\n")
        
        if not source_modules:
            print("❌ No modules found to migrate")
            return False
        
        # Display modules
        for module in source_modules:
            print(f"  • {module['module_name']}")
        
        # Confirm migration
        confirm = input(f"\n⚠️  Migrate {len(source_modules)} modules? (y/N): ").strip().lower()
        if confirm != 'y':
            print("🚫 Migration cancelled")
            return False
        
        # Migrate modules
        migrated_count = 0
        failed_count = 0
        
        for module in source_modules:
            try:
                # Update module app
                frappe.db.set_value('Module Def', module['name'], 'app_name', target_app)
                
                # Get and update all doctypes in module
                module_doctypes = frappe.get_all('DocType',
                    filters={'module': module['module_name']},
                    fields=['name', 'module', 'app']
                )
                
                for doctype in module_doctypes:
                    frappe.db.set_value('DocType', doctype['name'], 'app', target_app)
                
                migrated_count += 1
                print(f"  ✅ Migrated {module['module_name']} ({len(module_doctypes)} doctypes)")
                
            except Exception as e:
                failed_count += 1
                print(f"  ❌ Failed to migrate {module['module_name']}: {e}")
        
        frappe.db.commit()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 MIGRATION SUMMARY")
        print("=" * 70)
        print(f"  ✅ Migrated: {migrated_count}")
        print(f"  ❌ Failed: {failed_count}")
        
        if migrated_count > 0:
            print("\n🎉 MODULE MIGRATION COMPLETED!")
            
            # Optionally move files
            move_files = input("\n💡 Move module files? (y/N): ").strip().lower()
            if move_files == 'y':
                move_module_files(source_app, target_app, [m['module_name'] for m in source_modules])
        
        return migrated_count > 0
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


@with_session_management
def migrate_specific_doctypes(source_app, target_app, doctypes):
    """
    MIGRATE SPECIFIC DOCTYPES BETWEEN APPS
    V2-style doctype migration
    """
    print(f"📄 MIGRATING DOCTYPES: {source_app} → {target_app}")
    print("=" * 70)
    
    try:
        # Parse doctype list
        if isinstance(doctypes, str):
            doctype_list = [d.strip() for d in doctypes.split(',')]
        else:
            doctype_list = doctypes
        
        print(f"\n📊 Doctypes to migrate: {len(doctype_list)}\n")
        
        # Display doctypes
        for dt in doctype_list:
            exists = frappe.db.exists('DocType', dt)
            status = "✅" if exists else "❌"
            print(f"  {status} {dt}")
        
        # Confirm migration
        confirm = input(f"\n⚠️  Migrate {len(doctype_list)} doctypes? (y/N): ").strip().lower()
        if confirm != 'y':
            print("🚫 Migration cancelled")
            return False
        
        # Migrate doctypes
        migrated_count = 0
        failed_count = 0
        
        for doctype_name in doctype_list:
            try:
                if frappe.db.exists('DocType', doctype_name):
                    frappe.db.set_value('DocType', doctype_name, 'app', target_app)
                    doctype_doc = frappe.get_doc('DocType', doctype_name)
                    module_name = doctype_doc.module
                    
                    print(f"  ✅ Migrated {doctype_name} (module: {module_name})")
                    migrated_count += 1
                else:
                    print(f"  ⚠️  DocType not found: {doctype_name}")
                    failed_count += 1
            except Exception as e:
                print(f"  ❌ Failed to migrate {doctype_name}: {e}")
                failed_count += 1
        
        frappe.db.commit()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 DOCTYPE MIGRATION SUMMARY")
        print("=" * 70)
        print(f"  ✅ Migrated: {migrated_count}")
        print(f"  ❌ Failed: {failed_count}")
        print("🎉 DOCTYPE MIGRATION COMPLETED!")
        
        return migrated_count > 0
        
    except Exception as e:
        print(f"❌ DocType migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def move_module_files(source_app, target_app, modules):
    """
    MOVE MODULE FILES BETWEEN APPS ON FILESYSTEM
    V2-style file system operations
    """
    print(f"\n📁 MOVING FILES: {source_app} → {target_app}")
    print("=" * 70)
    
    try:
        bench_path = Path('/home/frappe/frappe-bench')
        source_app_path = bench_path / 'apps' / source_app / source_app
        target_app_path = bench_path / 'apps' / target_app / target_app
        
        if not source_app_path.exists():
            print(f"❌ Source app path not found: {source_app_path}")
            return False
        
        if not target_app_path.exists():
            print(f"❌ Target app path not found: {target_app_path}")
            return False
        
        moved_count = 0
        failed_count = 0
        
        for module in modules:
            module_path = source_app_path / module
            target_module_path = target_app_path / module
            
            if module_path.exists():
                try:
                    # Create parent directory if needed
                    target_module_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Move module directory
                    shutil.move(str(module_path), str(target_module_path))
                    
                    print(f"  ✅ Moved {module}")
                    moved_count += 1
                except Exception as e:
                    print(f"  ❌ Failed to move {module}: {e}")
                    failed_count += 1
            else:
                print(f"  ⚠️  Module directory not found: {module}")
                failed_count += 1
        
        print("\n" + "=" * 70)
        print("📊 FILE MOVE SUMMARY")
        print("=" * 70)
        print(f"  ✅ Moved: {moved_count}")
        print(f"  ❌ Failed: {failed_count}")
        
        if moved_count > 0:
            print("🎉 FILE MIGRATION COMPLETED!")
        
        return moved_count > 0
        
    except Exception as e:
        print(f"❌ File movement failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ========== LOCAL BENCH MIGRATION (V4) ==========

def clone_app_local(app_name, source_bench="frappe-bench-clean", target_bench="frappe-bench", session_id=None):
    """
    Clone app locally between benches with progress tracking
    V4-style local migration with progress
    """
    tracker = ProgressTracker(app_name)
    
    try:
        # Step 1: Validation
        tracker.update("Validating local migration")
        source_path = f"/home/frappe/{source_bench}/apps/{app_name}"
        target_path = f"/home/frappe/{target_bench}/apps/{app_name}"
        
        if not os.path.exists(source_path):
            tracker.fail(f"App not found in source: {source_path}")
            return False
            
        if os.path.exists(target_path):
            tracker.fail(f"App already exists in target: {target_path}")
            return False
        
        # Step 2: Copy app locally
        tracker.update("Copying app locally")
        success, output = run_command_with_progress(
            f"cd /home/frappe/{target_bench} && bench get-app {app_name} {source_path}",
            f"Local copy: {source_bench} → {target_bench}",
            timeout=300
        )
        
        if not success:
            tracker.fail(f"Local copy failed: {output}")
            return False
        
        # Step 3: Install app
        tracker.update("Installing app to sites")
        success, output = run_command_with_progress(
            f"cd /home/frappe/{target_bench} && bench install-app {app_name}",
            f"Installing {app_name}",
            timeout=300
        )
        
        if success:
            tracker.complete()
            if session_id:
                from .session_manager import SessionManager
                try:
                    session = SessionManager(session_id=session_id)
                    session.update_progress(f"clone_{app_name}", "completed")
                except:
                    pass
            return True
        else:
            tracker.fail(f"Installation failed: {output}")
            return False
            
    except Exception as e:
        tracker.fail(str(e))
        if session_id:
            from .session_manager import SessionManager
            try:
                session = SessionManager(session_id=session_id)
                session.update_progress(f"clone_{app_name}", "failed", str(e))
            except:
                pass
        return False


if __name__ == "__main__":
    # Test migration engine
    print("🧪 Testing Migration Engine\n")
    
    # Test validation
    validate_migration_readiness("test_app", "target_app")
