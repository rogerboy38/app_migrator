---
name: module-collision-preflight
version: 0.1.0
description: Detect module/package shadowing and path collisions before install, import, or migrate
tools:
  - bench app-migrator diagnose --json
  - bench app-migrator health --json
app_migrator:
  category: preflight
  substrates:
    - frappe
---

# module-collision-preflight

Use when install, import, or migrate failures suggest module/package shadowing or path collisions.

## Workflow

1. Run `bench app-migrator diagnose --json` to surface collision candidates
2. Run `bench app-migrator health --json` to check overall bench state
3. Apply internal collision preflight checks (per the underlying engine)
4. Block install if collision is detected

## Verifier goal

Collision eliminated or explicitly blocked before install proceeds.
