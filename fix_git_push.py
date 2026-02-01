import re

# Read hooks.py
with open('hooks.py', 'r') as f:
    content = f.read()

# Check if git_push is already imported
if 'from app_migrator.commands.git_push import git_push' not in content:
    print("Adding git_push import...")
    
    # Find a good place to add the import (after other imports)
    lines = content.split('\n')
    new_lines = []
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        # Look for the last import line
        if 'import' in line and 'app_migrator.commands' in line:
            # Check if next line is also an import
            if i + 1 < len(lines) and 'import' not in lines[i + 1]:
                new_lines.append('from app_migrator.commands.git_push import git_push')
                print("✅ Import added after other command imports")
                break
    
    content = '\n'.join(new_lines)

# Check if git_push is in commands list
if 'commands = [' in content and 'git_push' not in content.split('commands = [')[1].split(']')[0]:
    print("\nAdding git_push to commands list...")
    
    # Simple string replacement
    content = content.replace('commands = [', 'commands = [git_push, ')
    print("✅ git_push added to commands list")
else:
    print("\n⚠️  Commands list not found or git_push already in list")

# Write back
with open('hooks.py', 'w') as f:
    f.write(content)

print("\n✅ hooks.py updated successfully!")
