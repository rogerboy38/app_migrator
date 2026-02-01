import os
import re

def find_command_registration():
    # Check hooks.py
    with open('hooks.py', 'r') as f:
        hooks_content = f.read()
    
    # Look for imports pattern
    import_pattern = r'from app_migrator\.commands\.(\w+) import (\w+)'
    imports = re.findall(import_pattern, hooks_content)
    
    print("Imports found in hooks.py:")
    for module, cmd in imports:
        print(f"  from app_migrator.commands.{module} import {cmd}")
    
    # Look for commands list
    commands_pattern = r'commands\s*=\s*\[(.*?)\]'
    match = re.search(commands_pattern, hooks_content, re.DOTALL)
    if match:
        print("\nCommands list found:")
        commands = [c.strip() for c in match.group(1).split(',') if c.strip()]
        for cmd in commands:
            print(f"  • {cmd}")
    
    # Check if orphans is there
    if 'orphans' in hooks_content:
        print("\n✅ 'orphans' found in hooks.py")
    else:
        print("\n❌ 'orphans' NOT found in hooks.py")

find_command_registration()
