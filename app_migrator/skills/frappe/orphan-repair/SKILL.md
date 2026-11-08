---
name: orphan-repair
version: 0.1.0
description: Repair orphan doctypes, broken module ownership, app-field inconsistency, or uninstall risk
tools:
  - bench app-migrator orphans --json
  - bench app-migrator scan --json
  - bench app-migrator fix-modules
  - bench app-migrator fix-app-field
  - bench app-migrator fix-json-app
  - bench app-migrator ensure-controllers
app_migrator:
  category: repair
  substrates:
    - frappe
---

# orphan-repair

Use when a site shows orphaned DocTypes, broken module ownership, app-field inconsistency, or uninstall risk.

## Workflow

1. Run `bench app-migrator orphans --json` to detect orphan doctypes
2. Run `bench app-migrator scan --json` to get the full picture
3. Apply `fix-modules` and `fix-app-field` as needed
4. Run `fix-json-app` if JSON-based apps need normalization
5. Run `ensure-controllers` to restore controller coverage

## Verifier goal

Orphan count reduced, module ownership normalized, controller coverage restored.
