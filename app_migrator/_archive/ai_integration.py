#!/usr/bin/env python3
"""
🤖 AI INTEGRATION MODULE - App Migrator v5.5.1
Cloud-friendly natural language interface
"""

import os
import sys
import json
import re
from typing import Dict, Any, List, Tuple
import click

class AppMigratorAIAgent:
    """
    Cloud-friendly AI Agent for App Migrator commands
    Uses direct function calls instead of subprocess
    """

    def __init__(self):
        self.command_patterns = {
            # Analyze/Diagnose patterns
            r'analyze (?:the )?(?:health of )?(\w+)(?: app)?': 'diagnose-app',
            r'diagnose (?:the )?(\w+)(?: app)?': 'diagnose-app',
            r'check (?:the )?(?:health of )?(\w+)(?: app)?': 'diagnose-app',
            r'health (?:scan|check|analysis)': 'scan-bench-health',
            r'scan health': 'scan-bench-health',
            r'quick health check (?:for )?(\w+)': 'quick-health-check',

            # Fix/Repair patterns
            r'fix (?:broken|all|) apps': 'repair-bench-apps',
            r'fix apps': 'repair-bench-apps',
            r'repair apps': 'repair-bench-apps',
            r'batch repair': 'repair-bench-apps',

            # Intelligence patterns
            r'predict success (?:for )?(\w+)': 'predict-success',
            r'intelligence dashboard': 'intelligence-dashboard',

            # Multi-bench patterns
            r'list benches': 'list-benches',
            r'bench apps': 'bench-apps',

            # Help patterns
            r'help|commands|what can you do': 'help'
        }

        self.app_aliases = {
            'payments': 'payments',
            'erpnext': 'erpnext',
            'frappe': 'frappe',
            'app_migrator': 'app_migrator'
        }

    def parse_and_execute(self, user_input: str) -> Dict[str, Any]:
        """
        Parse natural language input and execute commands directly
        """
        print(f"🤖 Processing: '{user_input}'")

        # Convert to lowercase for pattern matching
        input_lower = user_input.lower().strip()

        # Special case for help
        if any(word in input_lower for word in ['help', 'commands', 'what can you do']):
            return self._execute_help_direct()

        # Match patterns and extract parameters
        command, args = self._match_pattern(input_lower)

        if command:
            return self._execute_command_direct(command, args)
        else:
            return {
                "success": False,
                "error": f"Could not understand: '{user_input}'. Try: 'analyze payments', 'scan health', 'fix apps', or 'help'",
                "suggestions": [
                    "analyze payments",
                    "scan health",
                    "fix apps",
                    "predict success erpnext",
                    "list benches"
                ]
            }

    def _match_pattern(self, user_input: str) -> Tuple[str, str]:
        """
        Match user input to command patterns and extract arguments
        """
        # Try exact matches first
        exact_matches = {
            'scan health': ('scan-bench-health', ''),
            'fix apps': ('repair-bench-apps', ''),
            'repair apps': ('repair-bench-apps', ''),
            'health scan': ('scan-bench-health', ''),
            'quick health check': ('quick-health-check', ''),
            'list benches': ('list-benches', ''),
            'bench apps': ('bench-apps', 'frappe-bench-v5'),
            'intelligence dashboard': ('intelligence-dashboard', ''),
            'predict success': ('predict-success', 'erpnext'),
        }

        if user_input in exact_matches:
            return exact_matches[user_input]

        # Then try regex patterns
        for pattern, command in self.command_patterns.items():
            match = re.search(pattern, user_input)
            if match:
                args = self._extract_arguments(match.groups())
                return command, args

        return None, ""

    def _extract_arguments(self, match_groups: tuple) -> str:
        """
        Extract command arguments from regex match groups
        """
        if not match_groups:
            return ""

        args = []
        for group in match_groups:
            if group:  # Only add non-empty groups
                clean_arg = group.strip()
                if clean_arg and clean_arg not in ['the', 'for', 'in', 'of']:
                    if clean_arg in self.app_aliases:
                        args.append(self.app_aliases[clean_arg])
                    else:
                        args.append(clean_arg)

        unique_args = list(dict.fromkeys(args))
        return " ".join(unique_args)

    def _execute_command_direct(self, command: str, args: str = "") -> Dict[str, Any]:
        """
        Execute commands directly via function calls (cloud-friendly)
        """
        print(f"🔧 Executing: {command} {args}")

        try:
            # Import and call functions directly instead of subprocess
            if command == 'scan-bench-health':
                from .app_health_scanner import scan_bench_health_function
                result = scan_bench_health_function()
                output = str(result) if result else "Bench health scan completed"

            elif command == 'repair-bench-apps':
                from .diagnostic_commands import repair_bench_apps_callback
                result = repair_bench_apps_callback(dry_run=True)
                output = "App repair analysis completed (dry run)"

            elif command == 'diagnose-app' and args:
                from .pre_installation_diagnostics import diagnose_app_function
                app_path = f"/home/frappe/frappe-bench-v5/apps/{args}"
                result = diagnose_app_function(app_path, fix=False)
                output = str(result) if result else f"Diagnosis completed for {args}"

            elif command == 'quick-health-check' and args:
                from .app_health_scanner import quick_health_check_function
                result = quick_health_check_function(args)
                output = str(result) if result else f"Quick health check completed for {args}"

            elif command == 'list-benches':
                from .analysis_tools import detect_available_benches
                benches = detect_available_benches()
                output = "Available benches:\n" + "\n".join([f"  • {bench}" for bench in benches])

            elif command == 'bench-apps' and args:
                from .analysis_tools import get_bench_apps
                apps = get_bench_apps(args)
                output = f"Apps in {args}:\n" + "\n".join([f"  • {app}" for app in apps])

            elif command == 'intelligence-dashboard':
                from .intelligence_engine import display_intelligence_dashboard
                display_intelligence_dashboard()
                output = "Intelligence dashboard displayed"

            elif command == 'predict-success' and args:
                from .intelligence_engine import predict_migration_success
                result = predict_migration_success(args, args)
                output = str(result) if result else f"Success prediction completed for {args}"

            else:
                return {
                    "success": False,
                    "error": f"Command '{command}' not available in cloud mode",
                    "command": f"{command} {args}"
                }

            return {
                "success": True,
                "output": output,
                "command": f"{command} {args}",
                "enhanced_analysis": self._enhance_with_ai_insights(output, command)
            }

        except ImportError as e:
            return {
                "success": False,
                "error": f"Module import error: {str(e)}",
                "command": f"{command} {args}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "command": f"{command} {args}"
            }

    def _execute_help_direct(self) -> Dict[str, Any]:
        """
        Cloud-friendly help command
        """
        help_text = """
🤖 App Migrator AI Assistant - Cloud Edition

Available Commands:
• analyze [app]           - Analyze app health
• scan health            - Scan bench health
• fix apps              - Fix broken apps (dry run)
• repair apps           - Repair apps (dry run)
• quick health check [app] - Quick app health check
• predict success [app]  - Predict migration success
• list benches          - List available benches
• bench apps [bench]    - List apps in bench
• intelligence dashboard - Show AI intelligence

Examples:
• "analyze payments"
• "scan health"
• "fix apps"
• "predict success erpnext"
• "list benches"

Note: Cloud edition uses direct function calls for security.
"""

        return {
            "success": True,
            "output": help_text,
            "enhanced_analysis": "Cloud-friendly AI assistant ready! All commands use secure direct function calls.",
            "command": "help"
        }

    def _enhance_with_ai_insights(self, command_output: str, command_type: str) -> str:
        """
        Add AI-powered insights to command results
        """
        insights = []

        if command_type == 'scan-bench-health':
            if "Healthy Apps:" in command_output:
                insights.append("📊 Bench health analysis completed")
                insights.append("💡 Use 'fix apps' to repair any issues found")

        elif command_type == 'repair-bench-apps':
            insights.append("🔧 App repair analysis completed")
            insights.append("💡 This was a dry run. All fixes are simulated")

        elif command_type == 'diagnose-app':
            insights.append("🩺 App diagnosis completed")
            insights.append("💡 Review the health score and blockers")

        elif command_type == 'predict-success':
            insights.append("🎯 Success prediction completed")
            insights.append("💡 Use this to plan your migration strategy")

        # Add general insights
        if not insights:
            insights.append("✅ Command executed successfully")
            insights.append("🤖 Cloud-friendly execution completed")

        return "\n".join(insights)


# Cloud-friendly CLI command
@click.command()
@click.argument('user_query')
def ai_migrate_cli(user_query: str):
    """Cloud-friendly AI migration commands"""
    agent = AppMigratorAIAgent()
    result = agent.parse_and_execute(user_query)

    if result.get('success'):
        click.echo(f"✅ AI Command Result:")
        click.echo(result['output'])
        if 'enhanced_analysis' in result:
            click.echo(f"\n🤖 AI Insights:\n{result['enhanced_analysis']}")
    else:
        click.echo(f"❌ AI Command Failed:")
        click.echo(result.get('error', 'Unknown error'))
        if 'suggestions' in result:
            click.echo(f"\n💡 Try these instead:")
            for suggestion in result['suggestions']:
                click.echo(f"   • {suggestion}")


if __name__ == "__main__":
    # Test the cloud-friendly AI agent
    agent = AppMigratorAIAgent()

    test_queries = [
        "analyze payments",
        "scan health",
        "fix apps",
        "help"
    ]

    print("🧪 Testing Cloud-Friendly AI Integration...")
    for query in test_queries:
        print(f"\n🔍 Testing: '{query}'")
        result = agent.parse_and_execute(query)
        print(f"✅ Success: {result.get('success', False)}")
