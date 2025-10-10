#!/bin/bash
# Auto-fix script for App Migrator repository structure
# Run this in your local repository root before pushing to GitHub

echo "========================================="
echo "App Migrator Repository Structure Fixer"
echo "========================================="
echo ""

# Check if we're in the right directory
if [ ! -d "app_migrator" ]; then
    echo "❌ Error: app_migrator directory not found!"
    echo "Please run this script from the repository root."
    exit 1
fi

echo "📂 Checking repository structure..."
echo ""

# Function to create file if missing
create_if_missing() {
    local file=$1
    local description=$2
    
    if [ ! -f "$file" ]; then
        echo "❌ Missing: $file"
        return 1
    else
        echo "✅ Found: $file"
        return 0
    fi
}

# Check critical files
MISSING=0

create_if_missing "setup.py" "Setup script" || MISSING=$((MISSING+1))
create_if_missing "package.json" "Package manifest" || MISSING=$((MISSING+1))
create_if_missing "requirements.txt" "Python dependencies" || MISSING=$((MISSING+1))
create_if_missing "pyproject.toml" "Project config" || MISSING=$((MISSING+1))
create_if_missing "modules.txt" "Module list" || MISSING=$((MISSING+1))
create_if_missing "patches.txt" "Patch list" || MISSING=$((MISSING+1))
create_if_missing "app_migrator/__init__.py" "App init" || MISSING=$((MISSING+1))
create_if_missing "app_migrator/hooks.py" "App hooks" || MISSING=$((MISSING+1))

echo ""

# Create setup.py if missing
if [ ! -f "setup.py" ]; then
    echo "📝 Creating setup.py..."
    cat > setup.py << 'SETUP_EOF'
from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in app_migrator/__init__.py
from app_migrator import __version__ as version

setup(
    name="app_migrator",
    version=version,
    description="Frappe App Migration Toolkit v5.0.0",
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
    echo "📝 Creating package.json..."
    cat > package.json << 'JSON_EOF'
{
  "name": "app_migrator",
  "version": "5.0.0",
  "description": "Frappe App Migration Toolkit - Ultimate Edition",
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
  "license": "MIT"
}
JSON_EOF
    echo "✅ Created package.json"
fi

# Ensure public directories exist
echo ""
echo "📁 Ensuring public directories exist..."
mkdir -p app_migrator/public/css
mkdir -p app_migrator/public/js
touch app_migrator/public/css/app_migrator.css
touch app_migrator/public/js/app_migrator.js
echo "✅ Public directories created"

# Check for common typos
echo ""
echo "🔍 Checking for common issues..."

# Check for app_migrator0 typo
if grep -r "app_migrator0" app_migrator/ 2>/dev/null | grep -v ".pyc" | grep -v "__pycache__"; then
    echo "❌ WARNING: Found 'app_migrator0' typo in code!"
    echo "   Please search and replace 'app_migrator0' with 'app_migrator'"
    MISSING=$((MISSING+1))
else
    echo "✅ No 'app_migrator0' typos found"
fi

# Check for wrong app_migrator.py file
if [ -f "app_migrator/app_migrator.py" ]; then
    echo "❌ WARNING: Found app_migrator/app_migrator.py"
    echo "   This file should not exist! It may conflict with imports."
    echo "   Consider removing it or renaming to something else."
    MISSING=$((MISSING+1))
fi

# Verify all __init__.py files exist
echo ""
echo "🔍 Checking for __init__.py files..."
for dir in app_migrator app_migrator/commands app_migrator/config app_migrator/templates app_migrator/templates/pages; do
    if [ -d "$dir" ]; then
        if [ ! -f "$dir/__init__.py" ]; then
            echo "❌ Missing: $dir/__init__.py"
            touch "$dir/__init__.py"
            echo "✅ Created: $dir/__init__.py"
        else
            echo "✅ Found: $dir/__init__.py"
        fi
    fi
done

echo ""
echo "========================================="
echo "Summary"
echo "========================================="

if [ $MISSING -eq 0 ]; then
    echo "✅ All checks passed!"
    echo ""
    echo "📤 Ready to commit and push:"
    echo "   git add ."
    echo "   git commit -m 'fix: Repository structure for Frappe installation'"
    echo "   git push origin main"
    echo ""
    echo "🏷️  Then create a new release:"
    echo "   git tag -a v5.0.1 -m 'Release v5.0.1 - Fixed installation issues'"
    echo "   git push origin v5.0.1"
else
    echo "⚠️  Found $MISSING issue(s) that need attention"
    echo "Please review the warnings above and fix them manually."
    echo ""
    echo "After fixing, run this script again to verify."
fi

echo ""
echo "========================================="
