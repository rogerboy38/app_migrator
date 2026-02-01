#!/bin/bash
# MCP Client for AI Agents
# Simple client to interact with the MCP server

SERVER_SCRIPT="$HOME/frappe-bench/apps/app_migrator/scripts/ai-mcp/mcp-server.sh"

# Check if server exists
if [[ ! -f "$SERVER_SCRIPT" ]]; then
    echo "Error: MCP server not found at $SERVER_SCRIPT"
    exit 1
fi

# Function to send command to server
send_command() {
    echo "$1" | "$SERVER_SCRIPT"
}

# Function to format JSON output
format_output() {
    if command -v jq >/dev/null 2>&1; then
        jq .
    else
        cat
        echo ""
    fi
}

# Main client logic
case "$1" in
    "repos"|"list-repos")
        send_command "github.list_repos" | format_output
        ;;
        
    "repo-status")
        if [[ -z "$2" ]]; then
            echo "Usage: $0 repo-status <repository-name>"
            echo "Example: $0 repo-status rnd_warehouse_management"
            exit 1
        fi
        send_command "github.get_status $2" | format_output
        ;;
        
    "apps"|"list-apps")
        send_command "frappe.list_apps" | format_output
        ;;
        
    "app-info")
        if [[ -z "$2" ]]; then
            echo "Usage: $0 app-info <app-name>"
            echo "Example: $0 app-info rnd_nutrition"
            exit 1
        fi
        send_command "frappe.get_info $2" | format_output
        ;;
        
    "status"|"system")
        send_command "system.status" | format_output
        ;;
        
    "help"|"--help"|"-h")
        echo "MCP Client for Frappe/GitHub AI Integration"
        echo ""
        echo "Usage: $0 <command> [arguments]"
        echo ""
        echo "Commands:"
        echo "  repos, list-repos      List all GitHub repositories"
        echo "  repo-status <repo>     Get status of specific repository"
        echo "  apps, list-apps        List all Frappe apps in bench"
        echo "  app-info <app>         Get information about specific app"
        echo "  status, system         Get system status"
        echo "  help                   Show this help"
        echo ""
        echo "Examples:"
        echo "  $0 repos"
        echo "  $0 repo-status rnd_warehouse_management"
        echo "  $0 apps"
        echo "  $0 app-info app_migrator"
        echo "  $0 status"
        ;;
        
    "interactive"|"shell")
        echo "Starting interactive MCP shell..."
        echo "Type 'exit' or 'quit' to exit"
        echo ""
        while true; do
            read -p "mcp> " command
            case "$command" in
                "exit"|"quit"|"q")
                    echo "Goodbye!"
                    exit 0
                    ;;
                "")
                    continue
                    ;;
                *)
                    send_command "$command" | format_output
                    ;;
            esac
        done
        ;;
        
    *)
        # If no command specified, show help
        if [[ -z "$1" ]]; then
            "$0" help
        else
            echo "Unknown command: $1"
            echo "Use '$0 help' for available commands"
            exit 1
        fi
        ;;
esac
