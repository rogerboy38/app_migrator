#!/bin/bash
# Integration between MCP and safe-git scripts

SAFE_GIT_DIR="$HOME/frappe-bench/apps/app_migrator/scripts/safe-git"
MCP_DIR="$HOME/frappe-bench/apps/app_migrator/scripts/ai-mcp"

# Function to get GitHub status via MCP
github_status_mcp() {
    "$MCP_DIR/mcp-client.sh" repos | grep -o '"name":"[^"]*"' | cut -d'"' -f4
}

# Function to sync via safe-git
github_sync_safe() {
    if [[ -f "$SAFE_GIT_DIR/safe-sync.sh" ]]; then
        "$SAFE_GIT_DIR/safe-sync.sh"
    else
        echo "Safe sync script not found"
        return 1
    fi
}

# Function to show combined status
combined_status() {
    echo "=== GitHub Status (via MCP) ==="
    github_status_mcp
    
    echo ""
    echo "=== App Status ==="
    for app in rnd_nutrition rnd_warehouse_management amb_w_tds app_migrator; do
        if [[ -d ~/frappe-bench/apps/$app ]]; then
            cd ~/frappe-bench/apps/$app 2>/dev/null && {
                branch=$(git branch --show-current 2>/dev/null || echo "?")
                changes=$(git status --porcelain | wc -l)
                echo "$app: branch=$branch, changes=$changes"
            } || echo "$app: error"
        fi
    done
}

case "$1" in
    "status")
        combined_status
        ;;
    "sync")
        github_sync_safe
        ;;
    "help")
        echo "GitHub MCP Integration"
        echo "Commands: status, sync"
        ;;
    *)
        combined_status
        ;;
esac
