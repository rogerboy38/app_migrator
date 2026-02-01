#!/bin/bash
# MCP Server for AI Agents
# Model Context Protocol server for GitHub and Frappe integration

VERSION="1.0.0"
CONFIG_FILE="$HOME/frappe-bench/apps/app_migrator/scripts/ai-mcp/mcp-config.json"

# Load configuration
load_config() {
    if [[ -f "$CONFIG_FILE" ]]; then
        echo "Loading config from $CONFIG_FILE" >&2
    else
        # Default configuration
        cat > "$CONFIG_FILE" << 'CONFIGEOF'
{
    "name": "frappe-github-mcp",
    "version": "1.0.0",
    "description": "MCP server for Frappe and GitHub integration",
    "capabilities": {
        "github": {
            "repositories": [
                "rnd_warehouse_management",
                "rnd_nutrition2", 
                "amb_w_tds",
                "app_migrator",
                "frappe-cloud-git-framework"
            ],
            "permissions": ["read", "write"]
        },
        "frappe": {
            "apps": ["rnd_nutrition", "rnd_warehouse_management", "amb_w_tds", "app_migrator"],
            "permissions": ["read", "execute"]
        }
    }
}
CONFIGEOF
    fi
}

# GitHub operations
github_list_repos() {
    echo '{
        "repositories": [
            {"name": "rnd_warehouse_management", "url": "https://github.com/rogerboy38/rnd_warehouse_management"},
            {"name": "rnd_nutrition2", "url": "https://github.com/rogerboy38/rnd_nutrition2"},
            {"name": "amb_w_tds", "url": "https://github.com/rogerboy38/amb_w_tds"},
            {"name": "app_migrator", "url": "https://github.com/rogerboy38/app_migrator"},
            {"name": "frappe-cloud-git-framework", "url": "https://github.com/rogerboy38/frappe-cloud-git-framework"}
        ]
    }'
}

github_get_repo_status() {
    local repo=$1
    local app_path="$HOME/frappe-bench/apps/$repo"
    
    if [[ ! -d "$app_path" ]]; then
        echo '{"error": "Repository not found in bench"}'
        return 1
    fi
    
    cd "$app_path" 2>/dev/null || {
        echo '{"error": "Cannot access repository"}'
        return 1
    }
    
    local branch=$(git branch --show-current 2>/dev/null || echo "unknown")
    local remote=$(git remote get-url origin 2>/dev/null || echo "none")
    local changes=$(git status --porcelain | wc -l)
    local last_commit=$(git log --oneline -1 2>/dev/null || echo "none")
    
    echo "{
        \"repository\": \"$repo\",
        \"branch\": \"$branch\",
        \"remote\": \"$remote\",
        \"uncommitted_changes\": $changes,
        \"last_commit\": \"$last_commit\",
        \"path\": \"$app_path\"
    }"
}

# Frappe operations
frappe_list_apps() {
    echo '{
        "apps": [
            {"name": "rnd_nutrition", "path": "/home/frappe/frappe-bench/apps/rnd_nutrition"},
            {"name": "rnd_warehouse_management", "path": "/home/frappe/frappe-bench/apps/rnd_warehouse_management"},
            {"name": "amb_w_tds", "path": "/home/frappe/frappe-bench/apps/amb_w_tds"},
            {"name": "app_migrator", "path": "/home/frappe/frappe-bench/apps/app_migrator"}
        ]
    }'
}

frappe_get_app_info() {
    local app=$1
    local app_path="$HOME/frappe-bench/apps/$app"
    
    if [[ ! -d "$app_path" ]]; then
        echo '{"error": "App not found"}'
        return 1
    fi
    
    local doctypes=$(find "$app_path" -name "*.json" -type f | grep -c "doctype") 2>/dev/null || echo "0"
    local modules=$(find "$app_path" -type d -name "*_module" | wc -l) 2>/dev/null || echo "0"
    local size=$(du -sh "$app_path" 2>/dev/null | cut -f1 || echo "unknown")
    
    echo "{
        \"app\": \"$app\",
        \"path\": \"$app_path\",
        \"doctypes\": $doctypes,
        \"modules\": $modules,
        \"size\": \"$size\",
        \"exists\": true
    }"
}

# System operations
system_status() {
    echo "{
        \"bench\": \"$(hostname)\",
        \"user\": \"$(whoami)\",
        \"time\": \"$(date)\",
        \"uptime\": \"$(uptime -p)\",
        \"disk\": \"$(df -h /home/frappe | tail -1 | awk '{print $4}')\"
    }"
}

# Main MCP server loop
main() {
    echo "MCP Server v$VERSION - Frappe/GitHub Integration" >&2
    echo "Type 'help' for available commands" >&2
    
    load_config
    
    while read -r command; do
        case "$command" in
            "help"|"?"|"")
                echo '{
                    "commands": [
                        {"name": "github.list_repos", "description": "List GitHub repositories"},
                        {"name": "github.get_status <repo>", "description": "Get repository status"},
                        {"name": "frappe.list_apps", "description": "List Frappe apps"},
                        {"name": "frappe.get_info <app>", "description": "Get app information"},
                        {"name": "system.status", "description": "Get system status"},
                        {"name": "help", "description": "Show this help"}
                    ]
                }'
                ;;
                
            "github.list_repos")
                github_list_repos
                ;;
                
            "github.get_status "*)
                repo=${command#github.get_status }
                github_get_repo_status "$repo"
                ;;
                
            "frappe.list_apps")
                frappe_list_apps
                ;;
                
            "frappe.get_info "*)
                app=${command#frappe.get_info }
                frappe_get_app_info "$app"
                ;;
                
            "system.status")
                system_status
                ;;
                
            *)
                echo "{\"error\": \"Unknown command: $command\"}"
                ;;
        esac
    done
}

# Run server
if [[ "$1" == "--test" ]]; then
    echo "Testing MCP server..." >&2
    echo "github.list_repos" | main | jq . 2>/dev/null || \
    echo "github.list_repos" | main
else
    main
fi
