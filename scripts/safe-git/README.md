# Safe Git Tools for App Migrator

## Overview
Safe, confirmation-based GitHub synchronization tools that survive bench resets by being stored in the app_migrator repository itself.

## Files

### 1. `safe-sync.sh`
Main safe synchronization script:
- Checks SSH connection
- Shows status of all apps
- Asks for confirmation before any push
- Uses `--force-with-lease` instead of `--force` when needed
- Provides detailed feedback

### 2. `github-config.sh`
Configuration file:
- GitHub user and repository mappings
- SSH configuration
- Centralized settings

### 3. `quick-setup.sh`
One-time setup script:
- Generates SSH keys if needed
- Configures SSH
- Tests connection
- Creates convenience symlinks

## Usage

### Initial Setup (in any bench):
```bash
cd ~/frappe-bench/apps/app_migrator/scripts/safe-git
./quick-setup.sh
