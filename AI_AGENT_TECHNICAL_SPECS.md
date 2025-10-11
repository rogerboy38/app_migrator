# 🤖 App Migrator v5.0.0 - AI Agent Technical Specification

> **Complete technical reference for AI agents** - Architecture, APIs, patterns, and integration guidelines

**Version**: 5.0.0  
**Last Updated**: October 11, 2025  
**Author**: MiniMax Agent  
**Purpose**: Enable AI agents to understand, integrate, and work with App Migrator

---

## 📋 Table of Contents

1. [Project Overview](#-project-overview)
2. [Architecture & Design](#-architecture--design)
3. [Module Reference](#-module-reference)
4. [API Reference](#-api-reference)
5. [Usage Patterns](#-usage-patterns)
6. [Integration Guidelines](#-integration-guidelines)
7. [Code Examples](#-code-examples)
8. [Troubleshooting](#-troubleshooting)
9. [Performance Optimization](#-performance-optimization)
10. [Version History](#-version-history)

---

## 🌟 Project Overview

### What is App Migrator?

App Migrator v5.0.0 is a comprehensive Frappe/ERPNext application migration toolkit that provides:
- **23 specialized commands** across **12 modules**
- **Intelligent DocType classification** (Standard/Customized/Custom/Orphan)
- **Interactive migration wizard** for guided workflows
- **Data quality management** tools
- **Database schema operations**
- **Multi-bench support** for complex environments
- **Session management** with persistence and auto-reconnect
- **Progress tracking** for long-running operations

### Key Capabilities

```python
# What you can do with App Migrator:
1. Analyze apps comprehensively
2. Migrate modules between apps
3. Fix orphaned doctypes
4. Restore missing doctype files
5. Verify and fix database schemas
6. Classify doctypes by status
7. Manage multi-bench environments
8. Track migration sessions
9. Generate risk assessments
10. Complete ERPNext installations
```

### Technology Stack

- **Language**: Python 3.8+
- **Framework**: Frappe Framework v13+
- **Database**: MariaDB 10.3+ / PostgreSQL 12+
- **CLI**: Frappe Bench CLI
- **Design**: Hybrid (Decorator-based + Class-based)

### Repository Information

- **GitHub**: https://github.com/rogerboy38/app_migrator
- **Branch**: `v5.0.0`
- **License**: MIT
- **Maintainer**: rogerboy38

---

## 🏗️ Architecture & Design

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Entry Point                           │
│               (bench migrate-app <command>)                  │
└──────────────┬──────────────────────────────┬────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────┐    ┌────────────────────────────┐
│   Command Dispatcher     │    │   Interactive Wizard       │
│     (__init__.py)        │◄───┤  (enhanced_interactive_    │
└──────────────────────────┘    │    wizard.py)              │
               │                 └────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Core Modules Layer                         │
├──────────────────────────────────────────────────────────────┤
│  • DocType Classifier (doctype_classifier.py)                │
│  • Migration Engine (migration_engine.py)                    │
│  • Data Quality (data_quality.py)                            │
│  • Database Schema (database_schema.py)                      │
│  • Analysis Tools (analysis_tools.py)                        │
│  • Session Manager (session_manager.py)                      │
│  • Progress Tracker (progress_tracker.py)                    │
│  • Multi-Bench (multi_bench.py)                              │
└──────────────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Frappe Framework                           │
│              (frappe.db, frappe.get_doc, etc.)               │
└──────────────────────────────────────────────────────────────┘
```

### Design Patterns

#### 1. Decorator Pattern (V2 Legacy)

Used for automatic session management:

```python
@with_session_management
def migrate_app_modules(source_app, target_app, modules=None):
    """Decorator ensures connection is active before execution"""
    # Function implementation
    pass

@with_session_tracking
def analyze_app_comprehensive(app_name):
    """Decorator adds session + progress tracking"""
    # Function implementation
    pass
```

**Benefits**:
- Automatic connection management
- Transparent error handling
- Progress tracking integration
- Minimal code changes needed

#### 2. Class-Based Management (V4 Style)

Used for stateful operations:

```python
# Session Management
session = SessionManager(name="my_migration")
session.update_progress("analyze", "started")
session.save()

# Progress Tracking
tracker = ProgressTracker("MyApp", total_steps=5)
tracker.update("Processing...")
tracker.complete()
```

**Benefits**:
- Explicit control over state
- Better testability
- Rich API with methods
- Persistent storage

#### 3. Modular Architecture

Each module has a single responsibility:

```python
# Separation of Concerns
doctype_classifier.py   → Classification logic
migration_engine.py     → Migration operations
data_quality.py         → Data validation & fixing
database_schema.py      → Schema operations
analysis_tools.py       → Analysis & reporting
session_manager.py      → Session lifecycle
progress_tracker.py     → Progress visualization
```

**Benefits**:
- Easy to test individual modules
- Clear dependencies
- Reusable components
- Maintainable codebase

#### 4. Strategy Pattern

Different classification strategies:

```python
def get_doctype_classification(doctype_name):
    """Returns: standard, customized, custom, or orphan"""
    
    # Strategy 1: Check if custom doctype
    if doc.custom == 1:
        return {"status": "custom"}
    
    # Strategy 2: Check if customized
    if has_custom_fields or has_property_setters:
        return {"status": "customized"}
    
    # Strategy 3: Check if orphan
    if doc.app is None or doc.module == "":
        return {"status": "orphan"}
    
    # Strategy 4: Default to standard
    return {"status": "standard"}
```

### File Structure

```
app_migrator_v5/
├── app_migrator/
│   ├── __init__.py                      # Package initialization
│   ├── hooks.py                         # Frappe hooks
│   ├── commands/                        # Command modules
│   │   ├── __init__.py                 # Command registry (362 lines)
│   │   ├── doctype_classifier.py      # Classification (400 lines)
│   │   ├── enhanced_interactive_wizard.py  # Wizard (550 lines)
│   │   ├── database_schema.py         # Schema ops (450 lines)
│   │   ├── data_quality.py            # Quality tools (600 lines)
│   │   ├── session_manager.py         # Sessions (450 lines)
│   │   ├── migration_engine.py        # Migration (600 lines)
│   │   ├── analysis_tools.py          # Analysis (450 lines)
│   │   ├── progress_tracker.py        # Progress (300 lines)
│   │   ├── multi_bench.py             # Multi-bench (100 lines)
│   │   ├── database_intel.py          # DB intel (100 lines)
│   │   └── test_precise_apps.py       # Testing (100 lines)
│   ├── config/                         # Configuration
│   ├── public/                         # Public assets
│   └── templates/                      # Web templates
├── README.md                            # Main documentation
├── USER_GUIDE.md                       # User guide
├── DEPLOYMENT.md                       # Deployment guide
├── CHANGELOG.md                        # Version history
├── COMMAND_MODULES_SUMMARY.md          # Module summary
├── QUICK_REFERENCE.md                  # Quick reference
└── AI_AGENT_TECHNICAL_SPECS.md         # This file
```

**Total Code**: ~4,585 lines across 12 modules

---

## 📦 Module Reference

### 1. Command Registry (`__init__.py`)

**Purpose**: Central command dispatcher and CLI integration

**Key Functions**:
```python
# Main CLI entry point
def main():
    """Registers all 23 commands with bench"""
    pass

# Command registration
@click.group()
def commands():
    """App Migrator v5.0.0 - CLI Commands"""
    pass

# Individual command decorators
@commands.command('interactive')
@commands.command('analyze')
@commands.command('migrate')
# ... 20 more commands
```

**Exports**:
```python
from app_migrator.commands import (
    # Interactive
    interactive_migration_wizard,
    
    # Analysis
    analyze_app_comprehensive,
    classify_doctypes,
    analyze_orphans,
    
    # Migration
    migrate_app_modules,
    migrate_specific_doctypes,
    
    # Data Quality
    fix_orphan_doctypes,
    restore_missing_doctypes,
    fix_app_none_doctypes,
    
    # Database
    verify_database_schema,
    fix_database_schema,
    fix_tree_doctypes,
    
    # Session & Progress
    SessionManager,
    ProgressTracker,
    
    # Multi-Bench
    detect_available_benches,
    multi_bench_analysis,
)
```

### 2. DocType Classifier (`doctype_classifier.py`)

**Purpose**: Intelligent classification of DocTypes by status

**Classification Logic**:
```python
"""
DocType Status Classification:

1. CUSTOM (custom=1)
   - User-created doctypes
   - Has 'custom' field set to 1
   - Usually prefixed with organization name
   
2. CUSTOMIZED (has modifications)
   - Standard doctypes with Custom Fields
   - Standard doctypes with Property Setters
   - Modified from original framework version
   
3. ORPHAN (broken references)
   - app = None or empty
   - module = None or empty
   - Missing from app structure
   - Incorrect module assignment
   
4. STANDARD (unchanged)
   - Core framework doctypes
   - No custom fields
   - No property setters
   - Original framework code
"""
```

**Key Functions**:
```python
def get_doctype_classification(doctype_name: str) -> dict:
    """
    Classify a single doctype
    
    Returns:
        {
            "status": "standard|customized|custom|orphan",
            "doctype": "DocType Name",
            "app": "app_name",
            "module": "Module Name",
            "custom_fields": [...],
            "property_setters": [...],
            "reasons": [...]
        }
    """

def classify_all_doctypes(app_name: str = None) -> dict:
    """
    Classify all doctypes (optionally filter by app)
    
    Returns:
        {
            "standard": ["DocType1", "DocType2"],
            "customized": ["DocType3", "DocType4"],
            "custom": ["DocType5", "DocType6"],
            "orphan": ["DocType7", "DocType8"],
            "summary": {
                "total": 100,
                "standard": 60,
                "customized": 20,
                "custom": 15,
                "orphan": 5
            }
        }
    """

def has_custom_fields(doctype_name: str) -> list:
    """Returns list of Custom Fields for doctype"""

def has_property_setters(doctype_name: str) -> list:
    """Returns list of Property Setters for doctype"""

def is_orphan_doctype(doctype_name: str) -> bool:
    """Check if doctype is orphaned"""
```

**Usage Example**:
```python
# Classify a single doctype
result = get_doctype_classification("Customer")
print(f"Status: {result['status']}")
print(f"Custom Fields: {len(result['custom_fields'])}")

# Classify all doctypes in an app
all_results = classify_all_doctypes("erpnext")
print(f"Total: {all_results['summary']['total']}")
print(f"Orphans: {all_results['orphan']}")
```

### 3. Enhanced Interactive Wizard (`enhanced_interactive_wizard.py`)

**Purpose**: User-friendly guided migration workflow

**Workflow Steps**:
```python
"""
Interactive Wizard Flow:

1. Welcome Screen
   └─> Display version and features

2. Site Selection
   ├─> List available sites
   ├─> Validate selection
   └─> Set active site

3. App Selection
   ├─> List apps in site
   ├─> Show app details
   └─> Select source/target apps

4. Module Analysis
   ├─> List all modules
   ├─> Classify doctypes
   └─> Show classification summary

5. Status Filtering
   ├─> Filter by Standard
   ├─> Filter by Customized
   ├─> Filter by Custom
   └─> Filter by Orphan

6. Migration Options
   ├─> Migrate all modules
   ├─> Migrate specific modules
   ├─> Migrate specific doctypes
   └─> Generate risk assessment

7. Execution
   ├─> Confirm selections
   ├─> Execute migration
   ├─> Show progress
   └─> Display results

8. Post-Migration
   ├─> Verify integrity
   ├─> Generate report
   └─> Save session
"""
```

**Key Functions**:
```python
def interactive_migration_wizard():
    """Main wizard entry point"""

def select_site() -> str:
    """Interactive site selection with validation"""

def list_apps_in_site(site: str) -> list:
    """List all apps installed in site"""

def select_app(apps: list) -> str:
    """Interactive app selection"""

def analyze_app_modules(app_name: str) -> dict:
    """
    Analyze app modules with classification
    
    Returns:
        {
            "modules": [...],
            "doctypes": {...},
            "classification": {...},
            "summary": {...}
        }
    """

def filter_by_status(doctypes: dict, status: str) -> list:
    """Filter doctypes by classification status"""

def guided_migration_workflow():
    """Step-by-step migration guidance"""
```

### 4. Database Schema (`database_schema.py`)

**Purpose**: Database schema validation and repair

**Key Functions**:
```python
def verify_database_schema(app_name: str) -> dict:
    """
    Verify database schema integrity
    
    Returns:
        {
            "app": "app_name",
            "total_doctypes": 100,
            "missing_tables": ["DocType1", "DocType2"],
            "issues": [...],
            "status": "ok|needs_fixing"
        }
    """

def fix_database_schema(app_name: str = None) -> dict:
    """
    Create missing tables for doctypes
    
    Process:
    1. Identify missing tables
    2. Call frappe.db.create_table() for each
    3. Verify table creation
    4. Return results
    
    Returns:
        {
            "created": ["Table1", "Table2"],
            "failed": [],
            "total_created": 2
        }
    """

def fix_tree_doctypes(app_name: str = None) -> dict:
    """
    Fix tree doctype structures
    
    Fixes:
    - Missing lft, rgt columns
    - Missing old_parent column
    - Incorrect tree values
    
    Returns:
        {
            "fixed": ["TreeDocType1", "TreeDocType2"],
            "errors": []
        }
    """

def complete_erpnext_install() -> dict:
    """
    Complete ERPNext installation
    
    Process:
    1. Run all pending migrations
    2. Create missing tables
    3. Fix tree doctypes
    4. Setup defaults
    5. Verify installation
    
    Returns:
        {
            "status": "success|failed",
            "steps_completed": [...],
            "errors": []
        }
    """

def run_database_diagnostics(app_name: str = None) -> dict:
    """
    Comprehensive database diagnostics
    
    Checks:
    - Missing tables
    - Orphan tables (no doctype)
    - Schema mismatches
    - Tree doctype issues
    - Index health
    - Foreign key constraints
    
    Returns:
        {
            "summary": {...},
            "missing_tables": [...],
            "orphan_tables": [...],
            "issues": [...]
        }
    """
```

**Usage Example**:
```python
# Verify schema
result = verify_database_schema("erpnext")
if result["status"] == "needs_fixing":
    # Fix issues
    fix_result = fix_database_schema("erpnext")
    print(f"Created {fix_result['total_created']} tables")

# Run full diagnostics
diagnostics = run_database_diagnostics()
print(f"Found {len(diagnostics['issues'])} issues")
```

### 5. Data Quality (`data_quality.py`)

**Purpose**: Data validation and quality assurance

**Key Functions**:
```python
def fix_orphan_doctypes(source_app: str) -> dict:
    """
    Fix orphaned doctypes
    
    Process:
    1. Identify orphans (app=None, module=None)
    2. Map to correct app/module
    3. Update doctype records
    4. Verify fixes
    
    Returns:
        {
            "fixed": [...],
            "failed": [...],
            "total_fixed": 10
        }
    """

def restore_missing_doctypes(source_app: str) -> dict:
    """
    Restore missing doctype JSON files
    
    Process:
    1. Find doctypes with missing files
    2. Retrieve from database
    3. Generate JSON structure
    4. Write to filesystem
    5. Verify file creation
    
    Returns:
        {
            "restored": [...],
            "failed": [...],
            "total_restored": 5
        }
    """

def fix_app_none_doctypes(target_app: str) -> dict:
    """
    Fix doctypes with app=None
    
    Process:
    1. Find app=None doctypes
    2. Assign to correct app
    3. Update module references
    4. Verify assignments
    
    Returns:
        {
            "fixed": [...],
            "total": 15
        }
    """

def analyze_cross_app_references(app_name: str) -> dict:
    """
    Analyze references to other apps
    
    Checks:
    - Link fields to other apps
    - Table fields to other apps
    - Dynamic links
    - Select fields with app references
    
    Returns:
        {
            "references": {
                "target_app": ["DocType1", "DocType2"]
            },
            "total_references": 50,
            "warning_count": 3
        }
    """

def verify_data_integrity(app_name: str) -> bool:
    """
    Comprehensive data integrity check
    
    Checks:
    - All doctypes have files
    - All files have database records
    - No orphan doctypes
    - No duplicate doctypes
    - Valid app assignments
    - Valid module assignments
    
    Returns: True if all checks pass
    """
```

**Usage Example**:
```python
# Fix orphans
result = fix_orphan_doctypes("custom_app")
print(f"Fixed {result['total_fixed']} orphans")

# Restore missing files
restored = restore_missing_doctypes("custom_app")
print(f"Restored {restored['total_restored']} files")

# Verify integrity
is_valid = verify_data_integrity("custom_app")
if not is_valid:
    print("Data integrity issues found!")
```

### 6. Session Manager (`session_manager.py`)

**Purpose**: Session persistence and connection management

**Class-Based API**:
```python
class SessionManager:
    """
    Manages migration sessions with persistence
    
    Attributes:
        name: Session name
        timestamp: Creation timestamp
        current_step: Current step name
        progress: Progress data
        results: Operation results
        metadata: Additional metadata
    """
    
    def __init__(self, name: str):
        """Initialize new session or load existing"""
    
    def save(self):
        """Persist session to JSON file"""
    
    @staticmethod
    def load_session(name: str) -> 'SessionManager':
        """Load existing session from file"""
    
    def update_progress(self, step: str, status: str, details: dict = None):
        """Update progress for a step"""
    
    def mark_complete(self, step: str):
        """Mark step as complete"""
    
    def mark_failed(self, step: str, error: str):
        """Mark step as failed"""
    
    def display_status(self):
        """Display formatted session status"""
    
    def get_summary(self) -> dict:
        """Get session summary"""
```

**Decorator-Based API**:
```python
@with_session_management
def my_migration_function():
    """Automatically manages session connection"""
    pass

@with_session_tracking
def my_tracked_function():
    """Adds session tracking + progress monitoring"""
    pass
```

**Helper Functions**:
```python
def ensure_frappe_connection():
    """Ensure Frappe connection is active"""

def reconnect_if_needed():
    """Auto-reconnect if connection lost"""

def list_sessions() -> list:
    """List all saved sessions"""

def delete_old_sessions(days: int = 30):
    """Delete sessions older than specified days"""
```

**Usage Example**:
```python
# Create session
session = SessionManager(name="migration_2025_10_11")

# Update progress
session.update_progress("analyze", "started")
session.update_progress("analyze", "completed", {"doctypes": 100})

# Save session
session.save()

# Load later
loaded = SessionManager.load_session("migration_2025_10_11")
loaded.display_status()

# Using decorators
@with_session_management
def my_function():
    # Connection automatically managed
    pass
```

### 7. Migration Engine (`migration_engine.py`)

**Purpose**: Core migration operations

**Key Functions**:
```python
def migrate_app_modules(
    source_app: str,
    target_app: str,
    modules: list = None,
    skip_backup: bool = False
) -> dict:
    """
    Migrate modules from source to target app
    
    Process:
    1. Validate source and target
    2. Get modules to migrate
    3. For each module:
       a. Move module files
       b. Update doctype records
       c. Update references
       d. Verify migration
    4. Run migrations
    5. Clear cache
    
    Args:
        source_app: Source application name
        target_app: Target application name
        modules: List of modules (None = all)
        skip_backup: Skip backup (not recommended)
    
    Returns:
        {
            "migrated": ["Module1", "Module2"],
            "failed": [],
            "total": 2,
            "status": "success|partial|failed"
        }
    """

def migrate_specific_doctypes(
    source_app: str,
    target_app: str,
    doctypes: list,
    target_module: str = None
) -> dict:
    """
    Migrate specific doctypes
    
    Process:
    1. Validate doctypes exist
    2. Determine target module
    3. For each doctype:
       a. Move JSON files
       b. Update app field
       c. Update module field
       d. Move child tables
       e. Update references
    4. Clear cache
    
    Returns:
        {
            "migrated": ["DocType1", "DocType2"],
            "failed": [],
            "total": 2
        }
    """

def move_module_files(
    source_app: str,
    target_app: str,
    module_name: str
) -> bool:
    """
    Move module files from source to target
    
    Moves:
    - Module directory
    - All doctypes in module
    - Page files
    - Report files
    - Doctype JS/PY files
    
    Returns: True if successful
    """

def validate_migration_readiness(
    source_app: str,
    target_app: str,
    modules: list = None
) -> dict:
    """
    Pre-migration validation
    
    Checks:
    - Source app exists
    - Target app exists
    - Modules exist in source
    - No conflicts in target
    - Database accessible
    - Sufficient permissions
    
    Returns:
        {
            "ready": True|False,
            "issues": [...],
            "warnings": [...]
        }
    """

def clone_app_local(
    app_name: str,
    target_bench: str = None
) -> dict:
    """
    Clone app to local bench
    
    Process:
    1. Detect target bench
    2. Copy app directory
    3. Install dependencies
    4. Add to apps.txt
    5. Run get-app
    
    Returns:
        {
            "status": "success|failed",
            "target_bench": "/path/to/bench",
            "errors": []
        }
    """
```

**Progress Tracking**:
```python
class ProgressTracker:
    """Track operation progress"""
    
    def __init__(self, operation: str, total_steps: int):
        """Initialize tracker"""
    
    def update(self, message: str, step: int = None):
        """Update progress"""
    
    def complete(self):
        """Mark complete"""
    
    def fail(self, error: str):
        """Mark failed"""
    
    def display_progress_bar(self):
        """Show visual progress bar"""

def run_command_with_progress(
    command: str,
    description: str,
    timeout: int = 300
) -> dict:
    """Execute command with progress tracking"""

def monitor_directory_creation(
    path: str,
    timeout: int = 60
) -> bool:
    """Monitor directory creation with progress"""
```

**Usage Example**:
```python
# Migrate all modules
result = migrate_app_modules("old_app", "new_app")
print(f"Migrated: {result['migrated']}")

# Migrate specific modules
result = migrate_app_modules(
    "old_app",
    "new_app",
    modules=["Selling", "Buying"]
)

# Migrate specific doctypes
result = migrate_specific_doctypes(
    "old_app",
    "new_app",
    doctypes=["Custom DocType 1", "Custom DocType 2"],
    target_module="Custom Module"
)

# With progress tracking
tracker = ProgressTracker("Migration", total_steps=5)
tracker.update("Validating...")
# ... operation ...
tracker.complete()
```

### 8. Analysis Tools (`analysis_tools.py`)

**Purpose**: Comprehensive analysis and reporting

**Key Functions**:
```python
def analyze_app_comprehensive(app_name: str) -> dict:
    """
    Comprehensive app analysis
    
    Analyzes:
    - Module structure
    - DocType inventory
    - Custom fields
    - Property setters
    - Cross-app references
    - Orphan doctypes
    - File system structure
    - Dependencies
    
    Returns:
        {
            "app": "app_name",
            "modules": [...],
            "doctypes": {
                "total": 100,
                "standard": 60,
                "customized": 20,
                "custom": 15,
                "orphan": 5
            },
            "dependencies": {...},
            "references": {...},
            "issues": [...],
            "recommendations": [...]
        }
    """

def analyze_bench_health() -> dict:
    """
    Analyze bench health
    
    Checks:
    - Frappe version
    - Python version
    - Node version
    - Database status
    - Disk space
    - App status
    - Configuration
    
    Returns:
        {
            "status": "healthy|warning|critical",
            "checks": {...},
            "issues": [...],
            "recommendations": [...]
        }
    """

def analyze_app_dependencies(app_name: str) -> dict:
    """
    Analyze app dependencies
    
    Analyzes:
    - requirements.txt
    - package.json
    - hooks.py
    - App dependencies
    
    Returns:
        {
            "python_packages": [...],
            "npm_packages": [...],
            "app_dependencies": [...],
            "conflicts": [...]
        }
    """

def detect_available_benches() -> list:
    """
    Detect all benches on system
    
    Returns:
        [
            {
                "path": "/path/to/bench",
                "name": "bench-name",
                "version": "v14.0.0",
                "apps": [...]
            }
        ]
    """

def get_bench_apps(bench_path: str) -> list:
    """List apps in specific bench"""

def multi_bench_analysis() -> dict:
    """
    Analyze entire multi-bench ecosystem
    
    Returns:
        {
            "benches": [...],
            "total_apps": 50,
            "common_apps": [...],
            "unique_apps": {...},
            "summary": {...}
        }
    """

def analyze_orphans() -> dict:
    """
    Detect all orphan doctypes
    
    Returns:
        {
            "orphans": [...],
            "total": 10,
            "by_app": {...},
            "recommendations": [...]
        }
    """
```

**Usage Example**:
```python
# Comprehensive analysis
result = analyze_app_comprehensive("erpnext")
print(f"Total doctypes: {result['doctypes']['total']}")
print(f"Orphans: {result['doctypes']['orphan']}")

# Bench health
health = analyze_bench_health()
if health["status"] != "healthy":
    print(f"Issues: {health['issues']}")

# Dependencies
deps = analyze_app_dependencies("custom_app")
print(f"Python packages: {len(deps['python_packages'])}")

# Multi-bench
benches = multi_bench_analysis()
print(f"Found {len(benches['benches'])} benches")
```

### 9. Progress Tracker (`progress_tracker.py`)

**Purpose**: Visual progress feedback

**Classes**:
```python
class ProgressTracker:
    """Simple progress tracking"""
    
    def __init__(self, operation: str, total_steps: int):
        self.operation = operation
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = time.time()
    
    def update(self, message: str):
        """Update progress"""
    
    def complete(self):
        """Mark complete"""
    
    def fail(self, error: str):
        """Mark failed"""
    
    def display_progress_bar(self):
        """Show progress bar: [=====>    ] 50%"""

class MultiStepProgressTracker:
    """Multi-step progress tracking"""
    
    def __init__(self, steps: list):
        self.steps = steps
        self.step_status = {}
        self.start_time = time.time()
    
    def start_step(self, step: str):
        """Start a step"""
    
    def complete_step(self, step: str):
        """Complete a step"""
    
    def fail_step(self, step: str, error: str):
        """Mark step as failed"""
    
    def display_summary(self):
        """Display step summary"""
```

**Helper Functions**:
```python
def run_with_progress(
    func: callable,
    operation: str,
    *args,
    **kwargs
) -> any:
    """Wrap function with progress tracking"""

def estimate_time_remaining(
    current: int,
    total: int,
    elapsed: float
) -> str:
    """Estimate time remaining"""
```

**Usage Example**:
```python
# Simple tracking
tracker = ProgressTracker("Migration", total_steps=10)
for i in range(10):
    tracker.update(f"Processing item {i+1}")
    # ... do work ...
tracker.complete()

# Multi-step tracking
steps = ["Validate", "Backup", "Migrate", "Verify"]
tracker = MultiStepProgressTracker(steps)

tracker.start_step("Validate")
# ... validation ...
tracker.complete_step("Validate")

tracker.start_step("Backup")
# ... backup ...
tracker.complete_step("Backup")

tracker.display_summary()

# Wrap function
result = run_with_progress(
    my_function,
    "My Operation",
    arg1, arg2
)
```

### 10. Multi-Bench (`multi_bench.py`)

**Purpose**: Multi-bench environment management

**Key Functions**:
```python
def detect_available_benches() -> list:
    """
    Detect all benches on system
    
    Search locations:
    - /home/*/frappe-bench
    - /home/*/*-bench
    - Common bench paths
    
    Returns:
        [
            {
                "path": "/path/to/bench",
                "name": "bench-name",
                "sites": [...],
                "apps": [...]
            }
        ]
    """

def compare_benches(bench1: str, bench2: str) -> dict:
    """
    Compare two benches
    
    Compares:
    - Frappe versions
    - App lists
    - Python versions
    - Node versions
    
    Returns:
        {
            "bench1": {...},
            "bench2": {...},
            "differences": [...]
        }
    """

def list_bench_inventory() -> dict:
    """
    Full bench inventory
    
    Returns:
        {
            "benches": [...],
            "apps": {...},
            "sites": {...}
        }
    """
```

---

## 🔧 API Reference

### Command-Line Interface

All commands follow the pattern:
```bash
bench --site <site-name> migrate-app <command> [arguments] [options]
```

#### Complete Command List (23 Commands)

##### 1. Interactive Commands
```bash
# Launch interactive wizard
bench --site mysite migrate-app interactive
```

##### 2. Analysis Commands
```bash
# Comprehensive app analysis
bench --site mysite migrate-app analyze <app-name>

# Classify doctypes
bench --site mysite migrate-app classify-doctypes <app-name>

# Detect orphans
bench --site mysite migrate-app analyze-orphans

# Pre-migration validation
bench --site mysite migrate-app validate-migration <app-name>
```

##### 3. Migration Commands
```bash
# Migrate app modules
bench --site mysite migrate-app migrate <source> <target> [--modules="Module1,Module2"]

# Clone app locally
bench --site mysite migrate-app clone-app-local <app-name> [--target-bench=/path]
```

##### 4. Data Quality Commands
```bash
# Fix orphan doctypes
bench --site mysite migrate-app fix-orphans <app-name>

# Restore missing doctype files
bench --site mysite migrate-app restore-missing <app-name>

# Fix app=None doctypes
bench --site mysite migrate-app fix-app-none <app-name>

# Fix all references
bench --site mysite migrate-app fix-all-references <app-name>

# Verify data integrity
bench --site mysite migrate-app verify-integrity
```

##### 5. Database Commands
```bash
# Fix database schema
bench --site mysite migrate-app fix-database-schema

# Complete ERPNext installation
bench --site mysite migrate-app complete-erpnext-install

# Fix tree doctypes
bench --site mysite migrate-app fix-tree-doctypes

# Run diagnostics
bench --site mysite migrate-app db-diagnostics
```

##### 6. Multi-Bench Commands
```bash
# Multi-bench analysis
bench --site mysite migrate-app multi-bench-analysis

# List available benches
bench --site mysite migrate-app list-benches

# List apps in bench
bench --site mysite migrate-app bench-apps <bench-name>

# Bench health check
bench --site mysite migrate-app bench-health
```

##### 7. Reporting Commands
```bash
# Show touched tables
bench --site mysite migrate-app touched-tables

# Risk assessment
bench --site mysite migrate-app risk-assessment <doctype>
```

### Python API

#### Direct Function Calls

```python
# Import from console or script
import frappe
from app_migrator.commands import (
    # Analysis
    analyze_app_comprehensive,
    classify_all_doctypes,
    analyze_orphans,
    
    # Migration
    migrate_app_modules,
    migrate_specific_doctypes,
    
    # Data Quality
    fix_orphan_doctypes,
    restore_missing_doctypes,
    verify_data_integrity,
    
    # Database
    verify_database_schema,
    fix_database_schema,
    run_database_diagnostics,
    
    # Session & Progress
    SessionManager,
    ProgressTracker,
)

# Example usage
frappe.init(site="mysite")
frappe.connect()

# Analyze app
result = analyze_app_comprehensive("custom_app")
print(result)

# Create session
session = SessionManager("my_migration")
session.update_progress("analyze", "started")
session.save()
```

---

## 🎯 Usage Patterns

### Pattern 1: Complete Migration Workflow

```python
"""Complete migration from old_app to new_app"""

from app_migrator.commands import (
    SessionManager,
    ProgressTracker,
    analyze_app_comprehensive,
    classify_all_doctypes,
    validate_migration_readiness,
    migrate_app_modules,
    verify_data_integrity
)

def complete_migration(source_app, target_app):
    # 1. Create session
    session = SessionManager(f"migrate_{source_app}_to_{target_app}")
    tracker = ProgressTracker("Complete Migration", total_steps=6)
    
    # 2. Analyze source app
    tracker.update("Analyzing source app...")
    analysis = analyze_app_comprehensive(source_app)
    session.update_progress("analyze", "completed", analysis)
    
    # 3. Classify doctypes
    tracker.update("Classifying doctypes...")
    classification = classify_all_doctypes(source_app)
    session.update_progress("classify", "completed", classification)
    
    # 4. Validate readiness
    tracker.update("Validating migration readiness...")
    validation = validate_migration_readiness(source_app, target_app)
    if not validation["ready"]:
        tracker.fail(f"Not ready: {validation['issues']}")
        return False
    session.update_progress("validate", "completed", validation)
    
    # 5. Execute migration
    tracker.update("Executing migration...")
    migration = migrate_app_modules(source_app, target_app)
    session.update_progress("migrate", "completed", migration)
    
    # 6. Verify integrity
    tracker.update("Verifying data integrity...")
    integrity = verify_data_integrity(target_app)
    session.update_progress("verify", "completed", {"passed": integrity})
    
    # 7. Complete
    tracker.complete()
    session.save()
    
    print(f"✅ Migration completed successfully!")
    print(f"Migrated: {migration['migrated']}")
    return True

# Execute
complete_migration("old_app", "new_app")
```

### Pattern 2: Data Quality Audit

```python
"""Comprehensive data quality audit"""

from app_migrator.commands import (
    analyze_orphans,
    classify_all_doctypes,
    verify_data_integrity,
    fix_orphan_doctypes,
    restore_missing_doctypes
)

def data_quality_audit(app_name):
    report = {
        "app": app_name,
        "timestamp": frappe.utils.now(),
        "issues": [],
        "fixed": []
    }
    
    # 1. Check for orphans
    orphans = analyze_orphans()
    app_orphans = [o for o in orphans["orphans"] if o.get("app") == app_name]
    if app_orphans:
        report["issues"].append(f"Found {len(app_orphans)} orphan doctypes")
        
        # Fix orphans
        fixed = fix_orphan_doctypes(app_name)
        report["fixed"].append(f"Fixed {fixed['total_fixed']} orphans")
    
    # 2. Check for missing files
    classification = classify_all_doctypes(app_name)
    
    # 3. Verify integrity
    integrity_ok = verify_data_integrity(app_name)
    if not integrity_ok:
        report["issues"].append("Data integrity check failed")
        
        # Restore missing files
        restored = restore_missing_doctypes(app_name)
        report["fixed"].append(f"Restored {restored['total_restored']} files")
    
    # 4. Generate summary
    report["summary"] = {
        "total_issues": len(report["issues"]),
        "total_fixed": len(report["fixed"]),
        "status": "clean" if not report["issues"] else "issues_found"
    }
    
    return report

# Execute
audit = data_quality_audit("custom_app")
print(frappe.as_json(audit, indent=2))
```

### Pattern 3: Bench-Wide Analysis

```python
"""Analyze all benches and apps"""

from app_migrator.commands import (
    detect_available_benches,
    analyze_bench_health,
    analyze_app_comprehensive
)

def bench_ecosystem_report():
    report = {
        "timestamp": frappe.utils.now(),
        "benches": [],
        "apps": {},
        "summary": {}
    }
    
    # 1. Detect benches
    benches = detect_available_benches()
    report["summary"]["total_benches"] = len(benches)
    
    # 2. Analyze each bench
    for bench in benches:
        bench_data = {
            "path": bench["path"],
            "name": bench["name"],
            "health": analyze_bench_health(),
            "apps": []
        }
        
        # 3. Analyze apps in bench
        for app in bench["apps"]:
            app_analysis = analyze_app_comprehensive(app)
            bench_data["apps"].append(app_analysis)
            
            # Track apps across benches
            if app not in report["apps"]:
                report["apps"][app] = []
            report["apps"][app].append(bench["name"])
        
        report["benches"].append(bench_data)
    
    # 4. Generate insights
    report["summary"]["total_apps"] = len(report["apps"])
    report["summary"]["common_apps"] = [
        app for app, benches in report["apps"].items()
        if len(benches) > 1
    ]
    
    return report

# Execute
ecosystem = bench_ecosystem_report()
print(frappe.as_json(ecosystem, indent=2))
```

### Pattern 4: Interactive Classification

```python
"""Interactive doctype classification and filtering"""

from app_migrator.commands import (
    classify_all_doctypes,
    get_doctype_classification
)

def interactive_classification(app_name):
    # Get all classifications
    all_classifications = classify_all_doctypes(app_name)
    
    # Display summary
    print("\n" + "="*60)
    print(f"DocType Classification Report: {app_name}")
    print("="*60)
    print(f"Total: {all_classifications['summary']['total']}")
    print(f"Standard: {all_classifications['summary']['standard']}")
    print(f"Customized: {all_classifications['summary']['customized']}")
    print(f"Custom: {all_classifications['summary']['custom']}")
    print(f"Orphan: {all_classifications['summary']['orphan']}")
    print("="*60)
    
    # Interactive filtering
    while True:
        print("\nFilter by:")
        print("1. Standard")
        print("2. Customized")
        print("3. Custom")
        print("4. Orphan")
        print("5. View specific doctype")
        print("6. Exit")
        
        choice = input("\nYour choice: ")
        
        if choice == "1":
            display_doctypes(all_classifications['standard'], "Standard")
        elif choice == "2":
            display_doctypes(all_classifications['customized'], "Customized")
        elif choice == "3":
            display_doctypes(all_classifications['custom'], "Custom")
        elif choice == "4":
            display_doctypes(all_classifications['orphan'], "Orphan")
        elif choice == "5":
            doctype = input("Enter doctype name: ")
            details = get_doctype_classification(doctype)
            print(frappe.as_json(details, indent=2))
        elif choice == "6":
            break

def display_doctypes(doctypes, category):
    print(f"\n{category} DocTypes ({len(doctypes)}):")
    print("-" * 60)
    for dt in doctypes:
        print(f"  • {dt}")

# Execute
interactive_classification("erpnext")
```

### Pattern 5: Automated Maintenance

```python
"""Automated maintenance script"""

from app_migrator.commands import (
    run_database_diagnostics,
    fix_database_schema,
    fix_tree_doctypes,
    verify_data_integrity,
    SessionManager
)

def automated_maintenance(app_name=None):
    session = SessionManager(f"maintenance_{frappe.utils.now()}")
    
    maintenance_report = {
        "timestamp": frappe.utils.now(),
        "tasks": [],
        "issues_found": 0,
        "issues_fixed": 0
    }
    
    # Task 1: Database diagnostics
    print("Running database diagnostics...")
    diagnostics = run_database_diagnostics(app_name)
    maintenance_report["tasks"].append({
        "name": "Database Diagnostics",
        "status": "completed",
        "issues": len(diagnostics.get("issues", []))
    })
    maintenance_report["issues_found"] += len(diagnostics.get("issues", []))
    
    # Task 2: Fix schema if needed
    if diagnostics.get("missing_tables"):
        print("Fixing database schema...")
        schema_fix = fix_database_schema(app_name)
        maintenance_report["tasks"].append({
            "name": "Fix Database Schema",
            "status": "completed",
            "fixed": schema_fix["total_created"]
        })
        maintenance_report["issues_fixed"] += schema_fix["total_created"]
    
    # Task 3: Fix tree doctypes
    print("Fixing tree doctypes...")
    tree_fix = fix_tree_doctypes(app_name)
    maintenance_report["tasks"].append({
        "name": "Fix Tree DocTypes",
        "status": "completed",
        "fixed": len(tree_fix.get("fixed", []))
    })
    maintenance_report["issues_fixed"] += len(tree_fix.get("fixed", []))
    
    # Task 4: Verify integrity
    print("Verifying data integrity...")
    integrity_ok = verify_data_integrity(app_name)
    maintenance_report["tasks"].append({
        "name": "Data Integrity Check",
        "status": "passed" if integrity_ok else "failed"
    })
    
    # Save session
    session.update_progress("maintenance", "completed", maintenance_report)
    session.save()
    
    # Print summary
    print("\n" + "="*60)
    print("Maintenance Summary")
    print("="*60)
    print(f"Tasks completed: {len(maintenance_report['tasks'])}")
    print(f"Issues found: {maintenance_report['issues_found']}")
    print(f"Issues fixed: {maintenance_report['issues_fixed']}")
    print("="*60)
    
    return maintenance_report

# Schedule with cron
# 0 2 * * * cd /path/to/bench && bench --site mysite execute app_migrator.commands.automated_maintenance
```

---

## 🔗 Integration Guidelines

### Integrating with Existing Apps

#### 1. Import App Migrator in Your App

```python
# In your custom app's code
try:
    from app_migrator.commands import (
        analyze_app_comprehensive,
        classify_all_doctypes,
        SessionManager
    )
    HAS_APP_MIGRATOR = True
except ImportError:
    HAS_APP_MIGRATOR = False

# Use conditionally
if HAS_APP_MIGRATOR:
    analysis = analyze_app_comprehensive("my_app")
else:
    frappe.throw("App Migrator is required for this feature")
```

#### 2. Create Custom Commands

```python
# In your app's commands.py
import click
from app_migrator.commands import migrate_app_modules

@click.command('custom-migrate')
@click.argument('target-app')
def custom_migrate_command(target_app):
    """Custom migration command"""
    
    # Use App Migrator functions
    result = migrate_app_modules("my_app", target_app)
    
    # Custom post-processing
    if result["status"] == "success":
        # Your custom logic
        pass

# Register with bench
commands = [custom_migrate_command]
```

#### 3. Extend Classification Logic

```python
# Add custom classification rules
from app_migrator.commands.doctype_classifier import get_doctype_classification

def get_enhanced_classification(doctype_name):
    # Get base classification
    base = get_doctype_classification(doctype_name)
    
    # Add custom logic
    doc = frappe.get_doc("DocType", doctype_name)
    
    # Check for organization-specific patterns
    if doc.name.startswith("ACME_"):
        base["organization"] = "ACME"
        base["custom_category"] = "organization_specific"
    
    # Check for integration doctypes
    if "integration" in doc.module.lower():
        base["custom_category"] = "integration"
    
    return base
```

### Creating Custom Workflows

#### Workflow Template

```python
from app_migrator.commands import (
    SessionManager,
    ProgressTracker,
    # Import other needed functions
)

def custom_workflow(app_name, **options):
    """Template for custom workflows"""
    
    # 1. Setup
    session = SessionManager(f"custom_workflow_{frappe.utils.now()}")
    tracker = ProgressTracker("Custom Workflow", total_steps=5)
    
    try:
        # 2. Step 1
        tracker.update("Step 1: Description")
        # Your logic
        session.update_progress("step1", "completed")
        
        # 3. Step 2
        tracker.update("Step 2: Description")
        # Your logic
        session.update_progress("step2", "completed")
        
        # ... more steps ...
        
        # N. Complete
        tracker.complete()
        session.save()
        
        return {"status": "success", "data": {...}}
        
    except Exception as e:
        tracker.fail(str(e))
        session.update_progress("error", "failed", {"error": str(e)})
        session.save()
        raise
```

### Extending the Wizard

```python
# Add custom steps to interactive wizard
from app_migrator.commands.enhanced_interactive_wizard import (
    interactive_migration_wizard
)

def custom_interactive_wizard():
    """Extended wizard with custom steps"""
    
    # Run standard wizard
    print("Running standard wizard...")
    result = interactive_migration_wizard()
    
    # Add custom steps
    print("\n" + "="*60)
    print("Custom Organization Steps")
    print("="*60)
    
    # Custom step 1: Organization rules
    print("\n1. Applying organization rules...")
    # Your logic
    
    # Custom step 2: Integration setup
    print("\n2. Setting up integrations...")
    # Your logic
    
    # Custom step 3: Post-migration tasks
    print("\n3. Running post-migration tasks...")
    # Your logic
    
    print("\n✅ Custom workflow completed!")
    return result
```

---

## 💡 Code Examples

### Example 1: Simple Migration Script

```python
#!/usr/bin/env python3
"""
Simple migration script
Usage: python simple_migrate.py source_app target_app
"""

import sys
import frappe
from app_migrator.commands import (
    migrate_app_modules,
    verify_data_integrity
)

def main():
    if len(sys.argv) != 3:
        print("Usage: python simple_migrate.py <source_app> <target_app>")
        sys.exit(1)
    
    source = sys.argv[1]
    target = sys.argv[2]
    
    # Initialize Frappe
    frappe.init(site="mysite")
    frappe.connect()
    
    # Migrate
    print(f"Migrating from {source} to {target}...")
    result = migrate_app_modules(source, target)
    
    # Verify
    print("Verifying integrity...")
    integrity_ok = verify_data_integrity(target)
    
    # Report
    if result["status"] == "success" and integrity_ok:
        print(f"✅ Migration successful!")
        print(f"Migrated modules: {', '.join(result['migrated'])}")
    else:
        print("❌ Migration failed!")
        print(f"Errors: {result.get('errors', [])}")

if __name__ == "__main__":
    main()
```

### Example 2: Batch Processing

```python
"""Process multiple apps in batch"""

from app_migrator.commands import (
    analyze_app_comprehensive,
    classify_all_doctypes,
    fix_orphan_doctypes
)

def batch_process_apps(app_list):
    """Process multiple apps"""
    
    results = {}
    
    for app_name in app_list:
        print(f"\nProcessing: {app_name}")
        print("-" * 60)
        
        try:
            # Analyze
            print("1. Analyzing...")
            analysis = analyze_app_comprehensive(app_name)
            
            # Classify
            print("2. Classifying...")
            classification = classify_all_doctypes(app_name)
            
            # Fix orphans if any
            if classification['summary']['orphan'] > 0:
                print(f"3. Fixing {classification['summary']['orphan']} orphans...")
                fix_result = fix_orphan_doctypes(app_name)
            else:
                fix_result = {"total_fixed": 0}
            
            # Store results
            results[app_name] = {
                "status": "success",
                "doctypes": classification['summary']['total'],
                "orphans_fixed": fix_result['total_fixed']
            }
            
            print(f"✅ Completed: {app_name}")
            
        except Exception as e:
            print(f"❌ Failed: {app_name} - {str(e)}")
            results[app_name] = {
                "status": "failed",
                "error": str(e)
            }
    
    return results

# Execute
apps = ["custom_app1", "custom_app2", "custom_app3"]
results = batch_process_apps(apps)

# Print summary
print("\n" + "="*60)
print("Batch Processing Summary")
print("="*60)
for app, result in results.items():
    print(f"{app}: {result['status']}")
```

### Example 3: Monitoring Long Operations

```python
"""Monitor long-running operations"""

import time
from app_migrator.commands import (
    SessionManager,
    ProgressTracker
)

def monitored_operation(app_name):
    """Example of monitored operation"""
    
    # Setup
    session = SessionManager(f"monitor_{app_name}")
    tracker = ProgressTracker("Processing", total_steps=100)
    
    # Simulate long operation
    for i in range(100):
        # Update progress
        tracker.update(f"Processing item {i+1}")
        session.update_progress("process", "in_progress", {
            "current": i+1,
            "total": 100,
            "percentage": (i+1) / 100 * 100
        })
        
        # Save every 10 steps
        if (i+1) % 10 == 0:
            session.save()
        
        # Simulate work
        time.sleep(0.1)
    
    # Complete
    tracker.complete()
    session.update_progress("process", "completed")
    session.save()
    
    return {"status": "success", "processed": 100}

# Execute
result = monitored_operation("test_app")

# Check saved session
loaded = SessionManager.load_session(f"monitor_test_app")
loaded.display_status()
```

### Example 4: Custom Reporting

```python
"""Generate custom reports"""

import frappe
from app_migrator.commands import (
    analyze_app_comprehensive,
    classify_all_doctypes,
    analyze_orphans
)

def generate_migration_report(app_name):
    """Generate comprehensive migration report"""
    
    report = {
        "app": app_name,
        "generated_at": frappe.utils.now(),
        "analysis": {},
        "classification": {},
        "recommendations": []
    }
    
    # 1. Comprehensive analysis
    report["analysis"] = analyze_app_comprehensive(app_name)
    
    # 2. Classification
    report["classification"] = classify_all_doctypes(app_name)
    
    # 3. Orphan analysis
    orphans = analyze_orphans()
    app_orphans = [o for o in orphans["orphans"] if o.get("app") == app_name]
    report["orphans"] = app_orphans
    
    # 4. Generate recommendations
    if app_orphans:
        report["recommendations"].append({
            "priority": "high",
            "action": "fix_orphans",
            "description": f"Fix {len(app_orphans)} orphan doctypes"
        })
    
    if report["classification"]["summary"]["customized"] > 10:
        report["recommendations"].append({
            "priority": "medium",
            "action": "review_customizations",
            "description": "Review heavy customizations"
        })
    
    # 5. Calculate migration complexity
    complexity_score = (
        report["classification"]["summary"]["customized"] * 2 +
        report["classification"]["summary"]["custom"] * 3 +
        len(app_orphans) * 5
    )
    
    report["migration_complexity"] = {
        "score": complexity_score,
        "level": (
            "low" if complexity_score < 20 else
            "medium" if complexity_score < 50 else
            "high"
        )
    }
    
    # 6. Save report
    filename = f"/tmp/migration_report_{app_name}_{frappe.utils.now()}.json"
    with open(filename, 'w') as f:
        f.write(frappe.as_json(report, indent=2))
    
    print(f"Report saved to: {filename}")
    return report

# Generate report
report = generate_migration_report("custom_app")

# Print summary
print("\n" + "="*60)
print(f"Migration Report: {report['app']}")
print("="*60)
print(f"Total DocTypes: {report['classification']['summary']['total']}")
print(f"Orphans: {len(report['orphans'])}")
print(f"Complexity: {report['migration_complexity']['level']}")
print(f"Recommendations: {len(report['recommendations'])}")
print("="*60)
```

---

## 🔍 Troubleshooting

### Common Issues & Solutions

#### Issue 1: Connection Lost During Migration

**Problem**: Database connection lost during long-running migration

**Solution**:
```python
from app_migrator.commands import with_session_management

@with_session_management
def my_migration():
    # Decorator handles auto-reconnect
    pass

# Or manually
from app_migrator.commands import ensure_frappe_connection

def my_function():
    ensure_frappe_connection()
    # Your code
```

#### Issue 2: Orphan Doctypes Not Fixing

**Problem**: Orphan doctypes persist after running fix command

**Diagnosis**:
```python
from app_migrator.commands import (
    analyze_orphans,
    get_doctype_classification
)

# Check specific orphan
orphans = analyze_orphans()
for orphan in orphans["orphans"]:
    details = get_doctype_classification(orphan["doctype"])
    print(frappe.as_json(details, indent=2))
```

**Solution**:
```python
# Manual fix
import frappe

doctype_name = "Orphan DocType"
correct_app = "target_app"
correct_module = "Target Module"

# Update doctype
doc = frappe.get_doc("DocType", doctype_name)
doc.app = correct_app
doc.module = correct_module
doc.save()

print(f"✅ Fixed: {doctype_name}")
```

#### Issue 3: Missing Tables After Migration

**Problem**: Doctypes migrated but tables not created

**Solution**:
```python
from app_migrator.commands import (
    verify_database_schema,
    fix_database_schema
)

# 1. Verify
result = verify_database_schema("migrated_app")
print(f"Missing tables: {result['missing_tables']}")

# 2. Fix
if result["missing_tables"]:
    fix_result = fix_database_schema("migrated_app")
    print(f"Created {fix_result['total_created']} tables")

# 3. Verify again
result = verify_database_schema("migrated_app")
print(f"Status: {result['status']}")
```

#### Issue 4: Permission Denied Errors

**Problem**: Permission errors during file operations

**Diagnosis**:
```bash
# Check permissions
ls -la /path/to/frappe-bench/apps/

# Check ownership
ls -la /path/to/frappe-bench/apps/target_app/
```

**Solution**:
```bash
# Fix permissions
cd /path/to/frappe-bench
sudo chown -R frappe:frappe apps/target_app/
sudo chmod -R 755 apps/target_app/

# Or run as correct user
sudo -u frappe bench --site mysite migrate-app migrate source target
```

#### Issue 5: Session Files Accumulating

**Problem**: Old session files filling disk space

**Solution**:
```python
from app_migrator.commands.session_manager import (
    list_sessions,
    delete_old_sessions
)

# List sessions
sessions = list_sessions()
print(f"Total sessions: {len(sessions)}")

# Delete old sessions (older than 30 days)
deleted = delete_old_sessions(days=30)
print(f"Deleted {deleted} old sessions")

# Or manually
import os
import glob
import time

session_dir = "/tmp/app_migrator_sessions"
cutoff = time.time() - (30 * 24 * 60 * 60)  # 30 days

for session_file in glob.glob(f"{session_dir}/*.json"):
    if os.path.getmtime(session_file) < cutoff:
        os.remove(session_file)
        print(f"Deleted: {session_file}")
```

### Debugging Tips

#### Enable Debug Logging

```python
# In site_config.json
{
    "logging": 2,
    "developer_mode": 1,
    "app_migrator": {
        "logging": {
            "level": "DEBUG"
        }
    }
}
```

#### Use Frappe Console for Testing

```bash
bench --site mysite console
```

```python
# In console
import frappe
frappe.set_user("Administrator")

# Test function
from app_migrator.commands import analyze_app_comprehensive
result = analyze_app_comprehensive("test_app")
print(frappe.as_json(result, indent=2))
```

#### Check Logs

```bash
# Worker logs
tail -f logs/worker.log

# Web logs
tail -f logs/web.log

# Custom app migrator logs
tail -f /var/log/frappe/app_migrator.log

# Filter for errors
grep -i error logs/*.log
```

---

## ⚡ Performance Optimization

### Best Practices

#### 1. Use Batch Operations

```python
# Bad: Process one at a time
for doctype in doctypes:
    classify_doctype(doctype)  # Multiple DB queries

# Good: Batch process
from app_migrator.commands import classify_all_doctypes
result = classify_all_doctypes("app_name")  # Single optimized query
```

#### 2. Leverage Session Management

```python
# Prevents connection overhead
from app_migrator.commands import with_session_management

@with_session_management
def process_large_dataset():
    # Connection maintained throughout
    for item in large_dataset:
        process(item)
```

#### 3. Use Progress Tracking Wisely

```python
# Bad: Update every iteration
for i in range(10000):
    tracker.update(f"Processing {i}")  # Too frequent

# Good: Update periodically
for i in range(10000):
    if i % 100 == 0:  # Update every 100 items
        tracker.update(f"Processed {i}/10000")
```

#### 4. Optimize Database Queries

```python
# Bad: Multiple queries
for doctype in doctypes:
    doc = frappe.get_doc("DocType", doctype)  # N queries

# Good: Single query
all_docs = frappe.get_all("DocType",
    filters={"app": "my_app"},
    fields=["name", "module", "custom"]
)  # 1 query
```

### Performance Monitoring

```python
import time

def monitored_function():
    start = time.time()
    
    # Your operation
    result = some_operation()
    
    elapsed = time.time() - start
    print(f"Operation took {elapsed:.2f} seconds")
    
    return result
```

---

## 📚 Version History

### v5.0.0 (October 11, 2025) - Current

**What's New**:
- ✅ Unified V2 + V4 architecture
- ✅ Enhanced classification system
- ✅ Interactive migration wizard
- ✅ 23 specialized commands
- ✅ 12 production-ready modules
- ✅ Comprehensive documentation

**Improvements**:
- Better error handling
- Enhanced progress tracking
- Improved session management
- More robust validation

**Breaking Changes**:
- None! Fully backward compatible

### v4.0.0 (Previous)

**Features**:
- Class-based session management
- Multi-bench support
- Enhanced analysis tools
- Local bench migration

### v2.0.0 (Legacy)

**Features**:
- Core migration functions
- Data quality tools
- Database schema operations
- Decorator-based session management

---

## 🤝 Contributing

### For AI Agents

When contributing or extending App Migrator:

1. **Understand the Architecture**: Study the modular design
2. **Follow Patterns**: Use existing decorators and classes
3. **Add Documentation**: Include docstrings and examples
4. **Test Thoroughly**: Validate with real Frappe sites
5. **Maintain Compatibility**: Ensure backward compatibility

### Code Style

```python
def example_function(param1: str, param2: int = None) -> dict:
    """
    Brief description
    
    Detailed description of what the function does,
    how it works, and any important notes.
    
    Args:
        param1: Description of param1
        param2: Description of param2 (optional)
    
    Returns:
        dict: Description of return value
        {
            "key1": "description",
            "key2": "description"
        }
    
    Raises:
        ValueError: When param1 is invalid
        frappe.ValidationError: When validation fails
    
    Example:
        >>> result = example_function("value", 123)
        >>> print(result["key1"])
    """
    # Implementation
    pass
```

---

## 📞 Support

### Getting Help

- **Documentation**: Check USER_GUIDE.md
- **GitHub Issues**: https://github.com/rogerboy38/app_migrator/issues
- **Gist**: https://gist.github.com/rogerboy38

### Reporting Issues

Include:
1. Frappe/ERPNext version
2. App Migrator version (5.0.0)
3. Command that failed
4. Complete error traceback
5. Steps to reproduce

---

## 📝 Quick Reference Card

### Most Used Commands
```bash
# Analysis
bench --site site analyze app
bench --site site classify-doctypes app

# Migration
bench --site site migrate-app migrate source target

# Data Quality
bench --site site fix-orphans app
bench --site site verify-integrity

# Database
bench --site site fix-database-schema
bench --site site db-diagnostics
```

### Most Used Functions
```python
from app_migrator.commands import (
    analyze_app_comprehensive,
    classify_all_doctypes,
    migrate_app_modules,
    fix_orphan_doctypes,
    verify_database_schema,
    SessionManager,
    ProgressTracker
)
```

### Key Patterns
```python
# Session Management
session = SessionManager("name")
session.update_progress("step", "status")
session.save()

# Progress Tracking
tracker = ProgressTracker("op", total=10)
tracker.update("message")
tracker.complete()

# Decorator Usage
@with_session_management
def my_function():
    pass
```

---

**Document Version**: 1.0.0  
**Last Updated**: October 11, 2025  
**Maintained By**: MiniMax Agent  
**For**: AI Agents & Developers

---

**End of Technical Specification**

*This document is maintained in the public gist at https://gist.github.com/rogerboy38 for easy access by AI agents and developers.*
