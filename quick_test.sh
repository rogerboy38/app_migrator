#!/bin/bash
# Quick one-command test
echo "🔧 Quick App Migrator Test..."
bench --site origin_site migrate-app test && \
bench --site origin_site migrate-app status && \
echo "✅ Quick test passed!" || echo "❌ Quick test failed!"
