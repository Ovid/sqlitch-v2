# SQLitch Agent Onboarding (Updated 2025-10-09)

## Orientation
- Python 3.11 project targeting parity with Perl Sqitch; Click powers the CLI under `sqlitch/cli/` and domain models live in `sqlitch/plan/`, `sqlitch/config/`, and `sqlitch/engine/`.
- Treat the vendored `sqitch/` directory as read-only fixtures for parity comparisons.
- Specs in `specs/004-sqlitch-tutorial-parity/` track current milestone expectations and golden outputs.

## Architecture Highlights
- Plans: `sqlitch/plan/parser.py` requires plan headers (project + default engine) and normalizes timestamps with `sqlitch.utils.time`. Models in `plan/model.py` are immutable via `MappingProxyType` and factory constructors (`Change.create`).
- Engines: `sqlitch/engine/base.py` exposes `ENGINE_REGISTRY`; adapters (e.g., `engine/sqlite.py`) register themselves at import with `register_engine(..., replace=True)`. Tests must restore registry state with `try/finally`.
- CLI Bootstrap: `cli/main.py` builds a `CLIContext` (env + config resolution) and pulls command modules through `cli/commands/__init__.py`. Commands register once via `@register_command` and must call `_clear_registry()` in tests before re-registration.
- Config: Loader/resolver merge system → user → local scopes (`config/loader.py`, `config/resolver.py`) and reject duplicate files per scope. Use `sqlitch.utils.time.ensure_timezone`/`parse_iso_datetime` for datetime handling.

## Conventions to Honor
- Every new module starts with `from __future__ import annotations`, defines `__all__`, and groups imports (stdlib, third-party, local).
- Public dataclasses remain frozen; mutate via helper factories rather than `__post_init__` hacks.
- Template discovery (plan/add workflows) must reuse `_discover_template_directories` in `cli/commands/add.py` to search project, config, and `/etc/{sqlitch,sqitch}` roots.
- Tests comparing outputs rely on byte-for-byte fixtures under `tests/support/golden/`; never strip whitespace.
- Tutorial parity harness reads overrides from `tests/support/tutorial_parity/` (see `env_overrides.json`) when simulating CLI runs.

## Workflow Basics
- Bootstrap env:
	```bash
	python3 -m venv .venv
	source .venv/bin/activate
	pip install -e .[dev]
	```
- Fast verification (coverage ≥90% is enforced):
	```bash
	source .venv/bin/activate
	python -m pytest
	```
- Full lint/type/security gate mirrors CI:
	```bash
	source .venv/bin/activate
	python -m tox
	```
- Before modifying spec-driven tests, run the skip guard:
	```bash
	source .venv/bin/activate
	python scripts/check-skips.py T123
	```

## Testing & Diagnostics
- Pytest runs with `pytest-randomly`; stabilize tests via deterministic fixtures, not ordering assumptions.
- Use `click.testing.CliRunner` helpers in `cli/_context.py` to build CLI contexts; avoid manual env juggling.
- Registry/engine tests should snapshot registry state and restore it with `register_engine(..., replace=True)` inside `try/finally`.
- Integration parity suites live under `tests/cli/commands/`, `tests/regression/`, and tutorial scenarios in `tests/support/tutorial_parity/`.

## Reference Points
- Registry lifecycle details: `docs/architecture/registry-lifecycle.md`.
- Tutorial quickstart and contracts: `specs/004-sqlitch-tutorial-parity/`.
- Golden fixture regeneration guidance: `tests/support/golden/README.md`.
