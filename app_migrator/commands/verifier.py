"""app-migrator-verifier: outcome derivation from before/after evidence.

Per U2/Q4 invariant: outcome is DERIVED from comparing before/after evidence
with deterministic rules (blockers delta, findings delta). A buggy verifier
that always returns one value must NOT pass — the test contract enforces this
via 3 test cases (improved/unchanged/regressed).

Test contract:
- bench app-migrator verifier <session_id> --pre <json> --post <json>
- Returns JSON with 'outcome' (improved|unchanged|regressed)
- regressed -> block_continuation=true

Derivation rules (priority order):
1. New findings added OR blockers increased -> regressed (block_continuation=true)
2. Blockers dropped -> improved
3. Otherwise -> unchanged

Full LLM-assisted verifier logic deferred to W1 close.
"""
from __future__ import annotations

import json
import sys

import click


def _count_blockers(b):
    """blockers can be either a list (of blocker objects) or an int (count)."""
    if isinstance(b, list):
        return len(b)
    if isinstance(b, (int, float)):
        return int(b)
    return 0


def _derive_outcome(pre: dict, post: dict) -> dict:
    """Derive outcome from pre/post evidence per U2/Q4 invariant."""
    pre_blockers = _count_blockers(pre.get("blockers"))
    post_blockers = _count_blockers(post.get("blockers"))
    pre_findings = {f.get("id") for f in pre.get("findings", [])}
    post_findings = {f.get("id") for f in post.get("findings", [])}

    new_findings = post_findings - pre_findings
    blocker_delta = post_blockers - pre_blockers

    # Rule 1: regressed (worse)
    if new_findings or blocker_delta > 0:
        return {
            "outcome": "regressed",
            "block_continuation": True,
            "reason": (
                f"new findings={[list(new_findings)]}; blocker delta={blocker_delta}"
            ),
        }

    # Rule 2: improved (better)
    if blocker_delta < 0:
        return {
            "outcome": "improved",
            "block_continuation": False,
            "reason": f"blockers dropped {pre_blockers} -> {post_blockers}",
        }

    # Rule 3: unchanged
    return {
        "outcome": "unchanged",
        "block_continuation": False,
        "reason": "no delta in findings or blockers",
    }


@click.command('app-migrator-verifier')
@click.argument('session_id')
@click.option('--pre', required=True, help='Pre-state JSON')
@click.option('--post', required=True, help='Post-state JSON')
def app_migrator_verifier(session_id, pre, post):
    """Derive outcome from pre/post evidence (deterministic; per U2/Q4).

    SESSION_ID is the migration session identifier (e.g., 'test-session').
    --pre and --post are JSON strings with keys 'findings' (list of {id,...})
    and 'blockers' (int count or list).
    """
    try:
        pre_dict = json.loads(pre)
        post_dict = json.loads(post)
    except json.JSONDecodeError as e:
        click.echo(f"Error: invalid JSON in --pre or --post: {e}", err=True)
        sys.exit(2)

    result = _derive_outcome(pre_dict, post_dict)
    result["session_id"] = session_id
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    sys.stdout.flush()