# 🏗️ App Migrator - Enterprise Multi-Bench Migration System

**Version**: 4.0.0  
**Frappe Compatibility**: v15+  
**Status**: Production Ready 🚀

## 📚 Documentation Structure

### Core Documentation
- **[README.md](README.md)** - This file (overview and quick start)
- **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Step-by-step migration procedures
- **[TECHNICAL_SPEC.md](ai_agent_frappe_migration_technical_specification.md)** - Technical specifications

### Core Code
- **[migrator.py](migrator.py)** - Main migration engine
- **commands/** - Multi-bench command modules

## 🎯 Quick Overview

App Migrator is an enterprise-grade tool for managing Frappe application migrations across multiple bench environments with intelligent analysis and smart recommendations.

## 🚀 Quick Start

```bash
# Install
bench get-app app_migrator https://github.com/rogerboy38/app_migrator.git
bench --site <your-site> install-app app_migrator

# Basic usage
bench migrate-app multi-bench-analysis
bench migrate-app smart-recommendation
