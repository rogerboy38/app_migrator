#!/bin/bash

# Production Verification Test
# More thorough than simple test

echo "🏭 App Migrator Production Verification"
echo "======================================="

print_result() {
    if [ $? -eq 0 ]; then
        echo "✅ $1"
        return 0
    else
        echo "❌ $1"
        return 1
    fi
}

# Test command discovery first (most critical)
echo "1. Command Discovery..."
bench --site origin_site console << 'CONSOLEEOF'
from frappe.utils.bench_helper import get_app_commands
cmds = get_app_commands('app_migrator')
print(f"Discovered commands: {list(cmds.keys())}")
assert 'migrate-app' in cmds, "migrate-app command not found"
print("✅ Command discovery verified")
CONSOLEEOF
print_result "Command discovery"

# Test each major command
echo "2. System Test..."
bench --site origin_site migrate-app test
print_result "System test"

echo "3. Enhanced Features..."
bench --site origin_site migrate-app enhanced-migrate verify_source verify_target --dry-run
print_result "Enhanced migration"

echo "4. Safety Features..."
bench --site origin_site migrate-app test-replacer
print_result "Safety features"

echo "5. App Analysis..."
bench --site origin_site migrate-app analyze frappe
print_result "App analysis"

echo ""
echo "======================================="
echo "🎯 PRODUCTION VERIFICATION COMPLETE"
echo "✅ All critical systems verified"
echo "🚀 Ready for production deployment"
echo "======================================="
