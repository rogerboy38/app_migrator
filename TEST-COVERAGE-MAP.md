# TEST-COVERAGE-MAP — v0.5-alpha W1 phases × tests × lessons (v2.1)

**Date:** 2026-06-24T02:30:00Z (strict UTC)
**Audit basis:** T3 lessons-learned review + v0.5 spec acceptance gate + T-VERIFY-001 fixes
**Purpose:** map each v0.5-alpha dev phase to its pytest coverage so Coder can pull this into the new `/home/frappe/app_migrator/` scaffold and run `pytest tests/` to validate the W1 close-out.

---

## v2 corrections (per T-VERIFY-001 + T-VERIFY-002)

| Gap | Description | Fix |
|---|---|---|
| 1 | Phase 2 L381 test was circular (fake returned `drift_detected`, test asserted on fake) | v2: input provides TWO hashes, function derives drift. v2.1: hashes loaded from `tests/fixtures/l381_known_stale_keypair.json` (external data, not return-the-truth mock in disguise). |
| 2 | Phase 1 had zero `pytest.skip` calls; would hard-fail on missing scaffold | v2: every test has `require_app_migrator` or `pytest.importorskip` guard. Module-level autouse guard skips whole session if `bench` not on PATH. |
| 3 | Phase 4 `PRIORITY_COMMANDS` listed 6 commands (SIGNED-OFF says 5 + 1 already-had-json) | v2: 5 priority commands; `audit-modules-disk-vs-db` moved to `ALREADY_HAS_JSON`. |
| 4 | All test files hardcoded `/home/frappe/*` paths; can't run on Windows host | v2: `conftest.py` with `app_migrator_root` fixture; `APP_MIGRATOR_ROOT` env var override. v2.1: `app_migrator_root_factory` for runtime override tests. |
| 5 | Phase 5 `test_verifier_3_outcomes` was weak (asserted outcome in set; buggy verifier passing one value would pass) | v2: removed weak test; kept strong pre/post tests + added `test_verifier_outcome_unchanged_when_no_delta` for negative case. |
| 6 | Phase 1 tool-registration test had `"scan" in registered` substring shortcut | v2: exact-match only (set membership); no substring fallback. |

## v2.1 additions (per Verifier T-VERIFY-002 probes + boundary checks)

| Item | Description |
|---|---|
| Conftest env-var override test | `test_app_migrator_root_env_var_override` proves APP_MIGRATOR_ROOT actually drives resolution (Verifier probe a). |
| Conftest default test | `test_app_migrator_root_default_when_env_var_unset` proves default fallback works. |
| L381 fixture file | `tests/fixtures/l381_known_stale_keypair.json` — external known-stale keypair (Verifier probe b: not a return-the-truth mock in disguise). |
| Malformed-JSON policy | Phase 4 `run_bench_json` now distinguishes: non-standard rc → SKIP, rc=0 + non-JSON → FAIL (real bug, not WIP). |
| Missing-frontmatter skip msg | Phase 1 frontmatter skip now clearly identifies the missing element (not silent pass). |
| Corrupt-SQLite handling | Phase 5 sessions test now catches `sqlite3.DatabaseError` and skips with a corrupt-DB message (not stack trace). |

---

## Phase × test × lesson matrix

