#!/bin/bash
# Quick GitHub Setup for App Migrator
# Run this in any bench to set up GitHub integration

echo "⚡ Quick GitHub Setup"
echo "===================="
echo ""

# Create SSH key if needed
if [[ ! -f ~/.ssh/id_ed25519 ]]; then
    echo "🔑 Generating SSH key..."
    mkdir -p ~/.ssh
    ssh-keygen -t ed25519 -C "rogerboy38@gmail.com" -f ~/.ssh/id_ed25519 -N "" -q
    
    echo ""
    echo "📋 PUBLIC KEY (add to GitHub):"
    echo "================================"
    cat ~/.ssh/id_ed25519.pub
    echo "================================"
    echo ""
    echo "🔗 Add at: https://github.com/settings/keys"
    echo ""
    read -p "📝 Press Enter after adding key to GitHub..." -r
fi

# Configure SSH
echo "🔧 Configuring SSH..."
cat > ~/.ssh/config << 'CONFIGEOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
CONFIGEOF
chmod 600 ~/.ssh/config

# Test connection
echo "🔗 Testing connection..."
if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    echo "✅ GitHub SSH connection working!"
else
    echo "❌ GitHub SSH connection failed"
    exit 1
fi

# Create symlink to safe-sync.sh in bench root
echo "🔗 Creating convenience symlinks..."
ln -sf ~/frappe-bench/apps/app_migrator/scripts/safe-git/safe-sync.sh ~/frappe-bench/safe-sync.sh 2>/dev/null
ln -sf ~/frappe-bench/apps/app_migrator/scripts/safe-git/quick-setup.sh ~/frappe-bench/setup-github.sh 2>/dev/null

echo ""
echo "🎉 GitHub Setup Complete!"
echo ""
echo "📋 Available commands:"
echo "  • ~/frappe-bench/safe-sync.sh  - Safe GitHub synchronization"
echo "  • bench app-migrator --help    - App migration tools"
echo ""
echo "🔗 Your GitHub repositories:"
echo "  • https://github.com/rogerboy38/rnd_warehouse_management"
echo "  • https://github.com/rogerboy38/rnd_nutrition2"
echo "  • https://github.com/rogerboy38/amb_w_tds"
echo "  • https://github.com/rogerboy38/app_migrator"
