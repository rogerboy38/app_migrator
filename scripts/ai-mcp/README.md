# AI MCP Integration for Frappe/GitHub

## Quick Start
1. Run setup: `./setup-mcp.sh`
2. Test: `./test-mcp.sh`
3. Use client: `./mcp-client.sh help`

## Files
- `mcp-server.sh` - MCP protocol server
- `mcp-client.sh` - Command line client
- `mcp-config.json` - Configuration
- `setup-mcp.sh` - Setup script
- `github-integration.sh` - Safe-git integration

## Persistence
All files are in app_migrator repository and survive bench resets.
