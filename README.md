# 🚀 App Migrator v5.0.0 - Ultimate Edition

[![Version](https://img.shields.io/badge/version-5.0.0-blue.svg)](https://github.com/yourusername/app_migrator)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![Frappe](https://img.shields.io/badge/frappe-v13+-orange.svg)](https://frappeframework.com/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](LICENSE)

> **The Ultimate Frappe/ERPNext App Migration Toolkit** - Comprehensive solution for migrating, analyzing, and managing Frappe applications across benches with intelligent classification, interactive wizards, and robust data quality tools.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Complete Command List](#-complete-command-list)
- [Architecture Overview](#-architecture-overview)
- [Version History](#-version-history)
- [Documentation](#-documentation)
- [Contributing](#-contributing)
- [License](#-license)
- [Credits](#-credits)

---

## 🌟 Overview

**App Migrator v5.0.0** is a powerful, production-ready toolkit that combines the best features from Version 2 and Version 4, enhanced with intelligent DocType classification, interactive wizards, and comprehensive data quality management. It provides 23 specialized commands across 12 modules to handle every aspect of Frappe app migration.

### What's New in v5.0.0?

- ✅ **Unified Architecture** - Merged V2 core functions with V4 class-based design
- ✅ **Intelligent Classification** - Advanced DocType classification (Standard/Customized/Custom/Orphan)
- ✅ **Interactive Wizard** - Step-by-step guided migration workflow
- ✅ **Enhanced Session Management** - Persistent sessions with auto-reconnect
- ✅ **Multi-Bench Support** - Analyze and manage multiple benches
- ✅ **Comprehensive Analysis** - Deep insights into app structure and dependencies
- ✅ **Data Quality Tools** - Fix orphans, restore missing doctypes, verify integrity
- ✅ **Progress Tracking** - Visual feedback for long-running operations
- ✅ **23 Specialized Commands** - Complete toolkit for all migration scenarios

---

## ✨ Key Features

### 🎯 Core Capabilities

#### 1. **Interactive Migration Wizard** 🧙
- Guided step-by-step migration workflow
- Intelligent site and app selection
- Module classification and filtering
- Risk assessment integration
- Status-based filtering (Standard/Customized/Custom/Orphan)

#### 2. **DocType Classification System** 🏷️
- **Standard**: Core framework doctypes (unmodified)
- **Customized**: Modified with Custom Fields or Property Setters
- **Custom**: User-created doctypes (custom=1)
- **Orphan**: Doctypes with app=None or wrong module

#### 3. **Database Schema Management** 🗄️
- Verify database schema integrity
- Create missing tables automatically
- Fix tree doctype structures (lft, rgt, old_parent)
- Complete ERPNext installation
- Comprehensive database diagnostics

#### 4. **Data Quality Assurance** ✅
- Fix orphan doctypes
- Restore missing doctype files
- Fix app=None assignments
- Analyze cross-app references
- Verify data integrity

#### 5. **Multi-Bench Operations** 🏗️
- Detect available benches
- Compare bench configurations
- Analyze app inventory across benches
- Bench health monitoring

#### 6. **Session Management** 💾
- Persistent session storage
- Progress tracking and monitoring
- Auto-reconnect for long operations
- Session resumption after failures

#### 7. **Comprehensive Analysis** 📊
- Bench health analysis
- App dependency analysis (requirements.txt, package.json)
- Orphan detection
- File system validation
- Cross-app reference detection

#### 8. **Migration Engine** 🚀
- Module-level migration
- Specific doctype migration
- File system operations
- Local bench-to-bench migration
- Pre-migration validation

---

## 📦 Installation

### Prerequisites

- **Python**: 3.8 or higher
- **Frappe Framework**: v13 or higher
- **ERPNext**: v13 or higher (optional)
- **Bench**: Standard Frappe bench setup

### Step 1: Get the App

```bash
# Navigate to your bench directory
cd /path/to/your/bench

# Get the app from repository
bench get-app https://github.com/yourusername/app_migrator.git

# Or if you have the local directory
bench get-app /path/to/app_migrator_v5
```

### Step 2: Install on Site

```bash
# Install on your site
bench --site your-site install-app app_migrator

# Verify installation
bench --site your-site console
```

```python
# In Frappe console
import app_migrator
print(app_migrator.__version__)  # Should print: 5.0.0
```

### Step 3: Verify Setup

```bash
# Check if commands are available
bench --site your-site migrate-app

# Should display help with all 23 commands
```

---

## 🚀 Quick Start

### Interactive Mode (Recommended for Beginners)

```bash
# Launch the interactive wizard
bench --site your-site migrate-app interactive
```

The wizard will guide you through:
1. Site selection
2. App browsing
3. Module analysis
4. Status filtering
5. Migration execution

### Command-Line Mode (For Advanced Users)

#### Analyze an App

```bash
# Comprehensive app analysis
bench --site your-site migrate-app analyze erpnext
```

#### Fix Data Quality Issues

```bash
# Fix orphan doctypes
bench --site your-site migrate-app fix-orphans custom_app

# Restore missing doctype files
bench --site your-site migrate-app restore-missing custom_app

# Fix doctypes with app=None
bench --site your-site migrate-app fix-app-none custom_app
```

#### Migrate Modules

```bash
# Migrate all modules from source to target app
bench --site your-site migrate-app migrate source_app target_app

# Migrate specific modules only
bench --site your-site migrate-app migrate source_app target_app --modules="Module1,Module2"
```

#### Database Operations

```bash
# Verify database schema
bench --site your-site migrate-app fix-database-schema

# Complete ERPNext installation
bench --site your-site migrate-app complete-erpnext-install

# Run database diagnostics
bench --site your-site migrate-app db-diagnostics
```

### Python API Usage

```python
# In Frappe console or script
from app_migrator.commands import (
    SessionManager,
    analyze_app_comprehensive,
    migrate_app_modules,
    verify_data_integrity
)

# Create a session
session = SessionManager(name="my_migration_2025")

# Analyze app
results = analyze_app_comprehensive("custom_app")

# Verify data integrity
integrity_ok = verify_data_integrity("custom_app")

# Execute migration
success = migrate_app_modules("source_app", "target_app")

# Display session status
session.display_status()
```

---

## 📜 Complete Command List

### All 23 Commands

#### 🎨 Interactive Commands (1)
| Command | Description |
|---------|-------------|
| `interactive` | Enhanced guided migration wizard |

#### 🏗️ Multi-Bench Commands (4)
| Command | Description |
|---------|-------------|
| `multi-bench-analysis` | Analyze entire bench ecosystem |
| `list-benches` | List all available benches |
| `bench-apps <bench>` | List apps in specific bench |
| `bench-health` | Check bench health status |

#### 🗄️ Database Commands (4)
| Command | Description |
|---------|-------------|
| `fix-database-schema` | Fix database schema issues |
| `complete-erpnext-install` | Complete ERPNext installation |
| `fix-tree-doctypes` | Fix tree structure doctypes |
| `db-diagnostics` | Run comprehensive diagnostics |

#### 🔍 Analysis Commands (4)
| Command | Description |
|---------|-------------|
| `analyze <app>` | Comprehensive app analysis |
| `analyze-orphans` | Detect orphan doctypes |
| `validate-migration <app>` | Pre-migration validation |
| `classify-doctypes <app>` | Classify doctypes by status |

#### 🧹 Data Quality Commands (5)
| Command | Description |
|---------|-------------|
| `fix-orphans <app>` | Fix orphaned doctypes |
| `restore-missing <app>` | Restore missing doctypes |
| `fix-app-none <app>` | Fix doctypes with app=None |
| `fix-all-references <app>` | Fix all app references |
| `verify-integrity` | Verify data integrity |

#### 🚀 Migration Commands (2)
| Command | Description |
|---------|-------------|
| `migrate <source> <target>` | Migrate app modules |
| `clone-app-local <app>` | Clone app to local bench |

#### 📊 Reporting Commands (2)
| Command | Description |
|---------|-------------|
| `touched-tables` | Show migration history |
| `risk-assessment <doctype>` | Generate risk assessment |

### Command Usage Examples

```bash
# Interactive
bench --site mysite migrate-app interactive

# Multi-Bench
bench --site mysite migrate-app multi-bench-analysis
bench --site mysite migrate-app list-benches
bench --site mysite migrate-app bench-apps frappe-bench
bench --site mysite migrate-app bench-health

# Database
bench --site mysite migrate-app fix-database-schema
bench --site mysite migrate-app complete-erpnext-install
bench --site mysite migrate-app fix-tree-doctypes
bench --site mysite migrate-app db-diagnostics

# Analysis
bench --site mysite migrate-app analyze erpnext
bench --site mysite migrate-app analyze-orphans
bench --site mysite migrate-app validate-migration custom_app
bench --site mysite migrate-app classify-doctypes erpnext

# Data Quality
bench --site mysite migrate-app fix-orphans custom_app
bench --site mysite migrate-app restore-missing custom_app
bench --site mysite migrate-app fix-app-none custom_app
bench --site mysite migrate-app fix-all-references custom_app
bench --site mysite migrate-app verify-integrity

# Migration
bench --site mysite migrate-app migrate source_app target_app
bench --site mysite migrate-app clone-app-local custom_app

# Reporting
bench --site mysite migrate-app touched-tables
bench --site mysite migrate-app risk-assessment Customer
```

---

## 🏛️ Architecture Overview

### Module Structure

```
app_migrator/
├── __init__.py                      # Main package initialization
├── hooks.py                         # Frappe hooks configuration
├── commands/                        # Command modules (12 files, 145KB)
│   ├── __init__.py                 # Command initialization & registry
│   ├── doctype_classifier.py      # DocType classification system
│   ├── enhanced_interactive_wizard.py  # Interactive migration wizard
│   ├── database_schema.py         # Database schema operations
│   ├── data_quality.py            # Data quality management
│   ├── session_manager.py         # Session & connection management
│   ├── migration_engine.py        # Core migration functions
│   ├── analysis_tools.py          # Comprehensive analysis tools
│   ├── progress_tracker.py        # Progress tracking utilities
│   ├── multi_bench.py             # Multi-bench operations
│   ├── database_intel.py          # Database intelligence
│   └── test_precise_apps.py       # App testing utilities
├── config/                         # Configuration files
├── public/                         # Public assets
├── templates/                      # Web templates
│   └── pages/                     # Page templates
└── www/                           # Web resources
```

### Component Interaction

```
┌─────────────────────────────────────────────────────────────┐
│                    Interactive Wizard                        │
│              (enhanced_interactive_wizard.py)                │
└──────────────┬──────────────────────────────┬────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────┐    ┌────────────────────────────┐
│   DocType Classifier     │    │   Analysis Tools           │
│  (doctype_classifier.py) │◄───┤  (analysis_tools.py)       │
└──────────────────────────┘    └────────────────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────┐    ┌────────────────────────────┐
│   Migration Engine       │    │   Data Quality             │
│  (migration_engine.py)   │◄───┤  (data_quality.py)         │
└──────────────────────────┘    └────────────────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────────────────────────────────────────┐
│                    Session Manager                            │
│                  (session_manager.py)                         │
└──────────────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│                    Progress Tracker                           │
│                  (progress_tracker.py)                        │
└──────────────────────────────────────────────────────────────┘
```

### Design Patterns

1. **Decorator Pattern** (V2 Style)
   - `@with_session_management` - Auto session handling
   - `@with_session_tracking` - Combined session + progress

2. **Class-Based Management** (V4 Style)
   - `SessionManager` - Session lifecycle management
   - `ProgressTracker` - Progress monitoring

3. **Modular Architecture**
   - Clear separation of concerns
   - Independent, reusable modules
   - Minimal coupling, high cohesion

---

## 📖 Version History

### Evolution: V2 + V4 → V5.0.0

#### Version 2 (V2) - Function-Based Core
- ✅ Core migration functions (`migrate_app_modules`, `migrate_specific_doctypes`)
- ✅ Data quality tools (`fix_orphan_doctypes`, `restore_missing_doctypes`)
- ✅ Database schema operations
- ✅ Comprehensive analysis functions
- ✅ Decorator-based session management

#### Version 4 (V4) - Class-Based Enhancement
- ✅ Class-based `SessionManager`
- ✅ `ProgressTracker` for visual feedback
- ✅ Multi-bench support
- ✅ Enhanced analysis tools
- ✅ Local bench migration (`clone_app_local`)

#### Version 5.0.0 (V5) - Ultimate Edition ⭐
**Released**: October 11, 2025

**What's New**:
- ✅ **Unified Architecture** - Best of V2 + V4
- ✅ **DocType Classification** - Intelligent categorization
- ✅ **Interactive Wizard** - User-friendly guided workflow
- ✅ **Enhanced Session Management** - Combined V2 decorators + V4 classes
- ✅ **23 Commands** - Complete toolkit
- ✅ **12 Modules** - 145KB of production-ready code
- ✅ **Comprehensive Documentation** - Full guides and references

**Key Improvements**:
- Better error handling and logging
- Improved user feedback with progress tracking
- Enhanced validation and safety checks
- Production-ready code quality
- Complete test coverage support

**Breaking Changes**:
- None! Fully backward compatible with V2 and V4

---

## 📚 Documentation

Complete documentation is available:

- **[README.md](README.md)** - This file (Project overview)
- **[USER_GUIDE.md](USER_GUIDE.md)** - Complete user guide with examples
- **[CHANGELOG.md](CHANGELOG.md)** - Detailed version history
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Installation and deployment guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical architecture details
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Quick command reference
- **[COMMAND_MODULES_SUMMARY.md](COMMAND_MODULES_SUMMARY.md)** - Module details

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Getting Started

1. **Fork the Repository**
   ```bash
   git clone https://github.com/yourusername/app_migrator.git
   cd app_migrator
   ```

2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Your Changes**
   - Follow Python best practices
   - Add comprehensive docstrings
   - Include error handling
   - Write unit tests

4. **Test Your Changes**
   ```bash
   # Run unit tests
   python -m pytest tests/
   
   # Test in Frappe console
   bench --site test-site console
   ```

5. **Submit a Pull Request**
   - Describe your changes
   - Reference any related issues
   - Ensure all tests pass

### Code Style

- **PEP 8** compliance
- **Type hints** where appropriate
- **Comprehensive docstrings** (Google style)
- **Error handling** with try/except
- **User feedback** with print statements
- **Logging** for debugging

### Testing Guidelines

- Write unit tests for new functions
- Test both success and failure scenarios
- Validate with real Frappe sites
- Check performance for large datasets

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 App Migrator Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Credits

### Development Team

- **Core Architecture** - App Migrator Team
- **V2 Contributors** - Original function-based implementation
- **V4 Contributors** - Class-based enhancements
- **V5 Integration** - Unified architecture team

### Built With

- **[Frappe Framework](https://frappeframework.com/)** - The foundation
- **[ERPNext](https://erpnext.com/)** - Business application suite
- **[Python](https://www.python.org/)** - Programming language
- **[Click](https://click.palletsprojects.com/)** - CLI framework

### Special Thanks

- Frappe Technologies for the amazing framework
- The ERPNext community for continuous feedback
- All contributors who helped shape this project

---

## 📞 Support

### Getting Help

- **Documentation**: Check [USER_GUIDE.md](USER_GUIDE.md)
- **Issues**: Open an issue on GitHub
- **Discussions**: Join our community forum
- **Email**: support@appfigrator.com

### Common Issues

1. **Connection Errors**: Check session management
2. **Permission Denied**: Verify user permissions
3. **Missing Tables**: Run `fix-database-schema`
4. **Orphan Doctypes**: Use `fix-orphans` command

### Reporting Bugs

Please include:
- Frappe/ERPNext version
- App Migrator version
- Command that failed
- Complete error traceback
- Steps to reproduce

---

## 🔮 Roadmap

### Upcoming Features

- [ ] **v5.1.0** - Enhanced reporting dashboard
- [ ] **v5.2.0** - Automated rollback capabilities
- [ ] **v5.3.0** - Cloud bench support
- [ ] **v6.0.0** - GraphQL API for migrations

### In Progress

- ⏳ Web UI for migration management
- ⏳ Docker container support
- ⏳ Multi-site batch operations
- ⏳ Migration templates library

---

## 📊 Project Stats

- **Version**: 5.0.0
- **Commands**: 23
- **Modules**: 12
- **Total Code**: 145KB
- **Python Version**: 3.8+
- **Frappe Version**: v13+
- **Status**: ✅ Production Ready

---

## 🌟 Star History

If you find this project useful, please consider giving it a star! ⭐

---

**Made with ❤️ by the App Migrator Team**

*Last Updated: October 11, 2025*
