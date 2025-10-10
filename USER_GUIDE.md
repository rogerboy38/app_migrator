# 📖 App Migrator v5.0.0 - Complete User Guide

> **Comprehensive guide to mastering App Migrator v5.0.0** - From basic concepts to advanced workflows

---

## 📋 Table of Contents

1. [Introduction](#-introduction)
2. [Getting Started](#-getting-started)
3. [Enhanced Features](#-enhanced-features)
4. [Command Reference](#-command-reference)
5. [Workflow Examples](#-workflow-examples)
6. [Troubleshooting](#-troubleshooting)
7. [Best Practices](#-best-practices)
8. [FAQ](#-faq)

---

## 🌟 Introduction

### What is App Migrator v5.0.0?

App Migrator v5.0.0 is the ultimate toolkit for managing Frappe/ERPNext app migrations. It combines powerful automation with intelligent analysis to help you:

- 🔄 **Migrate** apps between benches safely
- 🔍 **Analyze** app structure and dependencies
- 🧹 **Clean** data quality issues
- 🗄️ **Fix** database schema problems
- 📊 **Monitor** migration progress
- ✅ **Verify** data integrity

### Who Should Use This?

- **System Administrators** - Managing multiple Frappe installations
- **Developers** - Refactoring and reorganizing apps
- **Consultants** - Migrating client customizations
- **DevOps Teams** - Automating deployment workflows

### Prerequisites

Before using App Migrator, you should have:

- Basic understanding of Frappe framework
- Access to bench command line
- Appropriate user permissions
- Database backup (always!)

---

## 🚀 Getting Started

### Installation

#### Step 1: Get the App

```bash
# Navigate to your bench
cd /path/to/frappe-bench

# Get the app
bench get-app https://github.com/yourusername/app_migrator.git

# Or from local directory
bench get-app /path/to/app_migrator_v5
```

#### Step 2: Install on Site

```bash
# Install on your site
bench --site your-site install-app app_migrator

# Restart bench
bench restart
```

#### Step 3: Verify Installation

```bash
# Check if installed
bench --site your-site console
```

```python
# In Frappe console
import app_migrator
from app_migrator.commands import __version__

print(f"App Migrator version: {__version__}")
# Should output: App Migrator version: 5.0.0
```

### Your First Command

Let's start with something simple - analyzing an app:

```bash
# Analyze the 'erpnext' app
bench --site your-site migrate-app analyze erpnext
```

You should see comprehensive output including:
- Number of modules
- DocType counts and classifications
- Custom fields and property setters
- Dependencies and references
- File system validation
- Recommendations

---

## ✨ Enhanced Features

### 1. DocType Classification System 🏷️

App Migrator v5.0.0 introduces intelligent DocType classification that automatically categorizes doctypes into four types:

#### Classification Types

##### 🔵 Standard
- **Definition**: Core framework doctypes, unmodified
- **Characteristics**:
  - Part of frappe/erpnext core
  - No custom fields
  - No property setters
  - custom=0
- **Migration Risk**: ⭐ Low (Safe to skip)
- **Example**: User, Company, Item

##### 🟡 Customized
- **Definition**: Core doctypes with modifications
- **Characteristics**:
  - Standard doctype with custom fields
  - Or has property setters
  - custom=0 but modified
- **Migration Risk**: ⭐⭐ Medium (Review required)
- **Example**: Customer with custom fields

##### 🟢 Custom
- **Definition**: User-created doctypes
- **Characteristics**:
  - custom=1
  - Created by users/developers
  - Part of custom apps
- **Migration Risk**: ⭐⭐⭐ High (Must migrate)
- **Example**: Custom Leave Application

##### 🔴 Orphan
- **Definition**: Doctypes without proper app assignment
- **Characteristics**:
  - app=None
  - Wrong module assignment
  - Missing JSON files
- **Migration Risk**: ⭐⭐⭐⭐ Critical (Fix required)
- **Example**: Doctypes after improper deletion

#### Using Classification

```bash
# Classify all doctypes in an app
bench --site mysite migrate-app classify-doctypes custom_app

# Output shows:
# Standard: 45 doctypes
# Customized: 12 doctypes (with custom fields)
# Custom: 28 doctypes (user-created)
# Orphan: 3 doctypes (needs fixing)
```

```python
# In Python/console
from app_migrator.commands import get_doctype_classification

classification = get_doctype_classification("Customer")
print(f"Status: {classification['status']}")
print(f"Has Custom Fields: {classification['has_custom_fields']}")
print(f"Risk Level: {classification['risk_assessment']['risk_level']}")
```

### 2. Interactive Migration Wizard 🧙

The Enhanced Interactive Wizard guides you through migrations step-by-step:

#### Launching the Wizard

```bash
bench --site your-site migrate-app interactive
```

#### Wizard Flow

```
┌─────────────────────────────────────────────┐
│  Step 1: Site Selection                     │
│  - Lists available sites                    │
│  - Validates site existence                 │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Step 2: App Browsing                       │
│  - Shows installed apps                     │
│  - Displays app details                     │
│  - Allows app selection                     │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Step 3: Module Analysis                    │
│  - Lists modules in app                     │
│  - Classifies doctypes                      │
│  - Shows statistics                         │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Step 4: Status Filtering                   │
│  - Filter by Standard/Customized/etc        │
│  - Review selected doctypes                 │
│  - Confirm selection                        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Step 5: Migration Execution                │
│  - Pre-migration validation                 │
│  - Execute migration                        │
│  - Track progress                           │
│  - Display results                          │
└─────────────────────────────────────────────┘
```

#### Features

- ✅ **Intelligent Prompts** - Context-aware questions
- ✅ **Validation** - Checks at every step
- ✅ **Progress Tracking** - Visual feedback
- ✅ **Error Recovery** - Graceful error handling
- ✅ **Session Persistence** - Resume after interruption

### 3. Session Management 💾

Enhanced session management keeps track of your migration progress:

#### Creating a Session

```python
from app_migrator.commands import SessionManager

# Create a new session
session = SessionManager(name="migration_oct_2025")

# Update progress
session.update_progress("analysis", "started")
session.update_progress("analysis", "completed")

# Save session
session.save()

# Display status
session.display_status()
```

#### Session Features

- **Persistent Storage** - Saved to JSON files
- **Progress Tracking** - Monitor each step
- **Auto-Reconnect** - Handles connection drops
- **Resume Capability** - Continue after failures

#### Loading Existing Sessions

```python
# Load previous session
session = SessionManager.load_session("migration_oct_2025")

# Check what was completed
print(session.progress)

# Continue from where you left off
session.update_progress("migration", "started")
```

### 4. Progress Tracking 📊

Visual progress tracking for long-running operations:

#### Simple Progress Tracker

```python
from app_migrator.commands import ProgressTracker

tracker = ProgressTracker("MyApp", total_steps=5)

tracker.update("Analyzing modules...")
# Do work

tracker.update("Migrating doctypes...")
# Do work

tracker.complete()
```

#### Multi-Step Progress Tracker

```python
from app_migrator.commands import MultiStepProgressTracker

steps = ["Analyze", "Validate", "Backup", "Migrate", "Verify"]
tracker = MultiStepProgressTracker("Migration", steps)

for step in steps:
    tracker.start_step(step)
    # Do work
    tracker.complete_step(step)

tracker.display_summary()
```

---

## 📚 Command Reference

### Complete Command List (23 Commands)

#### 1. Interactive Commands

##### `interactive`
Launch the interactive migration wizard.

```bash
bench --site mysite migrate-app interactive
```

**Features**:
- Step-by-step guidance
- Site and app selection
- Module classification
- Status filtering
- Execution tracking

**When to Use**: First-time users, complex migrations

---

#### 2. Multi-Bench Commands

##### `multi-bench-analysis`
Analyze the entire bench ecosystem.

```bash
bench --site mysite migrate-app multi-bench-analysis
```

**Output**:
- Available benches
- Apps per bench
- Version comparisons
- Shared apps
- Recommendations

##### `list-benches`
List all available benches on the system.

```bash
bench --site mysite migrate-app list-benches
```

**Example Output**:
```
🏗️  AVAILABLE BENCHES:
   1. /home/frappe/frappe-bench
   2. /home/frappe/erpnext-bench
   3. /home/frappe/development-bench
```

##### `bench-apps <bench_name>`
List all apps in a specific bench.

```bash
bench --site mysite migrate-app bench-apps frappe-bench
```

**Example Output**:
```
📦 APPS IN frappe-bench:
   1. frappe (v14.0.0)
   2. erpnext (v14.0.0)
   3. custom_app (v1.0.0)
```

##### `bench-health`
Check the health status of current bench.

```bash
bench --site mysite migrate-app bench-health
```

**Checks**:
- Python dependencies
- Node modules
- Database connectivity
- File permissions
- Configuration validity

---

#### 3. Database Commands

##### `fix-database-schema`
Verify and fix database schema issues.

```bash
bench --site mysite migrate-app fix-database-schema
```

**What it Does**:
- Scans all doctypes
- Detects missing tables
- Creates missing tables
- Reports results

**Example Output**:
```
🗄️  DATABASE SCHEMA REPAIR
Scanning doctypes...
Found 5 missing tables:
  ✅ Created: tabCustom DocType 1
  ✅ Created: tabCustom DocType 2
  ...
✅ Schema repair completed!
```

##### `complete-erpnext-install`
Complete ERPNext installation and fix setup issues.

```bash
bench --site mysite migrate-app complete-erpnext-install
```

**What it Does**:
- Installs missing fixtures
- Creates default records
- Fixes tree doctypes
- Sets up configurations

**Use Case**: After manual ERPNext installation or migration

##### `fix-tree-doctypes`
Fix tree structure doctypes (lft, rgt, old_parent fields).

```bash
bench --site mysite migrate-app fix-tree-doctypes
```

**Fixes**:
- Missing lft/rgt fields
- Missing old_parent field
- Rebuilds tree structure
- Updates nested set values

**When to Use**: After tree doctype errors, before migration

##### `db-diagnostics`
Run comprehensive database diagnostics.

```bash
bench --site mysite migrate-app db-diagnostics
```

**Reports**:
- Orphan tables
- Missing tables
- Inconsistent data
- Performance issues
- Recommendations

---

#### 4. Analysis Commands

##### `analyze <app>`
Perform comprehensive app analysis.

```bash
bench --site mysite migrate-app analyze custom_app
```

**Analysis Includes**:
- Module count and structure
- DocType classifications
- Custom fields analysis
- Property setters
- Dependencies (requirements.txt, package.json)
- Cross-app references
- File system validation
- Size calculations

**Example Output**:
```
📊 APP ANALYSIS: custom_app
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Modules: 5
   - Custom Module 1
   - Custom Module 2
   ...

📄 DocTypes: 28 total
   🔵 Standard: 0
   🟡 Customized: 3
   🟢 Custom: 25
   🔴 Orphan: 0

📝 Custom Fields: 45 across 12 doctypes
🔧 Property Setters: 23 modifications

📦 Dependencies:
   - frappe
   - erpnext
   - requests==2.28.0

💾 Size: 2.5 MB

✅ RECOMMENDATIONS:
   1. Review customized doctypes before migration
   2. Test custom fields in target environment
   3. Backup before proceeding
```

##### `analyze-orphans`
Detect and list orphan doctypes.

```bash
bench --site mysite migrate-app analyze-orphans
```

**Detects**:
- Doctypes with app=None
- Doctypes in wrong modules
- Missing JSON files
- Inconsistent assignments

**Example Output**:
```
⚠️  ORPHAN DOCTYPES: 3

   - Custom Leave Type: app=None (should be: custom_hr)
   - Old Customer Form: wrong module
   - Deleted DocType: missing JSON file

💡 TIP: Use 'fix-orphans' to automatically fix these issues
```

##### `validate-migration <app>`
Pre-migration validation checks.

```bash
bench --site mysite migrate-app validate-migration custom_app
```

**Validates**:
- Source app exists
- Target app ready
- No circular dependencies
- Database schema valid
- File system permissions
- Sufficient disk space

**Example Output**:
```
✅ MIGRATION VALIDATION: custom_app
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Source app exists
✅ Modules accessible
✅ Database schema valid
✅ No orphan doctypes
✅ Permissions OK
✅ Disk space: 15GB available

READY TO MIGRATE! ✅
```

##### `classify-doctypes <app>`
Classify all doctypes in an app by status.

```bash
bench --site mysite migrate-app classify-doctypes erpnext
```

**Classifications**:
- Standard: Core, unmodified
- Customized: Core with modifications
- Custom: User-created
- Orphan: Needs fixing

**Example Output**:
```
📊 DOCTYPE CLASSIFICATION: erpnext
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔵 STANDARD (142 doctypes)
   Customer, Item, Sales Order, ...
   Risk: Low - Safe to skip

🟡 CUSTOMIZED (12 doctypes)
   Customer (3 custom fields)
   Item (5 custom fields)
   Sales Invoice (2 property setters)
   Risk: Medium - Review required

🟢 CUSTOM (0 doctypes)
   Risk: High - Must migrate

🔴 ORPHAN (0 doctypes)
   Risk: Critical - Fix required

SUMMARY:
   Total: 154 doctypes
   Migration Required: 12 doctypes
```

---

#### 5. Data Quality Commands

##### `fix-orphans <app>`
Fix orphaned doctypes in an app.

```bash
bench --site mysite migrate-app fix-orphans custom_app
```

**What it Does**:
1. Detects doctypes with app=None
2. Finds correct module assignment
3. Updates app field
4. Validates changes

**Example Output**:
```
🧹 FIXING ORPHAN DOCTYPES: custom_app
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Found 3 orphan doctypes:

   ✅ Custom Leave Type: app=None → custom_app
   ✅ Custom Attendance: app=None → custom_app
   ✅ Old Form: app=None → custom_app

✅ Fixed 3 orphan doctypes!
```

##### `restore-missing <app>`
Restore missing doctype JSON files.

```bash
bench --site mysite migrate-app restore-missing custom_app
```

**What it Does**:
1. Scans database for doctypes
2. Checks for JSON files
3. Generates missing files from database
4. Saves to correct module

**Use Case**: After accidental deletion, before migration

**Example Output**:
```
📁 RESTORING MISSING DOCTYPES: custom_app
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scanning database...
Found 2 doctypes without JSON files:

   ✅ Restored: Custom Leave Type
      Location: custom_app/custom_module/doctype/custom_leave_type/
   
   ✅ Restored: Custom Attendance
      Location: custom_app/custom_module/doctype/custom_attendance/

✅ Restored 2 doctype files!
```

##### `fix-app-none <app>`
Fix doctypes with app=None assignment.

```bash
bench --site mysite migrate-app fix-app-none custom_app
```

**Similar to fix-orphans but specifically targets app=None issues.**

##### `fix-all-references <app>`
Analyze and fix cross-app references.

```bash
bench --site mysite migrate-app fix-all-references custom_app
```

**Analyzes**:
- Link fields to other doctypes
- Table fields (child tables)
- Dynamic links
- Cross-app dependencies

**Example Output**:
```
🔗 ANALYZING REFERENCES: custom_app
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Link Fields (15 references):
   Custom Leave Type → Employee (erpnext)
   Custom Attendance → Employee (erpnext)
   ...

Table Fields (3 references):
   Custom Timesheet → Custom Timesheet Detail

Dynamic Links (2 references):
   Custom Document Link → various doctypes

⚠️  CROSS-APP DEPENDENCIES:
   - erpnext: 13 references
   - hrms: 2 references

💡 These references must be maintained after migration!
```

##### `verify-integrity`
Comprehensive data integrity verification.

```bash
bench --site mysite migrate-app verify-integrity
```

**Verifies**:
- All doctypes have valid schemas
- No orphan records
- All files exist
- Database consistency
- Reference integrity

**Example Output**:
```
✅ DATA INTEGRITY CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ All doctypes have valid schemas
✅ No orphan doctypes found
✅ All doctype files exist
✅ Database schema matches files
✅ All references are valid

INTEGRITY: 100% ✅
```

---

#### 6. Migration Commands

##### `migrate <source> <target>`
Migrate app modules from source to target.

```bash
# Migrate all modules
bench --site mysite migrate-app migrate source_app target_app

# Migrate specific modules
bench --site mysite migrate-app migrate source_app target_app --modules="Module1,Module2"
```

**Migration Process**:
1. **Pre-validation** - Check readiness
2. **Backup** - Create safety backup
3. **File Migration** - Copy module files
4. **Database Update** - Update app assignments
5. **Post-validation** - Verify success
6. **Report** - Display results

**Example Output**:
```
🚀 MIGRATION: source_app → target_app
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Pre-validation ✅
Step 2: Creating backup ✅
Step 3: Migrating modules...
   ✅ Custom Module 1 (5 doctypes)
   ✅ Custom Module 2 (8 doctypes)
Step 4: Updating database ✅
Step 5: Post-validation ✅

✅ MIGRATION COMPLETED SUCCESSFULLY!

Migrated:
   - 2 modules
   - 13 doctypes
   - 45 custom fields
   - 23 property setters

Time taken: 45 seconds
```

##### `clone-app-local <app>`
Clone app to a local bench for testing.

```bash
bench --site mysite migrate-app clone-app-local custom_app
```

**What it Does**:
1. Creates new bench directory
2. Installs Frappe
3. Clones app code
4. Sets up development environment

**Use Case**: Testing migrations in isolation

---

#### 7. Reporting Commands

##### `touched-tables`
Show migration history and touched tables.

```bash
bench --site mysite migrate-app touched-tables
```

**Shows**:
- Previously migrated tables
- Migration timestamps
- Success/failure status
- Related apps

##### `risk-assessment <doctype>`
Generate risk assessment for a doctype.

```bash
bench --site mysite migrate-app risk-assessment Customer
```

**Assessment Includes**:
- Classification (Standard/Customized/Custom/Orphan)
- Risk level (Low/Medium/High/Critical)
- Customizations count
- Dependencies
- Recommendations

**Example Output**:
```
⚠️  RISK ASSESSMENT: Customer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Status: Customized
Risk Level: Medium ⭐⭐

Details:
   - Base Type: Standard (erpnext)
   - Custom Fields: 3
   - Property Setters: 1
   - References: 45 doctypes link to this

Risk Factors:
   ⚠️  Core doctype with customizations
   ⚠️  High number of references
   ✅ No orphan status

📋 Recommendations:
   1. Test custom fields in target environment
   2. Verify all references after migration
   3. Backup before proceeding
   4. Consider using Custom Fields export/import
   5. Test thoroughly in staging environment
```

---

## 💼 Workflow Examples

### Workflow 1: Complete App Migration

**Scenario**: Migrate all customizations from `old_app` to `new_app`

```bash
# Step 1: Analyze the source app
bench --site mysite migrate-app analyze old_app

# Step 2: Check for data quality issues
bench --site mysite migrate-app analyze-orphans

# Step 3: Fix any issues found
bench --site mysite migrate-app fix-orphans old_app
bench --site mysite migrate-app restore-missing old_app

# Step 4: Validate migration readiness
bench --site mysite migrate-app validate-migration old_app

# Step 5: Classify doctypes to understand what's being migrated
bench --site mysite migrate-app classify-doctypes old_app

# Step 6: Verify database schema
bench --site mysite migrate-app fix-database-schema

# Step 7: Backup database (manual step!)
bench --site mysite backup --with-files

# Step 8: Execute migration
bench --site mysite migrate-app migrate old_app new_app

# Step 9: Verify integrity
bench --site mysite migrate-app verify-integrity

# Step 10: Rebuild search index
bench --site mysite rebuild-global-search
```

### Workflow 2: Interactive Migration (Beginner-Friendly)

```bash
# Launch interactive wizard
bench --site mysite migrate-app interactive

# Follow the prompts:
# 1. Select site
# 2. Choose app
# 3. Review modules
# 4. Filter by status
# 5. Confirm and execute
```

### Workflow 3: Fixing Data Quality Issues

**Scenario**: Clean up an app before migration

```bash
# Step 1: Analyze current state
bench --site mysite migrate-app analyze problematic_app

# Step 2: Identify orphans
bench --site mysite migrate-app analyze-orphans

# Step 3: Fix orphan doctypes
bench --site mysite migrate-app fix-orphans problematic_app

# Step 4: Restore missing files
bench --site mysite migrate-app restore-missing problematic_app

# Step 5: Fix app=None issues
bench --site mysite migrate-app fix-app-none problematic_app

# Step 6: Verify all references
bench --site mysite migrate-app fix-all-references problematic_app

# Step 7: Final integrity check
bench --site mysite migrate-app verify-integrity

# Step 8: Re-analyze to confirm
bench --site mysite migrate-app analyze problematic_app
```

### Workflow 4: Multi-Bench Management

**Scenario**: Manage apps across multiple benches

```bash
# Step 1: Discover available benches
bench --site mysite migrate-app list-benches

# Step 2: Analyze the ecosystem
bench --site mysite migrate-app multi-bench-analysis

# Step 3: Check specific bench apps
bench --site mysite migrate-app bench-apps frappe-bench

# Step 4: Check bench health
bench --site mysite migrate-app bench-health

# Step 5: Clone app to another bench for testing
bench --site mysite migrate-app clone-app-local custom_app
```

### Workflow 5: Database Schema Recovery

**Scenario**: Fix schema issues after manual changes

```bash
# Step 1: Run diagnostics
bench --site mysite migrate-app db-diagnostics

# Step 2: Fix database schema
bench --site mysite migrate-app fix-database-schema

# Step 3: Fix tree doctypes specifically
bench --site mysite migrate-app fix-tree-doctypes

# Step 4: Complete ERPNext setup if needed
bench --site mysite migrate-app complete-erpnext-install

# Step 5: Verify everything is fixed
bench --site mysite migrate-app verify-integrity
```

### Workflow 6: Pre-Migration Assessment

**Scenario**: Assess migration feasibility before starting

```bash
# Step 1: Comprehensive analysis
bench --site mysite migrate-app analyze custom_app

# Step 2: Classify all doctypes
bench --site mysite migrate-app classify-doctypes custom_app

# Step 3: Check for orphans
bench --site mysite migrate-app analyze-orphans

# Step 4: Analyze dependencies
bench --site mysite migrate-app fix-all-references custom_app

# Step 5: Risk assessment for critical doctypes
bench --site mysite migrate-app risk-assessment "Custom Important DocType"

# Step 6: Validation check
bench --site mysite migrate-app validate-migration custom_app

# Based on results, proceed or fix issues first
```

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### Issue 1: "Connection Lost" During Migration

**Symptoms**:
```
Error: Lost connection to database
Migration incomplete
```

**Solution**:
```python
# Use session management to auto-reconnect
from app_migrator.commands import SessionManager, migrate_app_modules

session = SessionManager(name="my_migration")
# Session will auto-reconnect if connection drops
migrate_app_modules("source", "target")
```

**Prevention**: Use session management decorators for long operations

---

#### Issue 2: "Table Already Exists" Error

**Symptoms**:
```
Error: Table 'tabCustom DocType' already exists
Cannot create table
```

**Solution**:
```bash
# Run database diagnostics
bench --site mysite migrate-app db-diagnostics

# Fix schema issues
bench --site mysite migrate-app fix-database-schema
```

---

#### Issue 3: Orphan Doctypes

**Symptoms**:
- Doctypes with app=None
- Modules not showing in desk
- Missing doctype files

**Solution**:
```bash
# Identify orphans
bench --site mysite migrate-app analyze-orphans

# Fix automatically
bench --site mysite migrate-app fix-orphans custom_app

# Restore missing files
bench --site mysite migrate-app restore-missing custom_app
```

---

#### Issue 4: Migration Validation Fails

**Symptoms**:
```
❌ Validation Failed:
   - Circular dependency detected
   - Missing required app
```

**Solution**:
```bash
# Analyze dependencies first
bench --site mysite migrate-app analyze custom_app

# Check for circular references
bench --site mysite migrate-app fix-all-references custom_app

# Install missing dependencies
bench get-app missing_app
bench --site mysite install-app missing_app

# Retry validation
bench --site mysite migrate-app validate-migration custom_app
```

---

#### Issue 5: Permission Denied

**Symptoms**:
```
PermissionError: Cannot write to directory
```

**Solution**:
```bash
# Fix ownership
cd /path/to/bench
sudo chown -R frappe:frappe apps/

# Fix permissions
chmod -R 755 apps/
```

---

#### Issue 6: Tree Doctype Errors

**Symptoms**:
```
Error: Field 'lft' doesn't exist
Error: Field 'rgt' doesn't exist
```

**Solution**:
```bash
# Fix tree doctypes
bench --site mysite migrate-app fix-tree-doctypes

# Rebuild tree structure
bench --site mysite rebuild-tree "DocType Name"
```

---

### Debug Mode

Enable detailed logging for troubleshooting:

```python
# In Frappe console
import frappe
frappe.conf.developer_mode = 1

# Or in site_config.json
{
    "developer_mode": 1,
    "logging": 2
}
```

### Getting Help

1. **Check logs**: `tail -f logs/worker.log`
2. **Run diagnostics**: `bench --site mysite migrate-app db-diagnostics`
3. **Verify integrity**: `bench --site mysite migrate-app verify-integrity`
4. **Check documentation**: Review [ARCHITECTURE.md](ARCHITECTURE.md)
5. **Open an issue**: GitHub Issues with full error traceback

---

## 🎯 Best Practices

### 1. Always Backup First 💾

```bash
# Full backup with files
bench --site mysite backup --with-files

# Verify backup
ls -lh sites/mysite/private/backups/
```

**Why**: Migrations can have unexpected results. Backups enable rollback.

### 2. Test in Staging First 🧪

```bash
# Clone to staging
bench --site staging migrate-app clone-app-local production_app

# Test migration
bench --site staging migrate-app migrate old_app new_app

# Verify results
bench --site staging migrate-app verify-integrity
```

**Why**: Catch issues before affecting production.

### 3. Use Session Management for Long Operations 📊

```python
from app_migrator.commands import SessionManager

session = SessionManager(name="migration_jan_2025")
# Your migration code
session.save()
```

**Why**: Enables recovery if process is interrupted.

### 4. Validate Before Migrating ✅

```bash
# Always validate first
bench --site mysite migrate-app validate-migration custom_app

# Only proceed if validation passes
```

**Why**: Identifies issues before migration starts.

### 5. Fix Data Quality Issues First 🧹

```bash
# Fix orphans
bench --site mysite migrate-app fix-orphans custom_app

# Restore missing
bench --site mysite migrate-app restore-missing custom_app

# Then migrate
bench --site mysite migrate-app migrate custom_app new_app
```

**Why**: Clean data ensures smoother migration.

### 6. Understand What You're Migrating 🔍

```bash
# Classify doctypes
bench --site mysite migrate-app classify-doctypes custom_app

# Review each category
# Decide what actually needs to be migrated
```

**Why**: Not everything needs to be migrated (e.g., standard doctypes).

### 7. Monitor Progress 📈

```python
from app_migrator.commands import ProgressTracker

tracker = ProgressTracker("MyApp", total_steps=5)
# Use tracker throughout your migration
```

**Why**: Visual feedback confirms operation is progressing.

### 8. Document Your Changes 📝

Keep a migration log:
```
Date: 2025-10-11
Source: old_app
Target: new_app
Modules: Custom Module 1, Custom Module 2
Doctypes: 15 custom, 3 customized
Result: Success
Issues: None
Time: 45 seconds
```

**Why**: Essential for troubleshooting and future reference.

### 9. Verify After Migration ✔️

```bash
# Always verify
bench --site mysite migrate-app verify-integrity

# Test the migrated app
# Check all doctypes are accessible
# Verify customizations are preserved
```

**Why**: Confirms migration success and data integrity.

### 10. Use Interactive Mode for Complex Migrations 🧙

```bash
bench --site mysite migrate-app interactive
```

**Why**: Guided workflow reduces mistakes and provides validation at each step.

---

## ❓ FAQ

### General Questions

**Q: Is App Migrator safe to use in production?**

A: Yes, v5.0.0 is production-ready. However, always:
- Backup before any operation
- Test in staging first
- Validate before migrating
- Monitor during migration

**Q: Can I undo a migration?**

A: Yes, if you have a backup:
```bash
# Restore from backup
bench --site mysite restore /path/to/backup.sql.gz
```

**Q: What Frappe versions are supported?**

A: App Migrator v5.0.0 supports Frappe v13 and above, including v14 and v15.

**Q: Do I need to stop services during migration?**

A: For large migrations, it's recommended to put the site in maintenance mode:
```bash
bench --site mysite set-maintenance-mode on
# Perform migration
bench --site mysite set-maintenance-mode off
```

### Classification Questions

**Q: What's the difference between "Standard" and "Customized"?**

A: 
- **Standard**: Core doctype, completely unmodified
- **Customized**: Core doctype with custom fields or property setters added

**Q: Should I migrate "Standard" doctypes?**

A: No! Standard doctypes are part of the framework/app and don't need migration. Only migrate:
- Custom doctypes (user-created)
- Customized doctypes (if you want to move the customizations)

**Q: What are "Orphan" doctypes and how do I fix them?**

A: Orphan doctypes have app=None or wrong module assignment. Fix with:
```bash
bench --site mysite migrate-app fix-orphans app_name
```

### Migration Questions

**Q: Can I migrate specific modules only?**

A: Yes:
```bash
bench --site mysite migrate-app migrate source target --modules="Module1,Module2"
```

**Q: What happens to custom fields during migration?**

A: Custom fields and property setters are automatically updated to reference the new app. Use:
```bash
bench --site mysite migrate-app fix-all-references new_app
```

**Q: Can I migrate from one bench to another?**

A: Yes, use the clone function:
```bash
bench --site mysite migrate-app clone-app-local app_name
```

### Technical Questions

**Q: Where are sessions stored?**

A: Sessions are stored in JSON files at:
```
/tmp/app_migrator_sessions/session_name.json
```

**Q: How do I enable debug logging?**

A: Add to site_config.json:
```json
{
    "developer_mode": 1,
    "logging": 2
}
```

**Q: Can I use this with custom apps?**

A: Yes! App Migrator works with any Frappe app, including custom apps.

**Q: Does this work with ERPNext?**

A: Yes, App Migrator v5.0.0 is fully compatible with ERPNext and includes special handling for ERPNext-specific features.

### Performance Questions

**Q: How long does a migration take?**

A: Depends on:
- Number of modules: ~5-10 seconds per module
- Number of doctypes: ~1-2 seconds per doctype
- Database size: Larger databases take longer
- Server resources: Better hardware = faster migration

Typical small app (10 modules): 1-2 minutes
Typical large app (50+ modules): 5-10 minutes

**Q: Will migration affect site performance?**

A: During migration, site performance may be impacted. Use maintenance mode for large migrations.

**Q: Can I run multiple migrations simultaneously?**

A: Not recommended. Run migrations sequentially to avoid conflicts.

---

## 📞 Support

### Need Help?

- **Documentation**: Check [README.md](README.md) and [ARCHITECTURE.md](ARCHITECTURE.md)
- **Issues**: Open a GitHub issue with:
  - Frappe/ERPNext version
  - App Migrator version
  - Complete error traceback
  - Steps to reproduce
- **Community**: Join Frappe Forum discussions

### Reporting Bugs

Include in your bug report:
1. **Environment**:
   ```bash
   bench version
   pip list | grep frappe
   ```

2. **Command that failed**:
   ```bash
   bench --site mysite migrate-app command-name
   ```

3. **Complete error traceback**

4. **Steps to reproduce**

---

**Made with ❤️ by the App Migrator Team**

*Last Updated: October 11, 2025*
*Version: 5.0.0*
