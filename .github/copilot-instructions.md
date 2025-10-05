# SQLitch Agent Onboarding (Updated 2025-10-05)

## Architecture Snapshot
- `sqlitch/plan/` owns plan parsing (`parser.py`) and immutable domain models (`model.py`). Parsers demand project/default-engine headers and normalize timestamps via `sqlitch.utils.time`.
- `sqlitch/engine/` registers DB targets. `engine/base.py` defines canonical names, connection factories, and the global `ENGINE_REGISTRY`; adapters (e.g., `engine/sqlite.py`) register themselves at import.
- `sqlitch/cli/` bootstraps Click. `cli/main.py` builds a `CLIContext` with config/env resolution, then hydrates command modules through `cli/commands/__init__.py`'s registry.
- Config resolution lives in `sqlitch/config/resolver.py`/`loader.py`, merging system → user → local scopes while rejecting duplicate files per scope.
- Vendored `sqitch/` mirrors upstream Perl fixtures—treat it as read-only and use it for parity comparisons.

## Key Patterns to Follow
- Always add `from __future__ import annotations`, populate `__all__`, and group imports (stdlib, third-party, local).
- Public dataclasses (plan models, CLI context) enforce immutability via `MappingProxyType` and validation in `__post_init__`; extend them through dedicated factory helpers (`Change.create`, etc.).
- CLI commands register once via `@register_command`; tests must call `_clear_registry()` when importing custom command modules to avoid leakage.
- Engine extensions must expose an `Engine` subclass and call `register_engine(..., replace=True)` during module import; tests replace entries with `try/finally` restore (see `docs/architecture/registry-lifecycle.md`).
- Template discovery in `cli/commands/add.py` searches project, config, and `/etc/{sqlitch,sqitch}`; reuse `_discover_template_directories` when introducing new script generators.
- Golden fixtures under `tests/support/golden/` are compared byte-for-byte; never normalize whitespace when loading them.
- Many tests assert timezone awareness—use `sqlitch.utils.time.ensure_timezone`/`parse_iso_datetime` instead of `datetime.fromisoformat` directly.

## Core Workflows
- Install tooling from the repo root:
	```bash
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -e .[dev]
	```
- Run the fast checks (pytest is strict about markers and coverage ≥90%):
	```bash
	source .venv/bin/activate
	python -m pytest
	```
- full gate (lint, type, security) mirrors CI:
	```bash
	source .venv/bin/activate
	python -m tox
	```
- Guard against stale skips before tackling a spec task:
	```bash
	source .venv/bin/activate
	python scripts/check-skips.py T123
	```

## Integration & Testing Notes
- Pytest config (`pyproject.toml`) enables `pytest-randomly`; stabilize flaky tests with deterministic fixtures, not ordering assumptions.
- CLI tests use `click.testing.CliRunner` and patch env via `monkeypatch`; prefer `_build_cli_context` and helpers in `cli/_context.py` over ad-hoc mocks.
- Registry tests snapshot previous state and restore it (`register_engine(..., replace=True)`) to keep global dicts clean.
- Use `tests/support/` helpers when diffing against Sqitch outputs; never hit real databases inside unit tests.

## Reference Docs
- Docs on registry lifecycle: `docs/architecture/registry-lifecycle.md`.
- Current milestone specs: `specs/002-sqlite/plan.md` and related research notes.
- Golden fixture provenance and regeneration: `tests/support/golden/README.md`.