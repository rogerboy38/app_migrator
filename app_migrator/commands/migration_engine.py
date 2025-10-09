# migration_engine.py - ENHANCED VERSION
import os
import subprocess
import time
import threading
from pathlib import Path
from ..utils.session import load_session, update_session_progress

class ProgressTracker:
    """Track migration progress with visual feedback"""
    
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
    
    def update(self, message=None):
        self.current_step += 1
        if message:
            print(f"\r🔄 [{self.current_step}/{self.total_steps}] {message}", end="", flush=True)
        else:
            print(f"\r🔄 [{self.current_step}/{self.total_steps}] {self.steps[self.current_step-1]}", end="", flush=True)
    
    def complete(self):
        print(f"\r✅ [{self.total_steps}/{self.total_steps}] {self.app_name} migration completed!")
    
    def fail(self, error):
        print(f"\r❌ [{self.current_step}/{self.total_steps}] {self.app_name} failed: {error}")

def monitor_directory_creation(app_name, timeout=600, check_interval=5):
    """Monitor app directory creation with progress"""
    target_path = f"/home/frappe/frappe-bench/apps/{app_name}"
    print(f"👀 Monitoring directory: {target_path}")
    
    for i in range(timeout // check_interval):
        if os.path.exists(target_path):
            size = get_directory_size(target_path)
            print(f"✅ Directory created: {app_name} ({size})")
            return True
        
        # Progress indicator
        dots = "." * (i % 4)
        print(f"\r⏳ Waiting for {app_name} directory{dots} ({i*check_interval}s)", end="", flush=True)
        time.sleep(check_interval)
    
    print(f"\r❌ Timeout: {app_name} directory not created after {timeout}s")
    return False

def get_directory_size(path):
    """Get human-readable directory size"""
    try:
        result = subprocess.run(
            f"du -sh {path}", 
            shell=True, capture_output=True, text=True
        )
        return result.stdout.strip().split()[0]
    except:
        return "unknown size"

def run_command_with_progress(command, description, timeout=600):
    """Run command with progress feedback"""
    print(f"🔄 {description}...")
    
    try:
        # Start process
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Monitor process with timeout
        start_time = time.time()
        while process.poll() is None:
            if time.time() - start_time > timeout:
                process.terminate()
                return False, f"Timeout after {timeout}s"
            
            # Show progress indicator
            elapsed = int(time.time() - start_time)
            print(f"\r⏳ {description}... ({elapsed}s)", end="", flush=True)
            time.sleep(2)
        
        # Get result
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            print(f"\r✅ {description} completed!")
            return True, stdout
        else:
            print(f"\r❌ {description} failed!")
            return False, stderr
            
    except Exception as e:
        return False, str(e)

def clone_app_with_progress(app_name, session_id=None):
    """Enhanced clone app with progress tracking"""
    tracker = ProgressTracker(app_name)
    
    try:
        # Step 1: Validation
        tracker.update("Validating migration readiness")
        if not validate_migration_readiness(app_name):
            tracker.fail("Migration validation failed")
            return False
        
        # Step 2: Get app
        tracker.update("Downloading app from source")
        success, output = run_command_with_progress(
            f"cd /home/frappe/frappe-bench && bench get-app {app_name}",
            f"Downloading {app_name}"
        )
        
        if not success:
            tracker.fail(f"Download failed: {output}")
            return False
        
        # Step 3: Monitor directory creation
        tracker.update("Monitoring installation")
        if not monitor_directory_creation(app_name):
            tracker.fail("Directory not created")
            return False
        
        # Step 4: Install app
        tracker.update("Installing app to sites")
        success, output = run_command_with_progress(
            f"cd /home/frappe/frappe-bench && bench install-app {app_name}",
            f"Installing {app_name}"
        )
        
        if not success:
            tracker.fail(f"Installation failed: {output}")
            return False
        
        # Step 5: Complete
        tracker.complete()
        
        # Update session
        if session_id:
            update_session_progress(session_id, f"clone_{app_name}", "completed")
        
        return True
        
    except Exception as e:
        tracker.fail(str(e))
        if session_id:
            update_session_progress(session_id, f"clone_{app_name}", "failed", str(e))
        return False

def validate_migration_readiness(app_name):
    """Check if migration is possible"""
    # Check if app already exists in target
    target_path = f"/home/frappe/frappe-bench/apps/{app_name}"
    if os.path.exists(target_path):
        print(f"❌ {app_name} already exists in target bench")
        return False
    
    # Check disk space
    try:
        result = subprocess.run(
            "df /home/frappe --output=avail | tail -1",
            shell=True, capture_output=True, text=True
        )
        free_space = int(result.stdout.strip()) / 1024 / 1024  # Convert to GB
        if free_space < 2:  # Less than 2GB free
            print(f"❌ Insufficient disk space: {free_space:.1f}GB free")
            return False
    except:
        pass  # Continue if disk check fails
    
    return True

# Keep original function for compatibility
def clone_app(app_name, session_id=None):
    """Main clone app function with progress tracking"""
    return clone_app_with_progress(app_name, session_id)
