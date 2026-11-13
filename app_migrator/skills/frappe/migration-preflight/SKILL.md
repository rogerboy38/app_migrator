---
name: migration-preflight
version: 0.1.0
description: Pre-flight scan, conflict detection, diagnosis, and health check before destructive migration
tools:
  - bench app-migrator scan --json
  - bench app-migrator conflicts --json
  - bench app-migrator diagnose --json
  - bench app-migrator health --json
  - bench app-migrator generate-plan --json
app_migrator:
  category: preflight
  substrates:
    - frappe
---

# migration-preflight

Use when any DocType move, app merge, uninstall, or staging workflow is about to begin.

## Workflow

1. Run `bench app-migrator scan --json` for substrate inventory
2. Run `bench app-migrator conflicts --json` to detect version or module conflicts
3. Run `bench app-migrator diagnose --json` for the full diagnostic
4. Run `bench app-migrator health --json` for overall bench state
5. Run `bench app-migrator generate-plan --json` to enumerate the plan
6. Block on any unrecoverable blocker

## Verifier goal

Blockers and risks are fully surfaced before a destructive phase begins.
