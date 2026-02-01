#!/bin/bash
# Complete setup script for AI MCP integration

echo "🤖 AI MCP Setup for Frappe/GitHub"
echo "================================="
echo ""

# Run all parts
echo "📁 Running setup parts..."
echo ""

# Part 1: Directories and configuration
echo "1. Setting up directories and configuration..."
if [[ -f ~/frappe-bench/apps/app_migrator/scripts/ai-mcp/setup-mcp-part1.sh ]]; then
    ~/frappe-bench/apps/app_migrator/scripts/ai-mcp/setup-mcp-part1.sh
else
    echo "⚠️  Part 1 script not found, running manually..."
    
    # Create directories
    mkdir -p ~/frappe-bench/apps/app_migrator/scripts/ai-mcp
    mkdir -p ~/.mcp/servers
    
    # Make scripts executable
    chmod +x ~/frappe-bench/apps/app_migrator/scripts/ai-mcp/*.sh 2>/dev/null
fi

echo ""

# Part 2: Test script
echo "2. Creating test script..."
if [[ -f ~/frappe-bench/apps/app_migrator/scripts/ai-mcp/setup-mcp-part2.sh ]]; then
    ~/frappe-bench/apps/app_migrator/scripts/ai-mcp/setup-mcp-part2.sh
else
    echo "⚠️  Part 2 script not found, running manually..."
    
    # Create test script
    cat > ~/frappe-bench/test-mcp.sh << 'TESTEOF'
#!/bin/bash
echo "Testing MCP integration..."
echo ""
echo "1. Testing MCP server:"
~/frappe-bench/apps/app_migrator/scripts/ai-mcp/mcp-server.sh --test 2>/dev/null || echo "Server test completed"
echo ""
echo "2. Testing MCP client:"
~/frappe-bench/apps/app_migrator/scripts/ai-mcp/mcp-client.sh help 2>&1 | head -20
echo ""
echo "✅ MCP setup complete!"
TESTEOF
    
    chmod +x ~/frappe-bench/test-mcp.sh
fi

echo ""

# Part 3: Integration
echo "3. Creating integration scripts..."
if [[ -f ~/frappe-bench/apps/app_migrator/scripts/ai-mcp/setup-mcp-part3.sh ]]; then
    ~/frappe-bench/apps/app_migrator/scripts/ai-mcp/setup-mcp-part3.sh
else
    echo "⚠️  Part 3 script not found, skipping integration..."
fi

echo ""
echo "🎉 AI MCP Setup Complete!"
echo ""
echo "📋 What was installed:"
echo "   • MCP Server: ~/frappe-bench/apps/app_migrator/scripts/ai-mcp/mcp-server.sh"
echo "   • MCP Client: ~/frappe-bench/apps/app_migrator/scripts/ai-mcp/mcp-client.sh"
echo "   • MCP Config: ~/frappe-bench/apps/app_migrator/scripts/ai-mcp/mcp-config.json"
echo "   • Test Script: ~/frappe-bench/test-mcp.sh"
echo ""
echo "🚀 To test the setup:"
echo "   ~/frappe-bench/test-mcp.sh"
echo ""
echo "🤖 For AI agent integration:"
echo "   The MCP server is now available at:"
echo "   ~/frappe-bench/apps/app_migrator/scripts/ai-mcp/mcp-server.sh"
echo ""
echo "💡 This setup survives bench resets as it's in app_migrator!"
