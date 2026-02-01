#!/usr/bin/env python3
import os
import sys

# Read current hooks.py
with open('hooks.py', 'r') as f:
    content = f.read()

# Check if git_push is imported
if 'from app_migrator.commands.git_push import git_push' not in content:
    print("Adding git_push import...")
    
    # Find where imports end and add our import
    lines = content.split('\n')
    new_lines = []
    imports_added = False
    
    for line in lines:
        new_lines.append(line)
        # Add import after the last import line
        if 'import' in line and not imports_added:
            if 'commands' in line or 'click' in line:
                # Check next line to see if it's also an import
                next_line = lines[lines.index(line) + 1] if lines.index(line) + 1 < len(lines) else ''
                if 'import' not in next_line:
                    new_lines.append('from app_migrator.commands.git_push import git_push')
                    imports_added = True
    
    # If we didn't add it, add at the end of imports
    if not imports_added:
        for i, line in enumerate(new_lines):
            if 'import' in line and (i == len(new_lines)-1 or 'import' not in new_lines[i+1]):
                new_lines.insert(i+1, 'from app_migrator.commands.git_push import git_push')
                break
    
    content = '\n'.join(new_lines)

# Check if git_push is in commands list
if 'git_push' not in content or 'commands = [' in content and 'git_push' not in content.split('commands = [')[1].split(']')[0]:
    print("Adding git_push to commands list...")
    
    # Find commands list
    if 'commands = [' in content:
        # Simple replacement
        content = content.replace('commands = [', 'commands = [git_push, ')
    else:
        # Find where commands are defined
        lines = content.split('\n')
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if 'commands = [' in line:
                # Add git_push to the list
                new_lines[-1] = line.replace('commands = [', 'commands = [git_push, ')
        
        content = '\n'.join(new_lines)

# Write back
with open('hooks.py', 'w') as f:
    f.write(content)

print("✅ hooks.py updated!")
