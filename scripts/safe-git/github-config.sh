#!/bin/bash
# GitHub Configuration for App Migrator
# Centralized configuration that survives bench resets

# GitHub User
export GITHUB_USER="rogerboy38"

# Repository mapping: app_name -> git_ssh_url
declare -A GITHUB_REPOS=(
    ["rnd_nutrition"]="git@github.com:rogerboy38/rnd_nutrition2.git"
    ["rnd_warehouse_management"]="git@github.com:rogerboy38/rnd_warehouse_management.git"
    ["amb_w_tds"]="git@github.com:rogerboy38/amb_w_tds.git"
    ["app_migrator"]="git@github.com:rogerboy38/app_migrator.git"
    ["frappe-cloud-git-framework"]="git@github.com:rogerboy38/frappe-cloud-git-framework.git"
)

# SSH Configuration
export SSH_KEY="$HOME/.ssh/id_ed25519"
export SSH_CONFIG="$HOME/.ssh/config"

# Safe push options
export SAFE_FORCE_PUSH="--force-with-lease"  # Safer than --force
export DEFAULT_BRANCH="main"

# GitHub API (optional, for advanced features)
export GITHUB_API_TOKEN=""  # Set if using GitHub API

# Utility functions
github_repo_url() {
    local app=$1
    if [[ -v GITHUB_REPOS[$app] ]]; then
        echo "${GITHUB_REPOS[$app]}"
    else
        echo ""
    fi
}

github_web_url() {
    local app=$1
    local repo_url=$(github_repo_url "$app")
    if [[ -n "$repo_url" ]]; then
        local repo_name=$(basename "$repo_url" .git)
        echo "https://github.com/$GITHUB_USER/$repo_name"
    else
        echo ""
    fi
}

list_github_repos() {
    echo "GitHub Repositories for $GITHUB_USER:"
    for app in "${!GITHUB_REPOS[@]}"; do
        local web_url=$(github_web_url "$app")
        echo "  • $app: $web_url"
    done
}
