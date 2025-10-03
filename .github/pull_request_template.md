## Summary

- _Describe the scope of this change and reference any relevant task IDs._

## Pre-merge Checklist

- [ ] Removed skip markers for the tasks implemented in this PR and confirmed the tests fail before starting implementation.
- [ ] Ran `python scripts/check-skips.py <TASK IDS>` (or set `SQLITCH_ACTIVE_TASKS`) and resolved any reported skip markers.
- [ ] Added or updated tests covering the change and verified `pytest` passes locally.
- [ ] Ran `tox -e lint type security` (or equivalent) and addressed all findings.
- [ ] Updated documentation, examples, and fixtures as needed.

> Tip: set `SQLITCH_ACTIVE_TASKS="T052,T055"` before running `tox -e lint` to have CI catch forgotten skip markers automatically.
