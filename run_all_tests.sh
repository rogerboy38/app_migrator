#!/bin/bash

# Master Test Runner for App Migrator
# Runs all test suites and provides comprehensive report

echo "🎯 App Migrator Master Test Suite"
echo "================================="
echo "Running all verification tests..."
echo ""

# Run quick test first
echo "1. QUICK TEST..."
./quick_test.sh
QUICK_RESULT=$?

echo ""

# Run simple test
echo "2. SIMPLE TEST SUITE..."
./simple_test.sh
SIMPLE_RESULT=$?

echo ""

# Run production verification
echo "3. PRODUCTION VERIFICATION..."
./production_verify.sh
PROD_RESULT=$?

echo ""
echo "================================="
echo "📊 TEST RESULTS SUMMARY:"
echo "   Quick Test: $([ $QUICK_RESULT -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "   Simple Test: $([ $SIMPLE_RESULT -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")" 
echo "   Production: $([ $PROD_RESULT -eq 0 ] && echo "✅ PASS" || echo "❌ FAIL")"
echo ""

if [ $QUICK_RESULT -eq 0 ] && [ $SIMPLE_RESULT -eq 0 ] && [ $PROD_RESULT -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED!"
    echo "🚀 App Migrator is fully operational and production-ready!"
    echo "💪 Frappe v15 compatibility confirmed!"
else
    echo "⚠️  Some tests failed. Please check the output above."
    echo "🔧 System may need attention."
fi

echo "================================="
