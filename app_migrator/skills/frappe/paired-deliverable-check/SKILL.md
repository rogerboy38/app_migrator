---
name: paired-deliverable-check
version: 0.1.0
description: Verify linked deliverables across repos or apps before transport or migration work
tools:
  - bench app-migrator generate-plan --json
  - bench app-migrator conflicts --json
app_migrator:
  category: preflight
  substrates:
    - frappe
---

# paired-deliverable-check

Use when transport or migration work may involve linked deliverables across repos or apps.

## Workflow

1. Run `bench app-migrator generate-plan --json` to enumerate linked deliverables
2. Run `bench app-migrator conflicts --json` to surface cross-app conflicts
3. Apply internal pair-detection rules
4. Block if any linked deliverable is missing

## Verifier goal

All linked deliverables are either included or explicitly blocked.
