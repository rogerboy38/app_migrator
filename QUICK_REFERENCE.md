# App Migrator V5.0.0 - Quick Reference Guide

## Module Overview

| Module | Size | Source | Description |
|--------|------|--------|-------------|
| `__init__.py` | 3KB | New | Module initialization & exports |
| `enhanced_interactive_wizard.py` | 16KB | V2+V4 | Interactive migration wizard |
| `database_schema.py` | 14KB | V2 | Schema verification & fixing |
| `data_quality.py` | 19KB | V2 | Orphan fixing, restoration |
| `session_manager.py` | 14KB | V2+V4 | Session & connection management |
| `migration_engine.py` | 18KB | V2+V4 | Core migration functions |
| `analysis_tools.py` | 14KB | V2+V4 | Comprehensive analysis |
| `progress_tracker.py` | 9KB | V4 | Progress tracking |
| `multi_bench.py` | 3KB | V4 | Multi-bench operations |
| `database_intel.py` | 2KB | V4 | Database intelligence |
| `test_precise_apps.py` | 2KB | V4 | App testing |
| `doctype_classifier.py` | 12KB | Existing | Classification system |

**Total: 12 modules, 145KB**

---

## Quick Start Commands

### 1. Interactive Wizard
```python
from app_migrator.commands import interactive_migration_wizard
interactive_migration_wizard()
```

### 2. Analyze App
```python
from app_migrator.commands import analyze_app_comprehensive
analyze_app_comprehensive("my_app")
```

### 3. Fix Data Quality Issues
```python
from app_migrator.commands import (
    fix_orphan_doctypes,
    restore_missing_doctypes,
    fix_app_none_doctypes
)

fix_orphan_doctypes("my_app")
restore_missing_doctypes("my_app")
fix_app_none_doctypes("my_app")
```

### 4. Verify Database Schema
```python
from app_migrator.commands import verify_database_schema, fix_database_schema

verify_database_schema("my_app")
fix_database_schema("my_app")
```

### 5. Session Management
```python
from app_migrator.commands import SessionManager

session = SessionManager(name="migration_2025")
session.update_progress("analyze", "started")
session.update_progress("analyze", "completed")
session.display_status()
```

### 6. Migrate Modules
```python
from app_migrator.commands import migrate_app_modules

migrate_app_modules("source_app", "target_app")
migrate_app_modules("source_app", "target_app", modules="Module1,Module2")
```

### 7. Classification
```python
from app_migrator.commands import (
    get_doctype_classification,
    generate_migration_risk_assessment
)

classification = get_doctype_classification("Customer")
risk = generate_migration_risk_assessment("Customer")
```

---

## Workflow Example

```python
# Complete migration workflow
from app_migrator.commands import (
    SessionManager,
    analyze_app_comprehensive,
    verify_data_integrity,
    fix_orphan_doctypes,
    migrate_app_modules,
    ProgressTracker
)

# 1. Create session
session = SessionManager(name="my_migration")

# 2. Analyze source app
session.update_progress("analysis", "started")
results = analyze_app_comprehensive("source_app")
session.update_progress("analysis", "completed")

# 3. Verify data integrity
session.update_progress("verification", "started")
integrity_ok = verify_data_integrity("source_app")
session.update_progress("verification", "completed")

# 4. Fix issues
if not integrity_ok:
    session.update_progress("fixing", "started")
    fix_orphan_doctypes("source_app")
    session.update_progress("fixing", "completed")

# 5. Execute migration
session.update_progress("migration", "started")
success = migrate_app_modules("source_app", "target_app")
session.update_progress("migration", "completed" if success else "failed")

# 6. Display results
session.display_status()
```

---

## Decorator Usage

### Session Management
```python
from app_migrator.commands import with_session_management

@with_session_management
def my_migration_function(source, target):
    # Function automatically has session reconnection
    pass
```

### Progress Tracking
```python
from app_migrator.commands import ProgressTracker

def migrate_with_progress(app_name):
    tracker = ProgressTracker(app_name, total_steps=4)
    
    tracker.update("Step 1")
    # ... do work ...
    
    tracker.update("Step 2")
    # ... do work ...
    
    tracker.complete()
```

---

## Common Patterns

### Pattern 1: Pre-Migration Check
```python
from app_migrator.commands import (
    analyze_app_comprehensive,
    verify_data_integrity,
    validate_migration_readiness
)

# Analyze
results = analyze_app_comprehensive("my_app")

# Verify integrity
integrity = verify_data_integrity("my_app")

# Validate readiness
ready, issues = validate_migration_readiness("source_app", "target_app")

if ready:
    print("Ready to migrate!")
else:
    print("Issues found:", issues)
```

### Pattern 2: Fix All Issues
```python
from app_migrator.commands import (
    fix_orphan_doctypes,
    restore_missing_doctypes,
    fix_app_none_doctypes,
    fix_database_schema
)

# Fix all data quality issues
fix_orphan_doctypes("my_app")
restore_missing_doctypes("my_app")
fix_app_none_doctypes("my_app")

# Fix schema issues
fix_database_schema("my_app")
```

### Pattern 3: Complete ERPNext Setup
```python
from app_migrator.commands import complete_erpnext_install

# Fix ERPNext installation issues
success = complete_erpnext_install()
```

---

## Status Codes

### DocType Status
- `standard` - Core doctype, not modified
- `customized` - Has Custom Fields or Property Setters
- `custom` - User-created (custom=1)
- `orphan` - app=None or wrong module

### Session Status
- `active` - Session in progress
- `completed` - Session finished successfully
- `failed` - Session encountered errors
- `paused` - Session temporarily stopped

### Operation Status
- `started` - Operation initiated
- `completed` - Operation finished successfully
- `failed` - Operation encountered errors

---

## Error Handling

All functions include comprehensive error handling:

```python
try:
    from app_migrator.commands import migrate_app_modules
    success = migrate_app_modules("source", "target")
    if not success:
        print("Migration failed, check logs")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
```

---

## Best Practices

1. **Always create a session** for long operations
2. **Verify integrity** before migration
3. **Use progress tracking** for user feedback
4. **Check validation** before executing
5. **Backup database** before any migration
6. **Test in staging** before production
7. **Review analysis** before proceeding
8. **Fix data quality** issues first

---

## Module Dependencies

```
enhanced_interactive_wizard
├── doctype_classifier (classification)
├── session_manager (connections)
└── analysis_tools (analysis)

migration_engine
├── session_manager (decorators)
└── progress_tracker (tracking)

data_quality
├── session_manager (connections)
└── doctype_classifier (detection)

database_schema
└── session_manager (connections)

analysis_tools
├── session_manager (connections)
└── doctype_classifier (classification)
```

---

## Version Information

- **Version**: 5.0.0
- **Created**: 2025-10-11
- **Python**: 3.8+
- **Frappe**: Compatible with v13+
- **Status**: Production Ready ✅

---

## Support

For issues or questions:
1. Check the detailed summary: `COMMAND_MODULES_SUMMARY.md`
2. Review implementation guide: `IMPLEMENTATION_GUIDE_V5.md`
3. Check module docstrings for detailed documentation

---

**Last Updated**: 2025-10-11
**Total Modules**: 12
**Total Size**: 145KB
**Status**: ✅ Complete
