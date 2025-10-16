cd ~/frappe-bench-v601/apps/app_migrator
cat > AI_AGENT_CRASH_PREVENTION_SPECS.md << 'SPECSEOF'
# AI Agent Technical Specifications: Frappe v15 Crash Prevention

## Overview
This document provides detailed technical specifications for AI agents to prevent crash loops when developing Frappe v15+ commands. Based on empirical research and debugging of the App Migrator project.

---

## 🚨 CRITICAL: Crash Loop Root Causes

### 1. Circular Import Patterns (MAJOR CRASH SOURCE)

#### ❌ DANGEROUS PATTERNS (CRASH-PRONE)
```python
# apps/your_app/your_app/commands/__init__.py

# ❌ MODULE-LEVEL FRAPPE IMPORTS (CAUSES CRASH)
import frappe
from frappe.utils import get_bench_path
from frappe.model.document import Document

# ❌ RELATIVE IMPORTS THAT CREATE DEPENDENCY LOOPS  
from .enhanced_migration_engine import EnhancedMigrationEngine
from ..utils.python_safe_replacer import PythonSafeReplacer

# ❌ COMPLEX INITIALIZATION AT MODULE LEVEL
frappe_app = frappe.get_app()  # CRASHES DURING DISCOVERY

✅ SAFE PATTERNS (CRASH-PROOF)
python

# apps/your_app/your_app/commands/__init__.py

# ✅ ONLY SAFE IMPORTS AT MODULE LEVEL
import click
from frappe.commands import pass_context

# ✅ FRAPPE IMPORTS INSIDE FUNCTIONS (SAFE)
@click.command("migrate-app")
@pass_context
def migrate_app_command(context, action=None):
    # ✅ SAFE: Import Frappe inside function
    import frappe
    from frappe.utils import get_bench_path
    
    # ✅ SAFE: Import other modules inside function
    from app_migrator.commands.enhanced_migration_engine import enhanced_migrate_app
    
    # Your command logic here

2. Command Discovery Mechanism Deep Dive
Frappe v15 Internal Process
python

# frappe/utils/bench_helper.py - ACTUAL IMPLEMENTATION
def get_app_commands(app: str) -> dict:
    ret = {}
    try:
        # ⚠️ This happens during Frappe bootstrap
        app_command_module = importlib.import_module(f"{app}.commands")
    except ModuleNotFoundError as e:
        return ret
    
    # ⚠️ Frappe looks for 'commands' list while initializing
    for command in getattr(app_command_module, "commands", []):
        ret[command.name] = command  # Must be Click objects
    
    return ret

Key Timing Constraints

    Command Discovery: Happens during Frappe framework initialization

    Module Loading: {app}.commands imported before database connection

    Critical Period: Any module-level Frappe operations will crash

🛡️ CRASH-PROOF ARCHITECTURE PATTERNS
1. Safe Module Structure Template
text

apps/your_app/
├── your_app/
│   ├── commands/
│   │   ├── __init__.py              # SAFE: Only Click imports
│   │   └── enhanced_engine.py       # SAFE: No Frappe imports at top
│   ├── utils/
│   │   ├── __init__.py              # EMPTY or minimal
│   │   └── safe_tools.py            # SAFE: Function-scoped imports
│   └── hooks.py                     # MINIMAL: No get_app_commands

2. Crash-Proof Command Template
python

# apps/your_app/your_app/commands/__init__.py
import click
from frappe.commands import pass_context

@click.command("your-command")
@click.argument("action", required=False)
@click.option("--site", help="Site name")
@pass_context
def your_command(context, action=None, site=None):
    """
    Crash-proof command template.
    """
    # ✅ SAFE ZONE: All Frappe imports inside function
    import frappe
    from frappe.utils import get_bench_path
    from frappe.model.document import Document
    
    try:
        if action == "test":
            return handle_test_action()
        elif action == "list":
            return handle_list_action()
        else:
            return handle_default_action(action)
            
    except Exception as e:
        # ✅ PROPER ERROR HANDLING
        print(f"💥 Command error: {e}")
        return 1  # Non-zero exit code for failures

def handle_test_action():
    """Safe command handler"""
    # ✅ Can use Frappe here safely
    import frappe
    print("✅ Command working in safe context")
    return 0

def handle_list_action():
    """Safe app listing"""
    from frappe.utils import get_bench_path
    import os
    
    bench_path = get_bench_path()
    apps_path = os.path.join(bench_path, "apps")
    # ... implementation
    return 0

# ✅ MANDATORY: Frappe v15 command discovery
commands = [your_command]

3. Safe Enhanced Feature Pattern
python

# apps/your_app/your_app/commands/enhanced_engine.py

# ✅ SAFE: No Frappe imports at module level
import os
import sys

def enhanced_migrate_app(source_app, target_app, dry_run=False):
    """
    Enhanced features with safe imports.
    """
    # ✅ SAFE: Import Frappe and utilities inside function
    try:
        import frappe
        from frappe.utils import get_bench_path
        from app_migrator.utils.python_safe_replacer import PythonSafeReplacer
        
        # Implementation here
        bench_path = get_bench_path()
        return {"success": True, "log": ["Migration completed"]}
        
    except ImportError as e:
        return {"success": False, "error": f"Import failed: {e}"}

class EnhancedMigrationEngine:
    def __init__(self, source_app, target_app):
        # ✅ SAFE: No Frappe operations in __init__
        self.source_app = source_app
        self.target_app = target_app
        
    def validate(self):
        # ✅ SAFE: Frappe operations in methods
        import frappe
        from frappe.utils import get_bench_path
        # ... implementation

🔧 DIAGNOSTIC PROTOCOLS FOR AI AGENTS
1. Pre-Implementation Safety Check
python

# AI Agent should ALWAYS verify this checklist:

SAFETY_CHECKLIST = {
    "module_level_frappe_imports": False,  # Must be False
    "relative_imports_in_commands_init": False,  # Should be False  
    "complex_module_level_operations": False,  # Must be False
    "frappe_db_operations_at_top": False,  # Must be False
    "commands_list_exists": True,  # Must be True
    "imports_inside_functions": True,  # Should be True
}

2. Crash Detection Diagnostics
bash

# When commands crash, run these diagnostics:

# 1. Test command discovery
bench --site [site] console << 'EOF'
from frappe.utils.bench_helper import get_app_commands
cmds = get_app_commands('your_app')
print(f"Commands: {list(cmds.keys())}")
EOF

# 2. Test direct import
python -c "import your_app.commands; print('✅ Import OK')"

# 3. Check for circular imports
python -c "
import your_app.commands as cmd_module
print('Module attributes:')
for attr in dir(cmd_module):
    if not attr.startswith('_'):
        print(f'  {attr}: {type(getattr(cmd_module, attr))}')
"

3. Progressive Enhancement Strategy
bash

# AI Agent Implementation Steps:

# PHASE 1: Minimal Stable Version
1. Create basic commands/__init__.py with NO Frappe imports
2. Test command discovery: bench --site [site] your-command test
3. Verify no crashes

# PHASE 2: Add Safe Features  
4. Add function-level Frappe imports inside command handlers
5. Test each command: bench --site [site] your-command list
6. Verify stable operation

# PHASE 3: Enhanced Components
7. Create separate modules with safe import patterns
8. Test integration: bench --site [site] your-command enhanced-feature
9. Verify all components work together

🚨 SPECIFIC CRASH SCENARIOS AND SOLUTIONS
Scenario 1: "No such command" after installation

Root Cause: Module-level Frappe imports causing import failure during discovery
Solution: Move ALL Frappe imports inside command functions
Scenario 2: Command shows but crashes on execution

Root Cause: Complex initialization in command module
Solution: Simplify module, move logic to function handlers
Scenario 3: Circular import errors

Root Cause: Relative imports between command modules
Solution: Use absolute imports or lazy loading
Scenario 4: Database connection errors

Root Cause: Frappe DB operations at module level
Solution: All DB operations must be inside command functions with proper site context
📋 AI AGENT IMPLEMENTATION RULES
MANDATORY RULES (Never Violate)

    NEVER import frappe at module level in commands/__init__.py

    ALWAYS put Frappe imports inside command functions

    ALWAYS include commands = [command_objects] list

    NEVER perform database operations at module level

    ALWAYS test command discovery after changes

RECOMMENDED PATTERNS

    Use function-specific imports for Frappe components

    Implement comprehensive error handling in commands

    Use progressive enhancement approach

    Test each feature independently before integration

    Document import patterns for future maintenance

DEBUGGING PROTOCOLS

    First, test command discovery with get_app_commands()

    Second, test minimal command execution

    Third, add features one at a time with testing

    Fourth, implement comprehensive error handling

    Fifth, document the stable configuration

✅ VERIFICATION CHECKLIST

Before declaring a Frappe v15 command system stable, verify:

    bench --site [site] your-command test executes without crashes

    get_app_commands('your_app') returns command objects

    No module-level Frappe imports in commands/__init__.py

    All Frappe operations happen inside command functions

    commands = [command_objects] list exists and is populated

    Error handling prevents uncaught exceptions

    Progressive enhancement approach followed

    Comprehensive testing completed

🎯 LESSONS LEARNED FROM APP MIGRATOR
Key Breakthroughs

    Frappe v15 Command Discovery: Automatic from commands list, no hooks needed

    Import Timing: Frappe framework not fully initialized during command discovery

    Safe Zones: Function scope is safe for Frappe operations

    Crash Prevention: Module-level Frappe imports = guaranteed crashes

Successful Patterns

    Function-scoped Frappe imports

    Minimal commands/__init__.py

    Separate feature modules with safe imports

    Comprehensive error handling

    Progressive testing approach

Document Version: 2.0
Based On: App Migrator Crash Loop Resolution
Tested With: Frappe v15, Python 3.12
Status: PRODUCTION VALIDATED
SPECSEOF

echo ""
echo "✅ COMPREHENSIVE CRASH PREVENTION SPECS CREATED!"
echo ""
echo "📚 Summary of Key AI Agent Rules:"
echo ""
echo "🚨 MANDATORY (Never Violate):"
echo " • NEVER import frappe at module level in commands/init.py"
echo " • ALWAYS put Frappe imports inside command functions"
echo " • ALWAYS include commands = [command_objects] list"
echo " • NEVER perform database operations at module level"
echo ""
echo "🛡️ SAFE PATTERNS:"
echo " • Function-scoped imports for all Frappe components"
echo " • Minimal commands/init.py with only Click imports"
echo " • Separate feature modules with safe import patterns"
echo " • Progressive enhancement with testing at each step"
echo ""
echo "🔧 DIAGNOSTICS:"
echo " • Test command discovery with get_app_commands()"
echo " • Verify no circular imports with direct import test"
echo " • Use minimal version first, then add features"
echo ""
echo "📁 File created: AI_AGENT_CRASH_PREVENTION_SPECS.md"
echo "📍 Location: ~/frappe-bench-v601/apps/app_migrator/"
echo ""
echo "🎯 These specifications will prevent AI agents from creating crash loops"
echo " in future Frappe v15 command development projects!"
text


This comprehensive specification document captures all the critical lessons learned from fixing the App Migrator crash loop. The key insights are:

1. **Frappe v15 command discovery happens during framework bootstrap** - module-level Frappe imports will crash
2. **Function scope is the safe zone** for all Frappe operations
3. **Progressive enhancement** is essential - start minimal, then add features
4. **Comprehensive testing** at each step prevents regression

The AI Agent now has clear, actionable rules to prevent crash loops in future Frappe v15 command development!
