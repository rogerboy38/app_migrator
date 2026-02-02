"""
Session Manager Module - V5.0.0
Merges V2 decorator-based and V4 class-based session management approaches

Features:
- Session persistence with JSON storage
- Progress tracking
- Connection management with auto-reconnect
- Decorator-based session handling
- Class-based session management
"""

import frappe
from frappe.utils import get_sites
import os
import json
from datetime import datetime
from pathlib import Path
import functools


class SessionManager:
    """
    Enterprise session management class
    Combines V2 decorator pattern with V4 structured session management
    """
    
    SESSION_DIR = "/home/frappe/migration_sessions"
    
    def __init__(self, name=None, session_id=None):
        """
        Initialize session manager
        
        Args:
            name: Session name (for new session)
            session_id: Existing session ID (to load session)
        """
        if session_id:
            # Load existing session
            self.session_id = session_id
            self.data = self.load_session(session_id)
            if not self.data:
                raise ValueError(f"Session {session_id} not found")
            self.name = self.data['metadata']['name']
        elif name:
            # Create new session
            self.name = name
            self.session_id = f"session_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.data = self._create_initial_data()
        else:
            raise ValueError("Either name or session_id must be provided")
        
        # Ensure session directory exists
        os.makedirs(self.SESSION_DIR, exist_ok=True)
    
    def _create_initial_data(self):
        """Create initial session data structure"""
        return {
            "metadata": {
                "name": self.name,
                "session_id": self.session_id,
                "start_time": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "status": "active",
                "current_phase": "initialization"
            },
            "progress": {
                "current_operation": None,
                "completed_operations": [],
                "failed_operations": [],
                "total_operations": 0,
                "success_count": 0,
                "failure_count": 0
            },
            "migration_data": {
                "source_app": None,
                "target_app": None,
                "migrated_modules": [],
                "migrated_doctypes": [],
                "pending_modules": [],
                "pending_doctypes": []
            },
            "connection_data": {
                "reconnection_count": 0,
                "last_reconnection": None,
                "site": None
            }
        }
    
    def save(self):
        """Save session to disk"""
        try:
            self.data['metadata']['last_updated'] = datetime.now().isoformat()
            session_file = os.path.join(self.SESSION_DIR, f"{self.session_id}.json")
            
            with open(session_file, 'w') as f:
                json.dump(self.data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"❌ Failed to save session: {e}")
            return False
    
    @classmethod
    def load_session(cls, session_id):
        """Load session from disk"""
        try:
            session_file = os.path.join(cls.SESSION_DIR, f"{session_id}.json")
            if os.path.exists(session_file):
                with open(session_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            print(f"❌ Failed to load session: {e}")
            return None
    
    @classmethod
    def list_sessions(cls):
        """List all available sessions"""
        try:
            if not os.path.exists(cls.SESSION_DIR):
                return []
            
            sessions = []
            for file in os.listdir(cls.SESSION_DIR):
                if file.endswith('.json'):
                    session_id = file[:-5]  # Remove .json extension
                    data = cls.load_session(session_id)
                    if data:
                        sessions.append({
                            'session_id': session_id,
                            'name': data['metadata']['name'],
                            'status': data['metadata']['status'],
                            'start_time': data['metadata']['start_time']
                        })
            
            return sorted(sessions, key=lambda x: x['start_time'], reverse=True)
        except Exception as e:
            print(f"❌ Failed to list sessions: {e}")
            return []
    
    def update_progress(self, operation, status, details=None):
        """
        Update session progress
        
        Args:
            operation: Operation name
            status: 'started', 'completed', 'failed'
            details: Additional details (optional)
        """
        try:
            operation_data = {
                "operation": operation,
                "status": status,
                "timestamp": datetime.now().isoformat(),
                "details": details
            }
            
            self.data['progress']['current_operation'] = operation
            self.data['progress']['total_operations'] += 1
            
            if status == 'completed':
                self.data['progress']['completed_operations'].append(operation_data)
                self.data['progress']['success_count'] += 1
            elif status == 'failed':
                self.data['progress']['failed_operations'].append(operation_data)
                self.data['progress']['failure_count'] += 1
            
            self.save()
            return True
        except Exception as e:
            print(f"❌ Failed to update progress: {e}")
            return False
    
    def set_phase(self, phase):
        """Update current migration phase"""
        self.data['metadata']['current_phase'] = phase
        self.save()
    
    def set_status(self, status):
        """Update session status"""
        self.data['metadata']['status'] = status
        self.save()
    
    def get_progress_summary(self):
        """Get formatted progress summary"""
        progress = self.data['progress']
        total = progress['total_operations']
        success = progress['success_count']
        failed = progress['failure_count']
        
        if total > 0:
            success_rate = (success / total) * 100
        else:
            success_rate = 0
        
        return {
            'total_operations': total,
            'success_count': success,
            'failure_count': failed,
            'success_rate': success_rate,
            'current_operation': progress['current_operation']
        }
    
    def display_status(self):
        """Display formatted session status"""
        print("\n" + "=" * 70)
        print(f"📊 SESSION STATUS: {self.name}")
        print("=" * 70)
        
        metadata = self.data['metadata']
        print(f"\n🆔 Session ID: {self.session_id}")
        print(f"📈 Status: {metadata['status'].upper()}")
        print(f"🕐 Started: {metadata['start_time']}")
        print(f"🔄 Last Updated: {metadata['last_updated']}")
        print(f"📍 Current Phase: {metadata['current_phase']}")
        
        summary = self.get_progress_summary()
        print(f"\n📊 Progress:")
        print(f"  Total Operations: {summary['total_operations']}")
        print(f"  ✅ Success: {summary['success_count']}")
        print(f"  ❌ Failed: {summary['failure_count']}")
        print(f"  📈 Success Rate: {summary['success_rate']:.1f}%")
        
        if summary['current_operation']:
            print(f"\n🔄 Current Operation: {summary['current_operation']}")
        
        # Show recent operations
        completed = self.data['progress']['completed_operations']
        if completed:
            print(f"\n🕐 Recent Completed Operations:")
            for op in completed[-5:]:
                print(f"  ✅ {op['operation']} ({op['timestamp']})")
        
        failed = self.data['progress']['failed_operations']
        if failed:
            print(f"\n❌ Recent Failed Operations:")
            for op in failed[-5:]:
                print(f"  ❌ {op['operation']} ({op['timestamp']})")
                if op.get('details'):
                    print(f"     Details: {op['details']}")
        
        print("\n" + "=" * 70)


# ========== V2-STYLE CONNECTION MANAGEMENT ==========

def ensure_frappe_connection():
    """
    Ensure Frappe connection is active - CRITICAL FOR LONG-RUNNING OPERATIONS
    V2-style connection management
    """
    try:
        frappe.db.sql("SELECT 1")
        return True
    except Exception:
        try:
            sites = get_sites()
            site = sites[0] if sites else None
            if site:
                frappe.init(site=site)
                frappe.connect()
                print("   🔄 Session reconnected")
                return True
        except Exception as e:
            print(f"   ❌ Failed to reconnect: {e}")
            return False
    return False


def with_session_management(func):
    """
    Decorator to handle session management for all migration functions
    V2-style decorator pattern with auto-reconnect
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            if not ensure_frappe_connection():
                print("❌ Cannot establish Frappe connection")
                return None
            
            result = func(*args, **kwargs)
            frappe.db.commit()
            return result
            
        except Exception as e:
            print(f"❌ Session error in {func.__name__}: {e}")
            try:
                print("   🔄 Attempting recovery...")
                if ensure_frappe_connection():
                    result = func(*args, **kwargs)
                    frappe.db.commit()
                    return result
            except Exception as retry_error:
                print(f"   ❌ Recovery failed: {retry_error}")
            return None
    
    return wrapper


def with_session_tracking(session_id=None):
    """
    Decorator to track operation in session
    Combines V2 connection management with V4 session tracking
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get or create session
            session = None
            if session_id:
                try:
                    session = SessionManager(session_id=session_id)
                except:
                    pass
            
            operation_name = func.__name__
            
            try:
                # Ensure connection
                if not ensure_frappe_connection():
                    print("❌ Cannot establish Frappe connection")
                    if session:
                        session.update_progress(operation_name, 'failed', 'Connection failed')
                    return None
                
                # Track start
                if session:
                    session.update_progress(operation_name, 'started')
                
                # Execute function
                result = func(*args, **kwargs)
                frappe.db.commit()
                
                # Track success
                if session:
                    session.update_progress(operation_name, 'completed')
                
                return result
                
            except Exception as e:
                print(f"❌ Error in {operation_name}: {e}")
                
                # Track failure
                if session:
                    session.update_progress(operation_name, 'failed', str(e))
                
                # Attempt recovery
                try:
                    print("   🔄 Attempting recovery...")
                    if ensure_frappe_connection():
                        result = func(*args, **kwargs)
                        frappe.db.commit()
                        if session:
                            session.update_progress(operation_name, 'completed', 'Recovered')
                        return result
                except Exception as retry_error:
                    print(f"   ❌ Recovery failed: {retry_error}")
                
                return None
        
        return wrapper
    return decorator


if __name__ == "__main__":
    # Test session management
    print("🧪 Testing Session Manager\n")
    
    # Create new session
    session = SessionManager(name="test_migration")
    print(f"✅ Created session: {session.session_id}")
    
    # Update progress
    session.update_progress("analyze_app", "started")
    session.update_progress("analyze_app", "completed")
    session.update_progress("migrate_modules", "started")
    session.update_progress("migrate_modules", "completed")
    
    # Display status
    session.display_status()
    
    # List all sessions
    print("\n📋 All Sessions:")
    for s in SessionManager.list_sessions():
        print(f"  • {s['name']} ({s['session_id']}) - {s['status']}")
