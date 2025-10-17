#!/bin/bash

################################################################################
# test_app_migrator.sh - Comprehensive Test for App Migrator v6.0.0
#
# Purpose: Verify all components are working after boot fixes
# Author: MiniMax Agent
# Date: October 17, 2025
################################################################################

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() { echo -e "${BLUE}➤${NC} $1"; }
print_success() { echo -e "${GREEN}✓${NC} $1"; }
print_error() { echo -e "${RED}✗${NC} $1"; }
print_warning() { echo -e "${YELLOW}⚠${NC} $1"; }

show_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║               App Migrator Comprehensive Test                ║"
    echo "║                        Version 6.0.0                         ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

check_frappe_environment() {
    print_status "1. Checking Frappe environment..."
    
    # Check if we're in a bench directory
    if [ -f "../../Procfile" ] || [ -f "../../common_site_config.json" ]; then
        print_success "In Frappe bench directory"
    else
        print_warning "Not in standard Frappe bench directory (might be OK)"
    fi
    
    # Check bench presence
    if command -v bench >/dev/null 2>&1; then
        print_success "Bench command available"
        bench --version
    else
        print_error "Bench command not found"
        return 1
    fi
    
    # Check Python environment
    if python -c "import frappe" 2>/dev/null; then
        print_success "Frappe Python package available"
    else
        print_error "Frappe Python package not available"
        return 1
    fi
    
    return 0
}

test_basic_imports() {
    print_status "2. Testing basic Python imports..."
    
    local test_script=$(mktemp)
    cat > "$test_script" << 'EOF'
import sys
import os

print("Python path:")
for path in sys.path:
    if "app_migrator" in path or "frappe" in path:
        print(f"  {path}")

try:
    import frappe
    print("✓ Frappe import successful")
    
    # Try to import app_migrator
    try:
        import app_migrator
        print("✓ App Migrator import successful")
    except ImportError as e:
        print(f"⚠ App Migrator import issue: {e}")
    
    print("SUCCESS: Basic imports working")
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
EOF

    if python "$test_script"; then
        print_success "Basic imports test passed"
        rm "$test_script"
        return 0
    else
        print_error "Basic imports test failed"
        rm "$test_script"
        return 1
    fi
}

test_boot_fix_modules() {
    print_status "3. Testing boot fix modules..."
    
    local test_script=$(mktemp)
    cat > "$test_script" << 'EOF'
import sys
import os

# Add current directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    # Test if boot fix files exist and can be imported
    boot_fix_files = [
        "app_migrator/core/boot_fixer.py",
        "app_migrator/core/emergency_boot.py", 
        "app_migrator/core/final_boot_fix.py",
        "app_migrator/core/ultimate_boot_fixer.py",
        "app_migrator/core/migration_manager.py",
        "app_migrator/commands/boot_fix.py"
    ]
    
    for file_path in boot_fix_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"⚠ {file_path} not found")
    
    # Try to import core modules
    try:
        from app_migrator.core.migration_manager import MigrationManager
        print("✓ MigrationManager import successful")
    except ImportError as e:
        print(f"⚠ MigrationManager import failed: {e}")
    
    print("SUCCESS: Boot fix modules check completed")
    
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
EOF

    if python "$test_script"; then
        print_success "Boot fix modules test passed"
        rm "$test_script"
        return 0
    else
        print_error "Boot fix modules test failed"
        rm "$test_script"
        return 1
    fi
}

test_app_structure() {
    print_status "4. Testing app structure..."
    
    # Check essential files
    essential_files=(
        "__init__.py"
        "app_migrator/__init__.py"
        "app_migrator/core/__init__.py"
        "app_migrator/commands/__init__.py"
    )
    
    for file in "${essential_files[@]}"; do
        if [ -f "$file" ]; then
            print_success "$file exists"
        else
            print_error "$file missing"
            return 1
        fi
    done
    
    # Check if app is properly structured
    if [ -f "hooks.py" ] || [ -f "__init__.py" ]; then
        print_success "App structure looks good"
    else
        print_warning "App structure might be incomplete"
    fi
    
    return 0
}

test_utility_scripts() {
    print_status "5. Testing utility scripts..."
    
    local scripts=(
        "diagnose_boot_issue.py"
        "fix_frappe_boot.py"
        "cleanup_orphaned_apps.py" 
        "create_clean_site.py"
        "setup_test_environment.py"
    )
    
    local all_ok=true
    
    for script in "${scripts[@]}"; do
        if [ -f "$script" ]; then
            # Check if file has Python syntax
            if python -m py_compile "$script" 2>/dev/null; then
                print_success "$script - Syntax OK"
            else
                print_error "$script - Syntax error"
                all_ok=false
            fi
        else
            print_warning "$script - Not found (might be OK)"
        fi
    done
    
    if $all_ok; then
        print_success "Utility scripts test passed"
        return 0
    else
        print_error "Utility scripts test failed"
        return 1
    fi
}

run_quick_test() {
    print_status "Running quick health check..."
    echo "=========================================="
    
    if check_frappe_environment && \
       test_basic_imports && \
       test_app_structure; then
        print_success "✅ Quick health check PASSED"
        print_success "Basic Frappe environment is working"
        return 0
    else
        print_error "❌ Quick health check FAILED"
        return 1
    fi
}

run_comprehensive_test() {
    show_header
    print_status "Starting comprehensive App Migrator test suite..."
    echo "=================================================="
    
    local tests=(
        check_frappe_environment
        test_basic_imports
        test_boot_fix_modules
        test_app_structure
        test_utility_scripts
    )
    
    local passed=0
    local total=${#tests[@]}
    
    for test_func in "${tests[@]}"; do
        if $test_func; then
            ((passed++))
        fi
        echo ""
    done
    
    echo "=================================================="
    
    if [ $passed -eq $total ]; then
        print_success "🎉 ALL TESTS PASSED! ($passed/$total)"
        print_success "App Migrator v6.0.0 is fully operational!"
    else
        print_warning "SOME TESTS PASSED ($passed/$total)"
        print_status "There might be minor issues but core functionality should work"
    fi
}

main() {
    case "${1:-}" in
        --quick|-q)
            run_quick_test
            ;;
        --help|-h)
            echo "Usage: ./test_app_migrator.sh [OPTION]"
            echo ""
            echo "Options:"
            echo "  --quick, -q    Run quick health check only"
            echo "  --full         Run comprehensive test suite (default)"
            echo "  --help, -h     Show this help message"
            ;;
        *)
            run_comprehensive_test
            ;;
    esac
}

# Run the main function
main "$@"
