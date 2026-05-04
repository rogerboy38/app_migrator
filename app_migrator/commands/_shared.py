"""
Cross-command shared helpers (T1.8.1).

Holds utilities used by multiple command modules. Extracted from
commands/__init__.py and commands/migration_engine.py to provide a
single canonical home — see launch brief §1.5 / Phase 1 plan §T1.8.

Public API:
  - ProgressTracker   — visual progress tracking with in-place updates
  - MigrationSession  — session metadata persistence (~/migration_sessions/)
  - get_current_site  — best-effort detection of the active site
  - detect_available_benches  — list ~/frappe-bench* directories
  - get_bench_apps    — list installed apps in a bench via `bench version`
"""

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path


# ==================== PROGRESS TRACKING ====================
# Canonical version (was duplicated in __init__.py and migration_engine.py).
# Uses carriage-return in-place updates for terminal feedback; default
# step labels supplied if caller doesn't pass a message.
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


# ==================== SITE DETECTION ====================

def get_current_site():
    """Get current site from common_site_config.json or currentsite.txt"""
    home = str(Path.home())
    possible_paths = [
        os.path.join(os.getcwd(), 'sites'),
        os.path.join(home, 'frappe-bench', 'sites'),
        os.path.abspath(os.path.join(os.getcwd(), '..', '..', 'sites')),
    ]
    for sites_path in possible_paths:
        # Try common_site_config.json first (has default_site)
        config_file = os.path.join(sites_path, 'common_site_config.json')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                if config.get('default_site'):
                    return config['default_site']
        # Fallback to currentsite.txt
        currentsite_file = os.path.join(sites_path, 'currentsite.txt')
        if os.path.exists(currentsite_file):
            with open(currentsite_file, 'r') as f:
                return f.read().strip()
    return None


# ==================== BENCH DISCOVERY (legacy) ====================
# Note: T1.9 will add find_bench_root() and discover_all_benches() with
# proper apps/apps.txt + sites/ + Procfile detection. The functions below
# are the legacy ~/frappe-bench* glob, kept to preserve current behavior
# until T1.9 replaces them.

def detect_available_benches():
    """Detect all available benches (legacy ~/frappe-bench* glob)"""
    benches = []
    frappe_home = os.path.expanduser('~')
    for item in os.listdir(frappe_home):
        if item.startswith('frappe-bench') and os.path.isdir(os.path.join(frappe_home, item)):
            benches.append(item)
    return sorted(benches)


def get_bench_apps(bench_path):
    """Get installed apps from a bench by running `bench version`"""
    try:
        result = subprocess.run(
            f"cd {bench_path} && bench version",
            shell=True, capture_output=True, text=True, timeout=30
        )
        apps = []
        for line in result.stdout.strip().split('\n'):
            if ' ' in line and not line.startswith('✅'):
                app = line.split()[0]
                apps.append(app)
        return sorted(apps)
    except Exception:
        return []


# ==================== MIGRATION SESSION ====================

class MigrationSession:
    """Session metadata persistence under ~/migration_sessions/"""

    def __init__(self, name):
        self.name = name
        self.session_id = f"session_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.session_dir = os.path.expanduser("~/migration_sessions")
        self.session_file = f"{self.session_dir}/{self.session_id}.json"
        self.data = {
            "metadata": {
                "name": name,
                "session_id": self.session_id,
                "start_time": datetime.now().isoformat(),
                "status": "active",
            },
            "progress": {"completed_apps": [], "failed_apps": []},
            "migration_plan": {},
        }
        os.makedirs(self.session_dir, exist_ok=True)

    def save(self):
        with open(self.session_file, 'w') as f:
            json.dump(self.data, f, indent=2)
        return self.session_id

    @staticmethod
    def load(session_id):
        session_file = os.path.expanduser(f"~/migration_sessions/{session_id}.json")
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                return json.load(f)
        return None
