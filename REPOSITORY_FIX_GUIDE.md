# 🔧 Repository Structure Fix Guide

## Problem Diagnosis

Your GitHub repository structure causes installation failures because:

1. **Missing `setup.py` at root level** - Frappe needs this for installation
2. **Possible module name conflicts** - The error `app_migrator0` suggests naming issues
3. **Build configuration issues** - Missing or incorrect build files

## Current Structure Issues

When cloning from your GitHub repo, users get:
```
app_migrator/
├── app_migrator/
│   ├── app_migrator.py    ❌ Wrong! Should not exist
│   ├── commands/
│   └── ...
├── modules.txt
├── patches.txt
└── ...
```

## Required Frappe App Structure

```
app_migrator/                          # Repository root
├── app_migrator/                      # Main app package
│   ├── __init__.py                    # App initialization
│   ├── hooks.py                       # Frappe hooks
│   ├── commands/                      # Commands module
│   │   ├── __init__.py
│   │   ├── analysis_tools.py
│   │   ├── database_schema.py
│   │   ├── data_quality.py
│   │   └── ...
│   ├── config/                        # Configuration
│   │   └── __init__.py
│   ├── public/                        # Public assets
│   │   ├── css/
│   │   └── js/
│   ├── templates/                     # Templates
│   │   ├── __init__.py
│   │   └── pages/
│   │       └── __init__.py
│   └── www/                          # Web resources
├── .github/                          # GitHub workflows
├── modules.txt                        # Module list
├── patches.txt                        # Patch list
├── pyproject.toml                     # Python project config
├── requirements.txt                   # Dependencies
├── setup.py                          # Setup script (CRITICAL!)
├── README.md                         # Documentation
├── LICENSE                           # License file
└── ... (other docs)
```

## Files That MUST Exist

### 1. `setup.py` (Root Level) - CRITICAL!

Create this file at the repository root:

```python
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in app_migrator/__init__.py
from app_migrator import __version__ as version

setup(
    name="app_migrator",
    version=version,
    description="Frappe App Migration Toolkit",
    author="Frappe Community",
    author_email="fcrm@amb-wellness.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
```

### 2. `app_migrator/__init__.py`

Already correct in your workspace - keep it as is.

### 3. `app_migrator/hooks.py`

Already correct - keep it as is.

### 4. `package.json` (Root Level)

Create this file:

```json
{
  "name": "app_migrator",
  "version": "5.0.0",
  "description": "Frappe App Migration Toolkit",
  "main": "app_migrator/public/js/app_migrator.js",
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/rogerboy38/app_migrator.git"
  },
  "keywords": [
    "frappe",
    "migration",
    "erpnext"
  ],
  "author": "Frappe Community",
  "license": "MIT",
  "bugs": {
    "url": "https://github.com/rogerboy38/app_migrator/issues"
  },
  "homepage": "https://github.com/rogerboy38/app_migrator#readme"
}
```

### 5. Ensure Public Directories Exist

```bash
# Create required directories
mkdir -p app_migrator/public/css
mkdir -p app_migrator/public/js

# Create placeholder files
touch app_migrator/public/css/app_migrator.css
touch app_migrator/public/js/app_migrator.js
```

## Step-by-Step Fix Instructions

### Step 1: Clean Your Current Repository

```bash
cd /path/to/your/local/app_migrator
git status
git add .
git commit -m "Backup before restructuring"
```

### Step 2: Create Missing Files

```bash
# Create setup.py at root
cat > setup.py << 'EOF'
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in app_migrator/__init__.py
from app_migrator import __version__ as version

setup(
    name="app_migrator",
    version=version,
    description="Frappe App Migration Toolkit",
    author="Frappe Community",
    author_email="fcrm@amb-wellness.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
EOF

# Create package.json at root
cat > package.json << 'EOF'
{
  "name": "app_migrator",
  "version": "5.0.0",
  "description": "Frappe App Migration Toolkit",
  "main": "app_migrator/public/js/app_migrator.js",
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/rogerboy38/app_migrator.git"
  },
  "keywords": ["frappe", "migration", "erpnext"],
  "author": "Frappe Community",
  "license": "MIT"
}
EOF

# Ensure public directories exist
mkdir -p app_migrator/public/css
mkdir -p app_migrator/public/js
touch app_migrator/public/css/app_migrator.css
touch app_migrator/public/js/app_migrator.js
```

### Step 3: Verify Structure

```bash
# Check critical files
ls -la setup.py
ls -la package.json
ls -la app_migrator/__init__.py
ls -la app_migrator/hooks.py
ls -la modules.txt
ls -la patches.txt
ls -la requirements.txt
ls -la pyproject.toml

# Should all exist!
```

### Step 4: Update .gitignore

