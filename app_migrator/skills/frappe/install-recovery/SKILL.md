---
name: install-recovery
version: 0.1.0
description: Recover from a destabilized app or bench after a failed install or transport
tools:
  - bench app-migrator health --json
  - bench app-migrator diagnose --json
  - bench app-migrator analyze-apps
  - bench app-migrator git-info
app_migrator:
  category: recovery
  substrates:
    - frappe
---

# install-recovery

Use when a development or transport operation has already destabilized the app or bench and recovery guidance is needed.

## Workflow

1. Run `bench app-migrator health --json` to classify current state
2. Run `bench app-migrator diagnose --json` for failure context
3. Run `bench app-migrator analyze-apps` for app-level diagnostics
4. Run `bench app-migrator git-info` to confirm working tree state
5. Apply v0.5 second-cut recovery helpers

## Verifier goal

System state is classified as recovered, partially recovered, or blocked with explicit next actions.
