# 🚀 Deployment Guide - App Migrator v5.0.0

> **Complete deployment and installation guide** - From development to production

---

## 📋 Table of Contents

1. [Prerequisites](#-prerequisites)
2. [Installation Methods](#-installation-methods)
3. [Configuration](#-configuration)
4. [Bench Integration](#-bench-integration)
5. [Testing & Verification](#-testing--verification)
6. [Production Deployment](#-production-deployment)
7. [Rollback Procedures](#-rollback-procedures)
8. [Maintenance](#-maintenance)
9. [Troubleshooting](#-troubleshooting)

---

## ✅ Prerequisites

### System Requirements

#### Minimum Requirements
- **OS**: Ubuntu 18.04+ / Debian 10+ / CentOS 7+
- **RAM**: 2GB minimum, 4GB recommended
- **Disk Space**: 500MB for app + working space
- **Python**: 3.8 or higher
- **Node.js**: 14.x or higher
- **Database**: MariaDB 10.3+ or PostgreSQL 12+

#### Software Prerequisites

```bash
# Check Python version
python3 --version
# Should be 3.8 or higher

# Check Node.js version
node --version
# Should be v14 or higher

# Check database
mysql --version
# or
psql --version

# Check bench
bench --version
# Should have Frappe bench installed
```

### User Permissions

The user running the installation must have:
- Read/write access to bench directory
- Database user permissions
- Ability to restart services

### Frappe/ERPNext Version Compatibility

| Frappe Version | ERPNext Version | App Migrator v5.0.0 |
|----------------|-----------------|---------------------|
| v13.x | v13.x | ✅ Supported |
| v14.x | v14.x | ✅ Supported |
| v15.x | v15.x | ✅ Supported |
| v12.x or older | v12.x or older | ⚠️ Not tested |

---

## 📥 Installation Methods

### Method 1: Install from GitHub (Recommended)

This is the recommended method for most users.

#### Step 1: Navigate to Bench

```bash
# Change to your bench directory
cd /path/to/frappe-bench

# Activate virtual environment
source env/bin/activate
```

#### Step 2: Get the App

```bash
# Get from GitHub
bench get-app https://github.com/yourusername/app_migrator.git

# Or specify a branch
bench get-app https://github.com/yourusername/app_migrator.git --branch main

# Or specify a version tag
bench get-app https://github.com/yourusername/app_migrator.git --branch v5.0.0
```

#### Step 3: Install on Site

```bash
# Install on a specific site
bench --site your-site install-app app_migrator

# Or install on all sites
bench --site all install-app app_migrator
```

#### Step 4: Verify Installation

```bash
# Check if installed
bench --site your-site list-apps

# Should show 'app_migrator' in the list
```

### Method 2: Install from Local Directory

Use this method if you have the app code locally.

#### Step 1: Copy to Bench

```bash
# Copy app directory to bench apps folder
cp -r /path/to/app_migrator_v5 /path/to/frappe-bench/apps/app_migrator

# Or create a symbolic link
ln -s /path/to/app_migrator_v5 /path/to/frappe-bench/apps/app_migrator
```

#### Step 2: Install Dependencies

```bash
cd /path/to/frappe-bench

# Get app dependencies
bench get-app app_migrator

# Or manually install
cd apps/app_migrator
pip install -r requirements.txt
```

#### Step 3: Install on Site

```bash
bench --site your-site install-app app_migrator
```

### Method 3: Development Installation

For developers who want to contribute or customize.

#### Step 1: Clone Repository

```bash
cd /path/to/frappe-bench/apps

# Clone the repository
git clone https://github.com/yourusername/app_migrator.git

# Or fork and clone your fork
git clone https://github.com/YOUR_USERNAME/app_migrator.git
```

#### Step 2: Install in Editable Mode

```bash
cd /path/to/frappe-bench

# Install in development mode
bench get-app app_migrator --skip-assets

# Install on development site
bench --site development install-app app_migrator
```

#### Step 3: Enable Developer Mode

```bash
# Enable developer mode on site
bench --site development set-config developer_mode 1

# Or edit site_config.json
nano sites/development/site_config.json
```

Add:
```json
{
    "developer_mode": 1,
    "logging": 2
}
```

### Method 4: Production Installation (Docker)

For containerized deployments.

#### Step 1: Create Dockerfile

```dockerfile
# Dockerfile
FROM frappe/erpnext-worker:v14.0.0

# Install app_migrator
RUN bench get-app https://github.com/yourusername/app_migrator.git
RUN bench --site all install-app app_migrator
```

#### Step 2: Build Image

```bash
docker build -t my-erpnext-with-migrator:v5.0.0 .
```

#### Step 3: Deploy

```bash
docker-compose up -d
```

---

## ⚙️ Configuration

### Basic Configuration

App Migrator works out-of-the-box with minimal configuration.

#### Site Configuration

Add to `sites/your-site/site_config.json`:

```json
{
    "app_migrator": {
        "session_storage_path": "/tmp/app_migrator_sessions",
        "backup_before_migration": true,
        "auto_reconnect": true,
        "progress_tracking": true
    }
}
```

#### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `session_storage_path` | String | `/tmp/app_migrator_sessions` | Path for session files |
| `backup_before_migration` | Boolean | `false` | Auto-backup before migrations |
| `auto_reconnect` | Boolean | `true` | Auto-reconnect on connection loss |
| `progress_tracking` | Boolean | `true` | Enable progress tracking |
| `log_level` | String | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `max_session_age_days` | Integer | `30` | Delete sessions older than this |

### Advanced Configuration

#### Session Management

```json
{
    "app_migrator": {
        "session": {
            "storage_path": "/var/frappe/sessions",
            "auto_save_interval": 60,
            "max_age_days": 30,
            "compress_old_sessions": true
        }
    }
}
```

#### Performance Tuning

```json
{
    "app_migrator": {
        "performance": {
            "batch_size": 100,
            "parallel_operations": 4,
            "connection_pool_size": 10,
            "query_timeout": 300
        }
    }
}
```

#### Logging Configuration

```json
{
    "app_migrator": {
        "logging": {
            "level": "INFO",
            "file": "logs/app_migrator.log",
            "max_file_size_mb": 100,
            "backup_count": 5,
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }
}
```

### Environment Variables

Set environment variables for system-wide configuration:

```bash
# Add to ~/.bashrc or /etc/environment
export APP_MIGRATOR_SESSION_PATH="/var/frappe/sessions"
export APP_MIGRATOR_LOG_LEVEL="INFO"
export APP_MIGRATOR_BACKUP_ENABLED="true"
```

---

## 🔌 Bench Integration

### Register Custom Commands

App Migrator automatically registers its commands with bench.

#### Verify Command Registration

```bash
# List all bench commands
bench --help

# Should see 'migrate-app' in the list

# View migrate-app help
bench --site your-site migrate-app
```

#### Command Structure

```
bench --site <site> migrate-app <command> [options]
```

### Add to Bench Config

Optionally add to `common_site_config.json`:

```json
{
    "app_migrator_enabled": true,
    "app_migrator_version": "5.0.0"
}
```

### Hooks Configuration

The app registers hooks in `hooks.py`:

```python
# hooks.py content (already configured)
app_name = "app_migrator"
app_title = "App Migrator"
app_publisher = "Your Company"
app_description = "Complete Frappe app migration toolkit"
app_icon = "octicon octicon-file-directory"
app_color = "blue"
app_email = "support@yourcompany.com"
app_license = "MIT"
app_version = "5.0.0"

# Include custom commands
commands = [
    {
        "name": "migrate-app",
        "description": "App Migrator v5.0.0 commands"
    }
]
```

---

## ✅ Testing & Verification

### Post-Installation Tests

#### Test 1: Basic Installation Check

```bash
# Check if app is installed
bench --site your-site list-apps

# Should show:
# frappe
# app_migrator
# ... (other apps)
```

#### Test 2: Version Verification

```bash
# Check version in console
bench --site your-site console
```

```python
# In Frappe console
from app_migrator.commands import __version__
print(f"App Migrator version: {__version__}")
# Should output: App Migrator version: 5.0.0

# Verify all modules are available
from app_migrator.commands import (
    interactive_migration_wizard,
    analyze_app_comprehensive,
    SessionManager,
    ProgressTracker
)
print("✅ All modules loaded successfully!")
```

#### Test 3: Command Availability

```bash
# Test interactive command
bench --site your-site migrate-app

# Should display help with all 23 commands
```

#### Test 4: Database Connectivity

```bash
# Run database diagnostics
bench --site your-site migrate-app db-diagnostics

# Should complete without errors
```

#### Test 5: Session Management

```bash
# Test session creation
bench --site your-site console
```

```python
from app_migrator.commands import SessionManager

# Create test session
session = SessionManager(name="test_session")
session.update_progress("test", "started")
session.save()

# Load session
loaded = SessionManager.load_session("test_session")
print(f"Session loaded: {loaded.name}")
print("✅ Session management working!")
```

#### Test 6: Analysis Functions

```bash
# Analyze an existing app (e.g., frappe)
bench --site your-site migrate-app analyze frappe

# Should display comprehensive analysis
```

#### Test 7: Classification System

```bash
# Test doctype classification
bench --site your-site console
```

```python
from app_migrator.commands import get_doctype_classification

# Test with a known doctype
result = get_doctype_classification("User")
print(f"Classification: {result['status']}")
print("✅ Classification system working!")
```

### Integration Tests

#### Test Scenario 1: Complete Analysis Workflow

```bash
#!/bin/bash
# test_analysis.sh

SITE="your-site"
APP="frappe"

echo "Testing Analysis Workflow..."

# Step 1: Analyze app
echo "1. Analyzing app..."
bench --site $SITE migrate-app analyze $APP

# Step 2: Classify doctypes
echo "2. Classifying doctypes..."
bench --site $SITE migrate-app classify-doctypes $APP

# Step 3: Check for orphans
echo "3. Checking orphans..."
bench --site $SITE migrate-app analyze-orphans

# Step 4: Run diagnostics
echo "4. Running diagnostics..."
bench --site $SITE migrate-app db-diagnostics

echo "✅ Analysis workflow test completed!"
```

#### Test Scenario 2: Data Quality Workflow

```bash
#!/bin/bash
# test_data_quality.sh

SITE="your-site"

echo "Testing Data Quality Workflow..."

# Step 1: Verify integrity
echo "1. Verifying data integrity..."
bench --site $SITE migrate-app verify-integrity

# Step 2: Fix database schema
echo "2. Fixing database schema..."
bench --site $SITE migrate-app fix-database-schema

# Step 3: Check tree doctypes
echo "3. Fixing tree doctypes..."
bench --site $SITE migrate-app fix-tree-doctypes

echo "✅ Data quality workflow test completed!"
```

### Performance Tests

#### Test Database Performance

```bash
# Time the analysis command
time bench --site your-site migrate-app analyze frappe

# Should complete in reasonable time (< 1 minute for most apps)
```

#### Test Session Performance

```python
import time
from app_migrator.commands import SessionManager

# Test session creation and save performance
start = time.time()
session = SessionManager(name="perf_test")
for i in range(100):
    session.update_progress(f"step_{i}", "completed")
session.save()
end = time.time()

print(f"100 updates + save: {end - start:.2f} seconds")
# Should be < 1 second
```

### Automated Test Suite

Create a comprehensive test script:

```bash
#!/bin/bash
# comprehensive_test.sh

SITE="your-site"
LOG_FILE="test_results.log"

echo "App Migrator v5.0.0 - Comprehensive Test Suite" > $LOG_FILE
echo "================================================" >> $LOG_FILE
echo "Started: $(date)" >> $LOG_FILE
echo "" >> $LOG_FILE

# Function to run test
run_test() {
    local test_name=$1
    local command=$2
    
    echo "Running: $test_name..."
    echo "TEST: $test_name" >> $LOG_FILE
    
    if eval $command >> $LOG_FILE 2>&1; then
        echo "  ✅ PASSED"
        echo "  RESULT: PASSED" >> $LOG_FILE
    else
        echo "  ❌ FAILED"
        echo "  RESULT: FAILED" >> $LOG_FILE
    fi
    echo "" >> $LOG_FILE
}

# Run tests
run_test "Installation Check" "bench --site $SITE list-apps | grep app_migrator"
run_test "Command Help" "bench --site $SITE migrate-app"
run_test "Database Diagnostics" "bench --site $SITE migrate-app db-diagnostics"
run_test "Analyze Frappe" "bench --site $SITE migrate-app analyze frappe"
run_test "List Benches" "bench --site $SITE migrate-app list-benches"
run_test "Verify Integrity" "bench --site $SITE migrate-app verify-integrity"

echo "" >> $LOG_FILE
echo "Completed: $(date)" >> $LOG_FILE
echo "Test results saved to: $LOG_FILE"
```

---

## 🏭 Production Deployment

### Pre-Deployment Checklist

- [ ] Tested in staging environment
- [ ] Database backup completed
- [ ] Site backup with files completed
- [ ] Maintenance window scheduled
- [ ] Team notified
- [ ] Rollback plan prepared
- [ ] Monitoring configured
- [ ] Documentation reviewed

### Deployment Steps

#### Step 1: Prepare Production Environment

```bash
# SSH to production server
ssh production-server

# Navigate to production bench
cd /home/frappe/production-bench

# Activate virtual environment
source env/bin/activate

# Check current status
bench --version
```

#### Step 2: Create Backup

```bash
# Create full backup
bench --site production-site backup --with-files

# Verify backup
ls -lh sites/production-site/private/backups/

# Copy backup to safe location
cp sites/production-site/private/backups/*.sql.gz /backup/location/
cp sites/production-site/private/backups/*.tar /backup/location/
```

#### Step 3: Enable Maintenance Mode

```bash
# Put site in maintenance mode
bench --site production-site set-maintenance-mode on

# Verify
curl https://production-site.com
# Should show maintenance page
```

#### Step 4: Install App Migrator

```bash
# Get the app
bench get-app https://github.com/yourusername/app_migrator.git --branch v5.0.0

# Install on production site
bench --site production-site install-app app_migrator

# Run migrations if any
bench --site production-site migrate
```

#### Step 5: Verify Installation

```bash
# Check if installed
bench --site production-site list-apps

# Test a simple command
bench --site production-site migrate-app list-benches

# Check version
bench --site production-site console
```

```python
from app_migrator.commands import __version__
print(__version__)  # Should be 5.0.0
```

#### Step 6: Restart Services

```bash
# Restart bench services
bench restart

# Or restart specific services
sudo supervisorctl restart all
```

#### Step 7: Disable Maintenance Mode

```bash
# Take site out of maintenance mode
bench --site production-site set-maintenance-mode off

# Verify site is accessible
curl https://production-site.com
```

#### Step 8: Monitor

```bash
# Monitor logs
tail -f logs/worker.log
tail -f logs/web.log

# Check for errors
grep -i error logs/*.log
```

### Production Configuration

Create production-specific configuration in `site_config.json`:

```json
{
    "app_migrator": {
        "session_storage_path": "/var/frappe/app_migrator_sessions",
        "backup_before_migration": true,
        "auto_reconnect": true,
        "progress_tracking": true,
        "logging": {
            "level": "INFO",
            "file": "/var/log/frappe/app_migrator.log"
        },
        "performance": {
            "batch_size": 100,
            "connection_pool_size": 10
        }
    }
}
```

### High-Availability Deployment

For multi-server setups:

#### Load Balancer Configuration

```nginx
# nginx.conf
upstream frappe_backend {
    server 10.0.0.10:8000 weight=3;
    server 10.0.0.11:8000 weight=3;
    server 10.0.0.12:8000 weight=2;
}

location /api/method/app_migrator {
    # Route migration commands to specific server
    proxy_pass http://10.0.0.10:8000;
}
```

#### Session Sharing

Use shared storage for sessions:

```json
{
    "app_migrator": {
        "session_storage_path": "/mnt/shared/frappe/sessions"
    }
}
```

---

## 🔄 Rollback Procedures

### When to Rollback

- Installation fails
- Critical errors in production
- Performance issues
- Data integrity problems

### Rollback Steps

#### Option 1: Uninstall App Migrator

```bash
# Uninstall from site
bench --site production-site uninstall-app app_migrator

# Remove app from bench
rm -rf apps/app_migrator

# Restart services
bench restart
```

#### Option 2: Restore from Backup

If issues occurred after using App Migrator:

```bash
# Put site in maintenance mode
bench --site production-site set-maintenance-mode on

# Restore database
bench --site production-site restore /path/to/backup.sql.gz

# Restore files (if needed)
bench --site production-site restore /path/to/files.tar

# Clear cache
bench --site production-site clear-cache

# Rebuild
bench --site production-site migrate
bench build

# Disable maintenance mode
bench --site production-site set-maintenance-mode off

# Restart
bench restart
```

#### Option 3: Rollback Specific Migration

If a migration caused issues:

```bash
# Identify the migration
bench --site production-site console
```

```python
# Check migration history
from app_migrator.commands import analyze_touched_tables
result = analyze_touched_tables()
print(result['tables'])

# Restore specific doctypes
# (Manual process based on backup)
```

### Post-Rollback Verification

```bash
# Verify site is working
curl https://production-site.com

# Check logs for errors
tail -100 logs/worker.log

# Test critical functions
bench --site production-site console
```

```python
# Test critical doctypes
frappe.get_list("Customer", limit=5)
# Should return data without errors
```

---

## 🔧 Maintenance

### Regular Maintenance Tasks

#### Weekly Tasks

```bash
# Clean old session files (older than 30 days)
find /tmp/app_migrator_sessions -mtime +30 -delete

# Check logs for errors
grep -i error logs/app_migrator.log

# Verify disk space
df -h
```

#### Monthly Tasks

```bash
# Update app to latest version
cd /path/to/frappe-bench
bench update --apps app_migrator

# Run integrity checks
bench --site production-site migrate-app verify-integrity

# Review and archive old backups
# Archive backups older than 90 days
```

#### Quarterly Tasks

```bash
# Full system review
bench --site production-site migrate-app db-diagnostics
bench --site production-site migrate-app bench-health

# Update documentation
# Review and update configuration

# Performance review
# Check if optimizations are needed
```

### Log Management

#### Log Rotation

Create `/etc/logrotate.d/app_migrator`:

```
/var/log/frappe/app_migrator.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0644 frappe frappe
    sharedscripts
    postrotate
        systemctl reload nginx > /dev/null 2>/dev/null || true
    endscript
}
```

#### Log Monitoring

```bash
# Monitor logs in real-time
tail -f /var/log/frappe/app_migrator.log

# Check for errors
grep ERROR /var/log/frappe/app_migrator.log | tail -20

# Check for warnings
grep WARNING /var/log/frappe/app_migrator.log | tail -20
```

### Performance Monitoring

```bash
# Monitor database queries
# Add to cron: 0 */6 * * *
#!/bin/bash
mysql -e "SHOW FULL PROCESSLIST" | grep app_migrator > /var/log/app_migrator_queries.log
```

### Backup Strategy

```bash
# Automated backup script
#!/bin/bash
# /home/frappe/scripts/backup_before_migration.sh

SITE="production-site"
BACKUP_DIR="/backup/app_migrator"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup
bench --site $SITE backup --with-files

# Copy to backup directory
cp sites/$SITE/private/backups/*.sql.gz $BACKUP_DIR/db_$DATE.sql.gz
cp sites/$SITE/private/backups/*.tar $BACKUP_DIR/files_$DATE.tar

# Keep only last 7 days
find $BACKUP_DIR -mtime +7 -delete

echo "Backup completed: $DATE"
```

---

## 🐛 Troubleshooting

### Common Deployment Issues

#### Issue 1: Installation Fails with Permission Error

**Error**:
```
Permission denied: '/path/to/bench/apps/app_migrator'
```

**Solution**:
```bash
# Fix ownership
sudo chown -R frappe:frappe /path/to/bench/apps/app_migrator

# Fix permissions
chmod -R 755 /path/to/bench/apps/app_migrator
```

#### Issue 2: Commands Not Available After Installation

**Error**:
```
bash: migrate-app: command not found
```

**Solution**:
```bash
# Reload bench
bench restart

# Reinstall if needed
bench --site your-site uninstall-app app_migrator
bench --site your-site install-app app_migrator

# Clear cache
bench clear-cache
```

#### Issue 3: Import Errors

**Error**:
```
ModuleNotFoundError: No module named 'app_migrator'
```

**Solution**:
```bash
# Activate virtual environment
source env/bin/activate

# Reinstall dependencies
pip install -e apps/app_migrator

# Verify
python -c "import app_migrator; print(app_migrator.__version__)"
```

#### Issue 4: Database Connection Issues

**Error**:
```
Can't connect to MySQL server
```

**Solution**:
```bash
# Check database status
sudo systemctl status mysql

# Check site_config.json
cat sites/your-site/site_config.json

# Test connection
bench --site your-site console
```

```python
import frappe
frappe.db.sql("SELECT 1")
# Should return: ((1,),)
```

#### Issue 5: Session Storage Issues

**Error**:
```
PermissionError: [Errno 13] Permission denied: '/tmp/app_migrator_sessions'
```

**Solution**:
```bash
# Create directory
mkdir -p /tmp/app_migrator_sessions

# Fix permissions
chmod 755 /tmp/app_migrator_sessions
chown frappe:frappe /tmp/app_migrator_sessions

# Or configure different path
nano sites/your-site/site_config.json
```

```json
{
    "app_migrator": {
        "session_storage_path": "/home/frappe/sessions"
    }
}
```

### Getting Support

1. **Check logs**: `tail -100 logs/worker.log`
2. **Run diagnostics**: `bench --site your-site migrate-app db-diagnostics`
3. **Review documentation**: Check [USER_GUIDE.md](USER_GUIDE.md)
4. **Open issue**: https://github.com/yourusername/app_migrator/issues

---

## 📚 Additional Resources

- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)
- **README**: [README.md](README.md)

---

**Made with ❤️ by the App Migrator Team**

*Last Updated: October 11, 2025*
*Version: 5.0.0*