Make sure these are in your `.gitignore`:

```
*.pyc
*.egg-info
__pycache__/
.DS_Store
*.swp
*.swo
node_modules/
.vscode/
.idea/
*.log
build/
dist/
```

### Step 5: Commit and Push

```bash
git add .
git commit -m "fix: Add missing setup.py and package.json for proper Frappe app installation"
git push origin main
```

### Step 6: Create a New Tag

```bash
# Tag the fixed version
git tag -a v5.0.1 -m "Release v5.0.1 - Fixed repository structure for Frappe installation"
git push origin v5.0.1
```

## Testing the Fix

After pushing to GitHub, test the installation:

```bash
# On your test bench
cd ~/frappe-bench-v5

# Remove old version
rm -rf apps/app_migrator

# Fresh install from GitHub
bench get-app app_migrator https://github.com/rogerboy38/app_migrator.git --branch v5.0.1

# Should work now!
```

## Common Issues and Solutions

### Issue 1: "ModuleNotFoundError: No module named 'app_migrator0'"

**Cause**: Typo in module name somewhere
**Fix**: Search for any occurrence of `app_migrator0` in all Python files:

```bash
grep -r "app_migrator0" app_migrator/
```

If found, replace with `app_migrator`.

### Issue 2: "Cannot find setup.py"

**Cause**: Missing setup.py at root
**Fix**: Create setup.py as shown above

### Issue 3: Build fails with asset errors

**Cause**: Missing public directories
**Fix**: Create public/css and public/js directories with placeholder files

### Issue 4: "No such file or directory: modules.txt"

**Cause**: modules.txt not found
**Fix**: Ensure modules.txt is at repository root (same level as setup.py)

## Verification Checklist

Before pushing to GitHub, verify:

- [ ] `setup.py` exists at repository root
- [ ] `package.json` exists at repository root  
- [ ] `app_migrator/__init__.py` exists and has `__version__`
- [ ] `app_migrator/hooks.py` exists
- [ ] `modules.txt` exists at root
- [ ] `patches.txt` exists at root
- [ ] `requirements.txt` exists at root
- [ ] `pyproject.toml` exists at root
- [ ] `app_migrator/public/css/` directory exists
- [ ] `app_migrator/public/js/` directory exists
- [ ] All `__init__.py` files exist in Python packages
- [ ] No files named `app_migrator.py` in `app_migrator/` directory
- [ ] No typos like `app_migrator0` anywhere in code

## Quick Fix Script

Run this script to auto-fix common issues:

```bash
#!/bin/bash
# fix_repo_structure.sh

echo "Fixing App Migrator repository structure..."

# Create setup.py if missing
if [ ! -f "setup.py" ]; then
    cat > setup.py << 'SETUP_EOF'
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

from app_migrator import __version__ as version

setup(
    name="app_migrator",
    version=version,
    description="Frappe App Migration Toolkit",
    author="Frappe Community",
    author_email="fcrm@amb-wellness.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)
SETUP_EOF
    echo "✅ Created setup.py"
fi

# Create package.json if missing
if [ ! -f "package.json" ]; then
    cat > package.json << 'JSON_EOF'
{
  "name": "app_migrator",
  "version": "5.0.0",
  "description": "Frappe App Migration Toolkit",
  "main": "app_migrator/public/js/app_migrator.js",
  "scripts": {
    "test": "echo \"Error: no test specified\" && exit 1"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/rogerboy38/app_migrator.git"
  },
  "keywords": ["frappe", "migration", "erpnext"],
  "author": "Frappe Community",
  "license": "MIT"
}
JSON_EOF
    echo "✅ Created package.json"
fi

# Ensure public directories exist
mkdir -p app_migrator/public/css
mkdir -p app_migrator/public/js
touch app_migrator/public/css/app_migrator.css
touch app_migrator/public/js/app_migrator.js
echo "✅ Created public directories"

# Check for typos
if grep -r "app_migrator0" app_migrator/ 2>/dev/null; then
    echo "❌ Found 'app_migrator0' typo in code!"
    echo "Please fix these manually."
else
    echo "✅ No typos found"
fi

echo ""
echo "Structure fix complete! Verify with:"
echo "  ls -la setup.py package.json"
echo "  ls -la app_migrator/__init__.py"
echo ""
echo "Then commit and push:"
echo "  git add ."
echo "  git commit -m 'fix: Repository structure for Frappe installation'"
echo "  git push origin main"
```

## Need Help?

If issues persist after following this guide:

1. Check the error logs carefully
2. Verify all files are in the correct locations
3. Ensure no typos in file/module names
4. Test installation on a clean bench first
5. Review Frappe's app development documentation

---

**Last Updated**: October 11, 2025  
**For**: App Migrator v5.0.0+
