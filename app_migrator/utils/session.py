"""
🎯 Enterprise Session Management System
Migration session tracking, persistence, and recovery
"""

import json
import os
from datetime import datetime
from pathlib import Path

class MigrationSession:
    def __init__(self, name, session_id=None):
        """
        Initialize a migration session
        If session_id is provided, load existing session
        Otherwise create new session
        """
        if session_id:
            # Load existing session
            self.session_id = session_id
            self.session_dir = Path("/home/frappe/migration_sessions")
            self.session_file = self.session_dir / f"{self.session_id}.json"
            
            if self.session_file.exists():
                # Load existing data
                with open(self.session_file, 'r') as f:
                    self.data = json.load(f)
                print(f"🔍 DEBUG: Loaded existing session: {self.data['metadata']['name']}")
            else:
                # Create new session with provided ID (shouldn't happen normally)
                self._initialize_new_session(name)
        else:
            # Create completely new session
            self.session_id = f"session_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.session_dir = Path("/home/frappe/migration_sessions")
            self.session_dir.mkdir(exist_ok=True)
            self.session_file = self.session_dir / f"{self.session_id}.json"
            self._initialize_new_session(name)
    
    def _initialize_new_session(self, name):
        """Initialize data for a new session"""
        self.data = {
            "metadata": {
                "name": name,
                "session_id": self.session_id,
                "start_time": datetime.now().isoformat(),
                "status": "active",
                "current_phase": "initialization"
            },
            "progress": {
                "completed_operations": [],
                "current_operation": None,
                "failed_operations": [],
                "checkpoints": {}
            },
            "migration_data": {
                "source_bench": None,
                "target_bench": None,
                "apps_to_migrate": [],
                "completed_apps": []
            },
            "system_state": {
                "pre_migration_snapshot": {},
                "backup_locations": {},
                "rollback_instructions": {}
            }
        }
    
    def save(self):
        """Save session to file"""
        try:
            # Ensure directory exists
            self.session_dir.mkdir(exist_ok=True)
            
            with open(self.session_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            
            print(f"🔍 DEBUG: Session saved to: {self.session_file}")
            return self.session_id
        except Exception as e:
            print(f"❌ Failed to save session: {e}")
            return None
    
    def update_progress(self, operation, status="completed", details=None):
        """Update progress tracking"""
        try:
            progress_entry = {
                "operation": operation,
                "status": status,
                "timestamp": datetime.now().isoformat()
            }
            if details:
                progress_entry["details"] = details
                
            self.data["progress"]["completed_operations"].append(progress_entry)
            
            # Update current operation
            if status == "completed":
                self.data["progress"]["current_operation"] = None
            else:
                self.data["progress"]["current_operation"] = operation
            
            # Auto-save on progress update
            self.save()
            print(f"🔍 DEBUG: Progress updated: {operation} - {status}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update progress: {e}")
            return False
    
    def add_checkpoint(self, checkpoint_name, data):
        """Add a rollback checkpoint"""
        try:
            self.data["progress"]["checkpoints"][checkpoint_name] = {
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            self.save()
            return True
        except Exception as e:
            print(f"❌ Failed to add checkpoint: {e}")
            return False
    
    def set_migration_plan(self, source_bench, target_bench, apps_to_migrate):
        """Set migration plan details"""
        try:
            self.data["migration_data"]["source_bench"] = source_bench
            self.data["migration_data"]["target_bench"] = target_bench
            self.data["migration_data"]["apps_to_migrate"] = apps_to_migrate
            self.save()
            return True
        except Exception as e:
            print(f"❌ Failed to set migration plan: {e}")
            return False
    
    def mark_app_completed(self, app_name):
        """Mark an app as successfully migrated"""
        try:
            if app_name not in self.data["migration_data"]["completed_apps"]:
                self.data["migration_data"]["completed_apps"].append(app_name)
            self.save()
            return True
        except Exception as e:
            print(f"❌ Failed to mark app completed: {e}")
            return False
    
    def get_status(self):
        """Get comprehensive session status"""
        try:
            total_ops = len(self.data["progress"]["completed_operations"])
            completed_ops = len([op for op in self.data["progress"]["completed_operations"] if op["status"] == "completed"])
            failed_ops = len([op for op in self.data["progress"]["completed_operations"] if op["status"] == "failed"])
            
            return {
                "session_id": self.session_id,
                "name": self.data["metadata"]["name"],
                "status": self.data["metadata"]["status"],
                "current_phase": self.data["metadata"]["current_phase"],
                "progress_metrics": {
                    "total_operations": total_ops,
                    "completed": completed_ops,
                    "failed": failed_ops,
                    "success_rate": f"{(completed_ops/total_ops)*100:.1f}%" if total_ops > 0 else "0%"
                },
                "migration_progress": {
                    "total_apps": len(self.data["migration_data"]["apps_to_migrate"]),
                    "completed_apps": len(self.data["migration_data"]["completed_apps"]),
                    "remaining_apps": len(self.data["migration_data"]["apps_to_migrate"]) - len(self.data["migration_data"]["completed_apps"])
                }
            }
        except Exception as e:
            print(f"❌ Failed to get session status: {e}")
            return None
    
    def complete_session(self):
        """Mark session as completed"""
        try:
            self.data["metadata"]["status"] = "completed"
            self.data["metadata"]["end_time"] = datetime.now().isoformat()
            self.save()
            return True
        except Exception as e:
            print(f"❌ Failed to complete session: {e}")
            return False
    
    def fail_session(self, reason):
        """Mark session as failed"""
        try:
            self.data["metadata"]["status"] = "failed"
            self.data["metadata"]["end_time"] = datetime.now().isoformat()
            self.data["metadata"]["failure_reason"] = reason
            self.save()
            return True
        except Exception as e:
            print(f"❌ Failed to mark session as failed: {e}")
            return False

def load_session(session_id):
    """Load existing session by session_id"""
    try:
        session_file = Path(f"/home/frappe/migration_sessions/{session_id}.json")
        if session_file.exists():
            with open(session_file, 'r') as f:
                data = json.load(f)
            print(f"🔍 DEBUG: load_session() loaded: {session_id}")
            return data
        else:
            print(f"🔍 DEBUG: load_session() file not found: {session_id}")
            return None
    except Exception as e:
        print(f"❌ Failed to load session {session_id}: {e}")
        return None

def list_all_sessions():
    """List all migration sessions"""
    try:
        sessions_dir = Path("/home/frappe/migration_sessions")
        sessions = []
        
        if sessions_dir.exists():
            for session_file in sessions_dir.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        data = json.load(f)
                    sessions.append({
                        "file": session_file.name,
                        "data": data
                    })
                except Exception as e:
                    print(f"❌ Error reading {session_file}: {e}")
        
        print(f"🔍 DEBUG: list_all_sessions() found {len(sessions)} sessions")
        return sessions
        
    except Exception as e:
        print(f"❌ Failed to list sessions: {e}")
        return []

def get_session_by_name(session_name):
    """Find session by name (not session_id)"""
    try:
        sessions = list_all_sessions()
        for session in sessions:
            if session["data"]["metadata"]["name"] == session_name:
                print(f"🔍 DEBUG: get_session_by_name() found: {session_name}")
                return session["data"]
        print(f"🔍 DEBUG: get_session_by_name() not found: {session_name}")
        return None
    except Exception as e:
        print(f"❌ Failed to get session by name: {e}")
        return None
