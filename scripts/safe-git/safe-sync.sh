#!/bin/bash
# SAFE GitHub Sync - Part of App Migrator
# Safe, confirmation-based GitHub synchronization
# Survives bench resets via GitHub storage

echo "🔒 SAFE GitHub Sync (App Migrator)"
echo "================================="
echo "Version: 1.0.0"
echo "Date: $(date)"
echo "Bench: $(hostname)"
echo ""

# Source configuration
CONFIG_DIR="$HOME/frappe-bench/apps/app_migrator/scripts/safe-git"
if [[ -f "$CONFIG_DIR/github-config.sh" ]]; then
    source "$CONFIG_DIR/github-config.sh"
else
    # Default configuration
    GITHUB_USER="rogerboy38"
    declare -A GITHUB_REPOS=(
        ["rnd_nutrition"]="git@github.com:rogerboy38/rnd_nutrition2.git"
        ["rnd_warehouse_management"]="git@github.com:rogerboy38/rnd_warehouse_management.git"
        ["amb_w_tds"]="git@github.com:rogerboy38/amb_w_tds.git"
        ["app_migrator"]="git@github.com:rogerboy38/app_migrator.git"
    )
fi

# Function to check SSH
check_ssh() {
    echo "🔗 Testing GitHub SSH connection..."
    if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
        echo "✅ SSH connection working"
        return 0
    else
        echo "❌ SSH connection failed"
        echo "   Please ensure SSH key is added to GitHub:"
        echo "   https://github.com/settings/keys"
        return 1
    fi
}

# Function to check app status
check_app_status() {
    local app=$1
    local app_path="$HOME/frappe-bench/apps/$app"
    
    if [[ ! -d "$app_path" ]]; then
        echo "  ❌ Directory not found"
        return 1
    fi
    
    cd "$app_path" 2>/dev/null || return 1
    
    if [[ ! -d .git ]]; then
        echo "  ⚠️  Not a git repository"
        return 1
    fi
    
    local remote=$(git remote get-url origin 2>/dev/null || echo "none")
    local branch=$(git branch --show-current 2>/dev/null || echo "main")
    local changes=$(git status --porcelain | wc -l)
    
    echo "  📍 Path: $app_path"
    echo "  🔗 Remote: $(basename "$remote" .git)"
    echo "  🌿 Branch: $branch"
    echo "  📝 Changes: $changes uncommitted"
    
    if [[ $changes -gt 0 ]]; then
        echo "  📋 Change list:"
        git status --short | sed 's/^/    /'
    fi
    
    return 0
}

# Function to sync single app
sync_app() {
    local app=$1
    local force=${2:-false}
    
    echo ""
    echo "📦 Syncing $app..."
    
    local app_path="$HOME/frappe-bench/apps/$app"
    if [[ ! -d "$app_path/.git" ]]; then
        echo "  ❌ Not a git repository"
        return 1
    fi
    
    cd "$app_path"
    
    # Get current branch
    local branch=$(git branch --show-current 2>/dev/null || echo "main")
    echo "  🌿 Branch: $branch"
    
    # Check if remote is configured
    local remote=$(git remote get-url origin 2>/dev/null)
    if [[ -z "$remote" ]]; then
        echo "  ⚠️  No remote configured"
        
        # Try to set remote from configuration
        if [[ -v GITHUB_REPOS[$app] ]]; then
            echo "  🔧 Setting remote to: ${GITHUB_REPOS[$app]}"
            git remote add origin "${GITHUB_REPOS[$app]}"
            remote="${GITHUB_REPOS[$app]}"
        else
            echo "  ❌ No configured remote for $app"
            return 1
        fi
    fi
    
    # Commit changes if any
    local changes=$(git status --porcelain | wc -l)
    if [[ $changes -gt 0 ]]; then
        echo "  📝 Committing $changes change(s)..."
        git add .
        git commit -m "Auto-sync via App Migrator - $(date '+%Y-%m-%d %H:%M:%S')"
    fi
    
    # Push to GitHub
    echo "  📤 Pushing to GitHub..."
    if [[ "$force" == true ]]; then
        if git push origin "$branch" --force-with-lease; then
            echo "  ✅ Force pushed safely"
            return 0
        else
            echo "  ❌ Force push failed"
            return 1
        fi
    else
        if git push origin "$branch"; then
            echo "  ✅ Pushed successfully"
            return 0
        else
            echo "  ⚠️  Standard push failed"
            return 2  # Special code for "try with force"
        fi
    fi
}

# Main execution
main() {
    # Check SSH first
    check_ssh || {
        read -p "⚠️  SSH failed. Continue anyway? (y/N): " -n 1 -r
        echo ""
        [[ $REPLY =~ ^[Yy]$ ]] || exit 1
    }
    
    # Show app status
    echo ""
    echo "🔍 Current App Status:"
    echo ""
    
    local apps_to_sync=()
    for app in "${!GITHUB_REPOS[@]}"; do
        echo "=== $app ==="
        if check_app_status "$app"; then
            apps_to_sync+=("$app")
        fi
        echo ""
    done
    
    if [[ ${#apps_to_sync[@]} -eq 0 ]]; then
        echo "✅ No apps need syncing"
        exit 0
    fi
    
    # Ask for confirmation
    echo "📋 Apps to sync: ${apps_to_sync[*]}"
    echo ""
    read -p "🚀 Proceed with sync? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Sync cancelled"
        exit 0
    fi
    
    # Perform sync
    local failed_apps=()
    local needs_force=()
    
    for app in "${apps_to_sync[@]}"; do
        if ! sync_app "$app"; then
            if [[ $? -eq 2 ]]; then
                needs_force+=("$app")
            else
                failed_apps+=("$app")
            fi
        fi
    done
    
    # Handle apps that need force push
    if [[ ${#needs_force[@]} -gt 0 ]]; then
        echo ""
        echo "⚠️  Some apps need force push: ${needs_force[*]}"
        read -p "🔨 Attempt force push? (y/N): " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            for app in "${needs_force[@]}"; do
                sync_app "$app" true
            done
        fi
    fi
    
    # Summary
    echo ""
    echo "🎉 Sync Summary:"
    echo "  • Total apps: ${#apps_to_sync[@]}"
    echo "  • Successful: $((${#apps_to_sync[@]} - ${#failed_apps[@]}))"
    echo "  • Failed: ${#failed_apps[@]}"
    
    if [[ ${#failed_apps[@]} -gt 0 ]]; then
        echo "  • Failed apps: ${failed_apps[*]}"
    fi
    
    echo ""
    echo "🔗 GitHub URLs:"
    for app in "${!GITHUB_REPOS[@]}"; do
        local repo_name=$(basename "${GITHUB_REPOS[$app]}" .git)
        echo "  • $app: https://github.com/$GITHUB_USER/$repo_name"
    done
}

# Run main function
main "$@"
