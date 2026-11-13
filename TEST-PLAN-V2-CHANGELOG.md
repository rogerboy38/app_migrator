# TEST PLAN v2 — CHANGELOG (2026-06-24T02:32:00Z strict UTC)

**Replaces:** v1 (envelope stamps `20260624T022000Z*`, FAIL verdict from T-VERIFY-001)
**Re-verdict requested:** T-VERIFY-002
**Pushed to:** `s3://frappe-mailbox-prod-2026/{coder,verifier,minimax-1,human}/inbox/20260624T023200Z__minimax-1__test-plan-v2-*`

---

## What's in this push (9 files)

| File | Status | Purpose |
|---|---|---|
| `tests/conftest.py` | NEW | Portable fixtures: `app_migrator_root`, `app_migrator_root_factory`, `skills_dir`, `require_app_migrator`; autouse `_require_bench_on_path` guard; 3 self-tests (env-var override, default, corrupt-DB boundary) |
| `tests/fixtures/l381_known_stale_keypair.json` | NEW | External known-stale key sample for L381 (per Verifier T-VERIFY-002 probe b: NOT a return-the-truth mock in disguise) |
| `tests/phase1_skills/test_skills_registry.py` | REWRITTEN | 6 tests; exact-match tool registration; per-test skip guards |
| `tests/phase2_verification/test_verification_gaps.py` | REWRITTEN | 6 tests (positive + negative cases for L381, L398, L413); L381 reads from fixture file |
| `tests/phase3_radar_flags/test_radar_flags.py` | REWRITTEN | 3 tests; module-level `pytest.importorskip` guard |
| `tests/phase4_envelope/test_json_envelope.py` | REWRITTEN | 9 tests; 5 priority commands (not 6); malformed-JSON = FAIL not SKIP |
| `tests/phase5_planner_verifier/test_planner_verifier.py` | REWRITTEN | 7 tests; weak `test_verifier_3_outcomes` removed; +1 unchanged case; corrupt-SQLite handling |
| `TEST-COVERAGE-MAP.md` | UPDATED v2.1 | Full diff table of v1->v2 corrections + v2.1 additions |
| `TEST-PLAN-V2-CHANGELOG.md` | NEW (this file) | One-page summary for Coder + Verifier |

---

## T-VERIFY-001 gap fixes (6)

1. **Phase 2 L381 test was circular** (fake returned `drift_detected`, test asserted on fake)
   - v2 fix: input provides TWO hashes (not pre-computed drift_detected); function under test must COMPARE them and DERIVE drift.
   - v2.1 fix: hashes loaded from `tests/fixtures/l381_known_stale_keypair.json` (external data, not a return-the-truth mock in disguise).
2. **Phase 1 had zero `pytest.skip` calls** (would hard-fail on missing scaffold)
   - v2 fix: every test has `require_app_migrator` or `pytest.importorskip` guard.
   - v2 fix: conftest.py autouse `_require_bench_on_path` skips whole session if `bench` not on PATH.
3. **Phase 4 `PRIORITY_COMMANDS` listed 6 commands** (SIGNED-OFF says 5 + 1 already-had-json)
   - v2 fix: 5 priority commands (`scan`, `module-conflicts`, `diagnose`, `orphans`, `health`); `audit-modules-disk-vs-db` moved to `ALREADY_HAS_JSON`.
4. **All test files hardcoded `/home/frappe/*` paths** (can't run on Windows host)
   - v2 fix: `conftest.py` provides `app_migrator_root` session-scoped fixture.
   - v2.1 fix: `app_migrator_root_factory` function-callable for runtime env-var override tests.
5. **Phase 5 `test_verifier_3_outcomes` was weak** (asserted outcome in set; buggy verifier passing one value would pass)
   - v2 fix: removed weak test; kept strong pre/post tests.
   - v2 fix: added `test_verifier_outcome_unchanged_when_no_delta` for negative case completeness.
6. **Phase 1 tool-registration test had `"scan" in registered` substring shortcut**
   - v2 fix: exact-match only (set membership); no substring fallback.

---

## T-VERIFY-002 probes + boundary checks (per Verifier pre-flight)

- **Probe (a) conftest env-var override**: verified by `test_app_migrator_root_env_var_override` (sets env var, calls factory, asserts resolved path).
- **Probe (b) L381 fixture-driven test**: confirmed — `tests/fixtures/l381_known_stale_keypair.json` IS in this push bundle (not just referenced).
- **Boundary: malformed JSON envelope** — Phase 4 `run_bench_json` now distinguishes:
  - non-standard rc → SKIP (not implemented)
  - rc=0 + empty stdout → SKIP (WIP)
  - rc in (0,10,20,30,40) + stdout NOT valid JSON → FAIL (real bug)
- **Boundary: missing-frontmatter SKILL.md** — Phase 1 skip message now identifies the missing element ('---' header) with file path.
- **Boundary: corrupt SQLite sessions DB** — Phase 5 catches `sqlite3.DatabaseError`, skips with clear "corrupt-DB, not WIP" message and remediation hint.

---

## Test count: v1 (28 tests) -> v2 (31 tests + 3 conftest self-tests)

| Phase | v1 | v2 | Delta |
|---|---|---|---|
| 1 — Skills | 6 | 6 | unchanged count, tightened (skip guards + exact-match) |
| 2 — Verification | 4 | 6 | +2 (positive + negative cases for L381, L398, L413) |
| 3 — Radar flags | 3 | 3 | unchanged count, module-level importorskip guard added |
| 4 — Envelope | 8 | 9 | +1 (malformed-JSON policy test); parametrized 5 commands instead of 6 |
| 5 — Planner/verifier | 7 | 7 | weak test removed, +1 unchanged case; corrupt-DB handling |
| 0 — Conftest self | 0 | 3 | NEW (env-var override, default, corrupt-DB boundary) |
| **TOTAL** | **28** | **34** | **+6 (4 new + 2 net additions)** |

---

## Run

```bash
cd /home/frappe/app_migrator
APP_MIGRATOR_ROOT=$(pwd) pytest tests/ -v
```

Expected at v1 close: 28 green (skips for unimplemented phases expected).
Expected at W1 close: 34 green (all phases implemented; conftest self-tests green).

---

## Cross-references

- v0.5-alpha acceptance gate: `s3://frappe-mailbox-prod-2026/minimax-1/inbox/20260624T021030Z__minimax-1__V0.5-ALPHA-SIGNED-OFF.md`
- v0.5 spec (with T3): `s3://frappe-mailbox-prod-2026/minimax-1/inbox/20260624T011500Z__minimax-1__V0.5-AMENDMENT-SPEC-AUDIT-AMENDED-with-T3.md`
- T-VERIFY-001 report (FAIL): `s3://frappe-mailbox-prod-2026/verifier/inbox/20260624T022800Z__verifier__T-VERIFY-001-REPORT.md`

---

*— Mavis (minimax-1, lead), 2026-06-24T02:32:00Z strict UTC*
