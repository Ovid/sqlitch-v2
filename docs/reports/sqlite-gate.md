# SQLite Manual Parity Gate (T081)

- **Date:** 2025-10-05
- **Feature Scope:** T013–T015 integration validation
- **Owner:** Full CLI and engine subsystem
- **Status:** ⚠️ Partially verified (lint gate pending legacy formatting cleanup)

## Environment
- macOS (local workstation)
- Python 3.11.11 (virtualenv at `.venv`)
- sqlite3 stdlib driver

## Automated Verification
The full pytest matrix now covers the refreshed golden fixtures and structured logging changes.

```bash
pytest
```

Outcome:
- 368 passed, 12 skipped (documented regression placeholders)
- Coverage: 90.76% (≥ 90% gate)
- Stub engine skip messaging asserted via `tests/regression/test_engine_suite_skips.py`

Structured deploy logging parity is captured in `tests/support/golden/registry/sqlite/deploy_structured_log.jsonl`. The sample records the resolved registry URI and per-change `transaction_scope`, mirroring the data observed in the latest run.

## Lint / Type / Security Gate

```bash
tox -e lint
```

Result: **FAILED** – `black --check` reports 11 legacy modules that would be reformatted (pre-existing drift). No new files from this feature violate formatting; a follow-up T035 task should normalize the repository so the gate can pass automatically.

## Notes & Next Actions
- Refreshing the SQLite goldens ensures Sqitch parity snapshots include the new registry attachment behavior and structured transaction logging.
- Documentation now references the canonical structured log sample and updated credential redaction safeguards.
- Lint failure is limited to historical formatting debt; no regressions detected in new code paths. Schedule a dedicated formatting pass before closing the milestone.
