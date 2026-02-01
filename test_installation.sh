#!/bin/bash
# Test script to verify app_migrator installation

echo "🧪 Testing app_migrator installation..."
echo "======================================"

# Check if we're in a bench
if [ ! -f "bench" ] && [ ! -d "apps" ]; then
    echo "❌ Not in a bench directory"
    exit 1
fi

# Activate virtual environment if exists
if [ -f "env/bin/activate" ]; then
    source env/bin/activate
    echo "✅ Virtual environment activated"
fi

echo ""
echo "1. Installing dependencies..."
pip install keyring>=25.0 requests>=2.31.0

echo ""
echo "2. Installing app_migrator..."
bench get-app app_migrator https://github.com/rogerboy38/app_migrator

echo ""
echo "3. Installing on site..."
SITE=$(bench list-sites 2>/dev/null | tail -n +2 | head -1 | xargs)
if [ -n "$SITE" ]; then
    bench --site "$SITE" install-app app_migrator
else
    bench new-site test-app-migrator --admin-password admin --force
    bench --site test-app-migrator install-app app_migrator
fi

echo ""
echo "4. Building..."
bench build --app app_migrator
bench restart

echo ""
echo "5. Testing commands..."
bench app-migrator --help | grep -E "(git|api-key|health)"

echo ""
echo "✅ Installation test complete!"
echo "If you see git and api-key commands, installation was successful."
