"""app-migrator-planner: workflow planner (Phase 5 stub).

Per U1/Q3 sign-off:
- execution_mode defaults to 'dry-run' (safe-by-default)
- --yes bypasses dry-run -> 'apply' (for scripted use)
- destructive steps in ordered_steps carry approval_required=true

For Phase 5 test contract, the planner emits a structured plan JSON for any
of the 5 first-wave skills (orphan-repair, module-collision-preflight,
paired-deliverable-check, migration-preflight, install-recovery).

Q7 native parametrize: pytest parameterizes test_planner_* across all 5 skills.

Full LLM-assisted planner logic deferred to W1 close when the new scaffold
installs as a proper bench app.
"""
from __future__ import annotations

import json
import sys

import click

try:
    from frappe.commands import pass_context
except ImportError:
    def pass_context(f):
        return f


# 5 first-wave skills per v0.5 spec
FIRST_WAVE_SKILLS = (
    "orphan-repair",
    "module-collision-preflight",
    "paired-deliverable-check",
    "migration-preflight",
    "install-recovery",
)


def _build_plan(workflow: str, execution_mode: str) -> dict:
    """Build a v0.5 plan dict for the given workflow + execution_mode."""
    return {
        "schema_version": "1.0.0",
        "workflow": workflow,
        "execution_mode": execution_mode,
        "ordered_steps": [
            {
                "name": f"{workflow}-step-1-validate",
                "destructive": False,
                "approval_required": False,
                "description": f"Validate {workflow} preconditions.",
            },
            {
                "name": f"{workflow}-step-2-apply",
                "destructive": True,
                "approval_required": True,
                "description": f"Apply {workflow} (destructive; requires approval).",
            },
            {
                "name": f"{workflow}-step-3-verify",
                "destructive": False,
                "approval_required": False,
                "description": f"Verify {workflow} result.",
            },
        ],
    }


@click.command('app-migrator-planner')
@click.argument('workflow')
@click.option('--yes', is_flag=True, help='Bypass dry-run pause for scripted use')
@pass_context
def app_migrator_planner(context, workflow, yes):
    """Generate a workflow plan (dry-run by default). Always emits JSON.

    WORKFLOW is one of: orphan-repair, module-collision-preflight,
    paired-deliverable-check, migration-preflight, install-recovery.
    """
    execution_mode = "apply" if yes else "dry-run"
    plan = _build_plan(workflow, execution_mode)
    sys.stdout.write(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    sys.stdout.flush()