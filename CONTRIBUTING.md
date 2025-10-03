# Contributing to SQLitch

Thanks for helping build the SQLitch Python parity fork! The guidelines below document the day-to-day developer workflow so you can land changes smoothly and keep the project healthy.

## 1. Environment Setup

1. Create and activate a virtual environment (Python 3.11+).
2. Install runtime and tooling dependencies (includes pytest, coverage plugins, linters, tox, etc.).

```bash
pip install ".[dev]"
```

3. All commands below assume the virtual environment remains active.

## 2. Working on Tasks (Red → Green Flow)

1. Each tracked task (e.g., `T052`) must start with a failing test.
2. Add or update tests in `tests/` referencing the task ID inside the skip reason (for example `pytest.mark.skip(reason="Pending T052")`).
3. Immediately before implementing the feature:
   - Remove the skip marker.
   - Run the test to confirm it now fails (Red).
   - Begin implementation and iterate until the test passes (Green).

This workflow is enforced automatically by the skip-check script and CI gates (FR-012).

## 3. Skip-Check Automation (`scripts/check-skips.py`)

The skip checker fails fast when skip markers referencing active tasks remain in the codebase.

### Basic usage

```bash
python scripts/check-skips.py T052 T055
```

### Environment-driven usage

Set `SQLITCH_ACTIVE_TASKS` to let the script (and CI) know which tasks are in flight:

```bash
export SQLITCH_ACTIVE_TASKS="T052,T055"
python scripts/check-skips.py
```

The `tox -e lint` environment runs the script automatically, so the lint job fails if any targeted skips survive.

### When the script fails

You’ll see output like:

```
Detected skip markers referencing active tasks:
  - tests/cli/contracts/test_plan_contract.py:12 -> T052: Pending T052
Remove these skip markers (or update the active task list) before proceeding with implementation.
```

Fix the offending tests by removing—or intentionally keeping—the skip markers and re-running the script until it passes.

## 4. Local Quality Gates

Before opening a pull request, make sure these commands succeed:

```bash
# Unit tests with coverage (≥90% enforced automatically)
pytest -q

# Static analysis, formatting, lint, security
tox -e lint type security
```

Additional tox environments may be added as features land; check `tox.ini` for the latest list.

## 5. Pull Request Checklist

Every PR must check the boxes in `.github/pull_request_template.md`, which cover:

- Skip removal and confirmation that `scripts/check-skips.py` was executed (or the active task environment variable is set).
- Updated/added tests with passing `pytest`.
- Successful `tox -e lint type security` runs.
- Documentation, examples, and fixtures updated when applicable.

## 6. Troubleshooting Tips

- **Coverage failures:** The project enforces `fail_under = 90`. Add targeted tests or expand existing ones to raise coverage before rerunning `pytest`.
- **`mysqlclient` build errors:** The optional dev install (`pip install ".[dev]"`) pulls in database adapters. On macOS you may need Xcode CLT and `pkg-config` (e.g., `brew install pkg-config mysql-client`) before installing `mysqlclient`.
- **Skip removal noise in lint:** If lint fails due to skip markers for tasks you’re *not* working on, double-check that `SQLITCH_ACTIVE_TASKS` only lists your active task IDs.

## 7. Need Help?

- Review the feature plan and task list under `specs/001-we-re-going/` for sequencing and dependencies.
- File issues or start a discussion if you find gaps in these docs; keeping contributor docs current is part of the MVP goals.

Happy hacking! 🎉
