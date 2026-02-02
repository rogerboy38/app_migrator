# App Migrator Enterprise 🚀

**Multi-bench Migration Toolkit for Frappe/ERPNext**

![Frappe 15+](https://img.shields.io/badge/Frappe-15+-blue.svg)
![ERPNext Compatible](https://img.shields.io/badge/ERPNext-Compatible-green.svg)
![License MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Version v9.0.0+](https://img.shields.io/badge/Version-v9.0.0+-brightgreen.svg)

## 📋 Overview

App Migrator Enterprise is a comprehensive CLI tool for managing Frappe app migrations, diagnostics, and maintenance across multiple benches. It provides intelligent analysis, conflict resolution, and automated migration workflows with enhanced Git operations.

## ✨ Enhanced Features (v9.0.0+)

### **🎯 Git Operations - Fully Enhanced**
- **Multi-remote Support**: Handle multiple remotes (origin, upstream) per app
- **Intelligent Status Detection**: Shows ahead/behind/diverged/same status with commit counts
- **Automatic Commit Handling**: Commit uncommitted changes with custom messages
- **Safe Push Options**: Dry-run, force push, pull-first, skip-diverged
- **SSH Connection Testing**: Automatic GitHub SSH connectivity verification
- **Comprehensive Summary**: Detailed success/failure reports with emoji-enhanced output

### **🏗️ Core Migration Features**
- Multi-bench Management: Analyze and manage apps across different benches
- Conflict Detection: Identify and resolve conflicts between apps
- Migration Planning: Generate intelligent migration plans
- Orphan Detection: Find and fix orphaned DocTypes
- Health Checks: Comprehensive app diagnosis and validation
- Modernization: Upgrade apps from traditional to modern Python structure

## 🚀 Quick Start

### Installation
```bash
# Clone the app
bench get-app app_migrator https://github.com/rogerboy38/app_migrator

# Install on your site
bench --site [site-name] install-app app_migrator

# Build assets
bench build --app app_migrator
bench restart
Basic Usage
bash

# View all available commands
bench app-migrator --help

# Check system health
bench app-migrator health

# Scan your site for analysis
bench app-migrator scan --site [site-name]

📊 Command Reference

Total commands available: 26
#	Command	Description	Category
1	app-migrator	Main command group	Group
2	app-migrator health	Check App Migrator health and list commands	Diagnostics
3	app-migrator scan	Scan site for apps, doctypes, custom fields	Analysis
4	app-migrator conflicts	Detect conflicts between apps (use --all-apps to scan all)	Conflict Resolution
5	app-migrator plan	Generate a migration plan	Migration
6	app-migrator execute	Execute a migration plan	Migration
7	app-migrator benches	List all available benches and their apps	Bench Management
8	app-migrator session-start	Start a new migration session	Sessions
9	app-migrator session-status	Check migration session status	Sessions
10	app-migrator apps	List downloaded apps vs installed apps	App Management
11	app-migrator fix-orphans	Fix orphan doctypes (doctypes with no module or app)	Maintenance
12	app-migrator analyze	Analyze app structure (modern pyproject.toml vs traditional setup.py)	Analysis
13	app-migrator create-host	Create a staging/host app for ping-pong migration	Migration
14	app-migrator stage	Stage doctypes from source app to host app with prefix	Migration
15	app-migrator unstage	Unstage doctypes from host module to target module without prefix	Migration
16	app-migrator fix-structure	Analyze Frappe app folder structure and report issues	Maintenance
17	app-migrator ensure-controllers	Create missing .py controller files for DocTypes in apps	Maintenance
18	app-migrator fix-app-field	Fix DocTypes with NULL app field to prevent orphan detection	Maintenance
19	app-migrator fix-json-app	Fix JSON app field issues to prevent orphan detection	Maintenance
20	app-migrator wizard	Launch interactive migration wizard (no site required)	Migration
21	app-migrator orphans	Intelligent orphaned DocType detection and resolution	Maintenance
22	app-migrator predict-success	Predict migration success probability using heuristics	Analysis
23	app-migrator generate-plan	Generate an intelligent migration plan with validation	Migration
24	app-migrator diagnose	Comprehensive app diagnosis for migration readiness	Diagnostics
25	app-migrator modernize	Upgrade app from traditional setup.py to modern pyproject.toml	Modernization
26	app-migrator git-push	Enhanced Git Push Helper for all apps	Git Operations
🔧 Key Commands Deep Dive
🚀 Git Push Helper (Enhanced)

The git-push command has been completely rewritten for v9.0.0 with advanced features:
bash

# Show help with all options
bench app-migrator git-push --help

# Dry-run: See what would be pushed without making changes
bench app-migrator git-push --dry-run

# Push all apps with commit message for uncommitted changes
bench app-migrator git-push --message "Release v2.0"

# Push specific app only
bench app-migrator git-push --app my_app --dry-run

# Force push (use with caution)
bench app-migrator git-push --app my_app --force

# Pull from remote before pushing
bench app-migrator git-push --app my_app --pull-first

# Skip apps with diverged branches
bench app-migrator git-push --skip-diverged

# Combined example: Safe push with commit
bench app-migrator git-push --app my_app --message "Bug fixes" --dry-run

Features:

    ✅ Multi-remote detection: Automatically detects all remotes (origin, upstream, etc.)

    ✅ Branch status: Shows ahead/behind/diverged/same status with commit counts

    ✅ SSH verification: Tests GitHub SSH connection before pushing

    ✅ Uncommitted changes: Auto-commits with custom message when needed

    ✅ Dry-run mode: Preview changes before execution

    ✅ Force push: Safe force push with warnings

    ✅ Pull-first: Pull changes before pushing to avoid conflicts

    ✅ Skip diverged: Skip apps with diverged branches

    ✅ Comprehensive summary: Detailed success/failure report

🏥 Health & Diagnostics
bash

# Check overall health
bench app-migrator health

# Comprehensive diagnosis
bench app-migrator diagnose --site [site-name]

# Predict migration success
bench app-migrator predict-success --source-app [app] --target-app [app]

🔍 Analysis & Scanning
bash

# Scan site for detailed analysis
bench app-migrator scan --site [site-name]

# Analyze app structure
bench app-migrator analyze --app [app-name]

# Detect conflicts between apps
bench app-migrator conflicts --app1 [app1] --app2 [app2]

# Scan all apps for conflicts
bench app-migrator conflicts --all-apps

🚚 Migration Workflow
bash

# Generate migration plan
bench app-migrator plan --source-bench [path] --target-bench [path]

# Create host app for staging
bench app-migrator create-host --source-app [app] --host-app [host-app]

# Stage doctypes
bench app-migrator stage --source-app [app] --host-app [host-app] --prefix [prefix]

# Execute migration
bench app-migrator execute --plan-file [path]

🛠️ Maintenance & Fixes
bash

# Fix orphan doctypes
bench app-migrator fix-orphans --site [site-name]

# Intelligent orphan detection
bench app-migrator orphans --site [site-name]

# Fix app structure issues
bench app-migrator fix-structure --app [app-name]

# Ensure controller files exist
bench app-migrator ensure-controllers --app [app-name]

# Fix NULL app fields
bench app-migrator fix-app-field --site [site-name]

# Fix JSON app fields
bench app-migrator fix-json-app --site [site-name]

🔄 Modernization
bash

# Modernize app structure
bench app-migrator modernize --app [app-name]

# Interactive wizard
bench app-migrator wizard

🎯 Use Cases
1. Git Management for All Apps
bash

# Check what would be pushed for all apps
bench app-migrator git-push --dry-run

# Push all apps with automatic commits
bench app-migrator git-push --message "Daily update"

# Push specific app with custom options
bench app-migrator git-push --app my_app --pull-first --skip-diverged

2. Multi-bench Migration
bash

# Analyze source bench
bench app-migrator scan --site source_site

# Generate migration plan
bench app-migrator plan --source-bench /path/to/source --target-bench /path/to/target

# Execute migration
bench app-migrator execute --plan-file migration_plan.json

3. App Conflict Resolution
bash

# Detect conflicts
bench app-migrator conflicts --all-apps

# Resolve duplicates
bench app-migrator resolve-duplicates --app1 [app1] --app2 [app2]

4. App Modernization
bash

# Analyze current structure
bench app-migrator analyze --app legacy_app

# Modernize to pyproject.toml
bench app-migrator modernize --app legacy_app

🏗️ Architecture
text

app_migrator/
├── commands/           # CLI command modules
│   ├── __init__.py    # Command registration
│   ├── git_push.py    # Enhanced Git push helper (v9.0.0+)
│   ├── analyze.py     # App structure analysis
│   └── ...           # Other command modules
├── utils/             # Utility functions
│   └── git_helper.py  # Git operations utilities
├── migrations/        # Database migrations
└── public/           # Frontend assets

🔒 Security Features

    Safe Mode: Confirmation prompts for destructive operations

    Dry Run: Preview changes before execution

    Session Management: Track migration sessions

    Validation: Comprehensive pre-migration checks

    SSH Verification: Automatic GitHub connection testing

📈 Performance

    Parallel Processing: Concurrent operations where possible

    Caching: Intelligent caching of scan results

    Incremental Analysis: Only analyze changed components

    Memory Efficient: Stream processing for large datasets

🐛 Troubleshooting
Common Issues:

Command not found
bash

# Rebuild the app
bench build --app app_migrator
bench restart

Permission errors
bash

# Check bench permissions
bench --site [site-name] install-app app_migrator

Git push SSH issues
bash

# Test SSH connection
ssh -T git@github.com

# Use dry-run first
bench app-migrator git-push --dry-run

Branch status detection
bash

# If branch status shows "error", check GitHelper compatibility
# Fixed in v9.0.0 - ensure you have latest version

Debug Mode:
bash

# Enable verbose logging
bench --verbose app-migrator [command] [options]

🤝 Contributing

We welcome contributions! Please see our Contributing Guidelines for details.
Adding New Commands:

    Create command file in commands/ directory

    Define with @click.command('command-name')

    Register in commands/__init__.py:

python

from .your_command import your_command
app_migrator.add_command(your_command, 'command-name')

📄 License

MIT License. See LICENSE for details.
📞 Support

    Issues: GitHub Issues

    Documentation: GitHub Wiki

    Releases: GitHub Releases

🚀 Roadmap
✅ Completed in v9.0.0

    ✅ Enhanced Git push helper with multi-remote support

    ✅ Intelligent branch status detection

    ✅ SSH connection verification

    ✅ Comprehensive push summaries

🔄 In Progress

    Web interface for migration management

    API for integration with other tools

    Automated testing framework

    Plugin system for extensibility

    Performance optimizations for large benches

Version: v9.0.0+
Last Updated: February 2024
Maintainer: Rogerboy38
Frappe Compatibility: Version 15+

⭐ Star us on GitHub if you find this tool useful!
EOF

echo "✅ README.md updated with enhanced features"
text


Now let's commit this enhanced README and test the git-push command one more time with the actual push:

```bash
# Add the updated README
git add README.md

# Test the enhanced git-push with commit message
cd ~/frappe-bench
bench app-migrator git-push --app app_migrator --dry-run --message "feat: Enhanced README with v9.0.0 features"

# If it looks good, do the actual push
bench app-migrator git-push --app app_migrator --message "feat: Enhanced README with v9.0.0 features"

The enhanced README now includes:

    Clear highlighting of v9.0.0 enhancements

    Detailed git-push command documentation

    All features we tested and fixed

    Comprehensive examples and use cases

    Troubleshooting section for common issues

    Architecture overview

    Roadmap showing what's completed
