"""W3 finding #4 — envelope uniformity: every priority command must accept --json.

Before this fix only scan + orphans accepted --json (and returned stubs);
conflicts / generate-plan / execute had no --json option at all, so the v0.5
envelope contract was only partially wired.

This introspects each command's Click parameters in-process (no `bench`
subprocess -> never hangs on this substrate). The full envelope-shape assertions
over live output are covered by tests/phase4_envelope/test_json_envelope.py under
T-VERIFY-005 in a fresh venv.
"""
import pytest

from app_migrator.commands.conflicts import app_migrator_conflicts
from app_migrator.commands.execute import app_migrator_execute
from app_migrator.commands.intelligence import generate_intelligent_plan
from app_migrator.commands.orphans import app_migrator_orphans
from app_migrator.commands.scan import app_migrator_scan

PRIORITY_COMMANDS = {
    "scan": app_migrator_scan,
    "conflicts": app_migrator_conflicts,
    "orphans": app_migrator_orphans,
    "generate-plan": generate_intelligent_plan,
    "execute": app_migrator_execute,
}


def _option_flags(command):
    return {flag for param in command.params for flag in getattr(param, "opts", [])}


@pytest.mark.parametrize("name", list(PRIORITY_COMMANDS))
def test_priority_command_accepts_json(name):
    """Each priority command must expose a --json option (no 'No such option' error)."""
    flags = _option_flags(PRIORITY_COMMANDS[name])
    assert "--json" in flags, f"{name} does not accept --json (flags: {sorted(flags)})"


@pytest.mark.parametrize("name", list(PRIORITY_COMMANDS))
def test_json_option_binds_to_as_json(name):
    """The --json flag must bind to the as_json parameter the handlers branch on."""
    command = PRIORITY_COMMANDS[name]
    json_params = [p for p in command.params if "--json" in getattr(p, "opts", [])]
    assert json_params, f"{name} has no --json param"
    assert json_params[0].name == "as_json", (
        f"{name} --json binds to {json_params[0].name!r}, expected 'as_json'"
    )