| Phase | T3 Priority | Test file | Tests | Lessons embodied |
|---|---|---|---|---|
| **1 — Skills layer** | P1 (highest leverage) | `tests/phase1_skills/test_skills_registry.py` | 6 tests (skills list, file existence, frontmatter, tools validation, validate, show) | (no L### code-embodied; this is the SKILLS layer itself) |
| **2 — Verification gaps** | P2 | `tests/phase2_verification/test_verification_gaps.py` | 6 tests (L381 positive + negative, L398 positive + negative, L413 positive + negative, L419) | **L381**, **L398**, **L413**, **L419** |
| **3 — Radar flags** | P3 | `tests/phase3_radar_flags/test_radar_flags.py` | 3 tests (fixture-drift, symbol-collision, severity levels) | **L394** |
| **4 — JSON envelope** | P4 | `tests/phase4_envelope/test_json_envelope.py` | 9 tests (parametrized 6 + audit-modules wrap + malformed-JSON boundary + exit-code) | (envelope design itself, no specific L###) |
| **5 — Planner + verifier** | P5 | `tests/phase5_planner_verifier/test_planner_verifier.py` | 7 tests (dry-run, destructive approval, --yes bypass, improved, regressed, unchanged, sessions SQLite w/ corrupt-DB handling) | (planner/verifier design + U2/Q4 sign-off) |
| **0 — Conftest** | n/a | `tests/conftest.py` | 3 tests (env-var override, default fallback, corrupt-DB boundary) | (test infrastructure) |

**Total: 31 tests across 5 phase files + conftest self-tests.**

---

## Run sequence

```bash
cd /home/frappe/app_migrator
pytest tests/ -v
```

Expected pass condition: **all 31 tests green** at W1 close-out. Any red flag indicates a phase is incomplete (or a malformed-envelope bug, per the new policy).

---

## Test design principles

1. **Each test exercises the lesson's discipline, not just the API.** A test that just calls `get_database_info()` and asserts no exception doesn't validate L381. The L381 test provides TWO external hashes and asserts the function derives drift from their comparison.

2. **Tests skip gracefully if the phase isn't built yet, but FAIL on real bugs.** All tests use `pytest.skip()` for unimplemented CLI commands, but `pytest.fail()` for implemented-but-malformed outputs (Phase 4). This means running `pytest tests/` against an in-progress scaffold shows which phases are pending (skips) vs which have real bugs (fails).

3. **No test fixtures required (except L381 external sample).** Tests use monkeypatch + subprocess to keep them independent of bench/site state. The L381 test reads from `tests/fixtures/l381_known_stale_keypair.json` to make the test data clearly external.

4. **Strict-UTC timestamps in test outputs.** All test logs use ISO-8601 UTC (per TZ-hygiene decision 2026-06-24T00:48:53Z).

5. **Conftest is portable.** `APP_MIGRATOR_ROOT` env var override allows running tests on non-VM2 hosts (CI, Windows). `conftest.py` provides `app_migrator_root` (session-scoped) and `app_migrator_root_factory` (function-callable for env-var override tests).

---

## Cross-reference to v0.5 spec acceptance gate

The v0.5-alpha acceptance gate includes (per the latest spec amendment + T-VERIFY-001 fixes):

> - 5 priority commands support stable --json output (T3 Phase 4 test_envelope_*) — count was 6 in v1, corrected to 5 in v2
> - Five first-wave skills load and validate successfully (T3 Phase 1 test_skills_*)
> - Planner can generate advisory sequences for all five first-wave skills (T3 Phase 5 test_planner_*)
> - Verifier can assess workflows with 3-outcome semantics (T3 Phase 5 test_verifier_*) — weak test removed in v2; only strong pre/post tests remain
> - Session state persists via SQLite (T3 Phase 5 test_sessions_*) — corrupt-DB boundary handling added in v2.1
> - 5 T3 lessons embodied (T3 Phase 2 test_l381/398/413/419 + Phase 3 test_l394 partial) — L407 deliberately omitted (Frappe client-script lesson, not pytest-testable)

---

## Files

| Path | Purpose |
|---|---|
| `tests/conftest.py` | Portable fixtures (env var, scaffold root, skills dir) + 3 self-tests (env-var override, default, corrupt-DB) |
| `tests/fixtures/l381_known_stale_keypair.json` | External known-stale key sample for L381 (per Verifier probe b) |
| `tests/phase1_skills/test_skills_registry.py` | 6 tests for skills layer (exact-match tool registration, no substring shortcut) |
| `tests/phase2_verification/test_verification_gaps.py` | 6 tests for L381 (fixture-driven) / L398 / L413 / L419 (positive + negative cases) |
| `tests/phase3_radar_flags/test_radar_flags.py` | 3 tests for L394 radar flags |
| `tests/phase4_envelope/test_json_envelope.py` | 9 tests for v1.0.0 JSON envelope (parametrized + malformed-JSON policy test) |
| `tests/phase5_planner_verifier/test_planner_verifier.py` | 7 tests for planner + verifier (3-outcome semantics + corrupt-DB handling) |
| `TEST-COVERAGE-MAP.md` (this file) | Phase × test × lesson matrix (v2.1) |
| `TEST_PLAN-existing.md` (already in workspace) | The pre-existing CI/CD test plan (224 lines, focused on Docker deploy, NOT v0.5 scope) |

---

## Notes

- These tests **complement** the existing `TEST_PLAN.md` (which covers CI/CD deployment). The existing plan does NOT cover v0.5 skills/planner/verifier; this file does.
- Tests assume the new scaffold at `/home/frappe/app_migrator/` per T-1A-004. Coder will copy these test files into `tests/` of the new scaffold during S-1A-01.
- Tests run with `pytest` (no Frappe test runner required). Fast feedback loop.
- If a test can't be implemented (e.g., L381 detection needs site context that doesn't exist in scaffold), update the test to be more lenient + add a fixture, but DO NOT delete the test. The lesson's discipline must still be validated.
- The conftest autouse guard `_require_bench_on_path` skips the whole test session if `bench` is not on PATH. This is intentional: tests target the VM2 substrate, not the Windows host.

---

*— Mavis (minimax-1, lead), 2026-06-24T02:30:00Z (v2.1 after T-VERIFY-001 + T-VERIFY-002 fixes)*