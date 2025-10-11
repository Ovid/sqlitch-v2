# SQLitch Agent Onboarding (Updated 2025-10-11)

## Mission & Scope
- Python 3.11 rewrite chasing parity with Perl Sqitch; CLI is Click-based under `sqlitch/cli/`, domain layers live in `sqlitch/plan/`, `sqlitch/config/`, and `sqlitch/engine/`.
- Treat the vendored `sqitch/` tree as immutable fixtures and compare against the parity specs in `specs/004-sqlitch-tutorial-parity/`.
- Current milestone: full SQLite tutorial support while other engines incubate; consult `TODO.md` and specs for in-flight gaps.

## Architecture Touchpoints
- CLI bootstrap (`cli/main.py`) builds a `CLIContext`, toggles global JSON mode, and wires commands discovered via `cli/commands/__init__.py`; tests must call `_clear_registry()` before re-registering commands.
- Each command module registers exactly once with `@register_command`; structure handlers to consume `click.get_current_context().obj` as the `CLIContext` rather than reading globals.
- Structured logging flows through `sqlitch.utils.logging`; `CommandError` automatically suppresses output in JSON mode, so prefer raising it for user-facing failures.
- Plan parsing (`plan/parser.py`) requires `%project` + `%default_engine`; compact entries auto-slug script names, while rework detection rewrites script paths to `deploy/users@v1.sql` style when tags are present.
- Plan models (`plan/model.py`) and registry DTOs are frozen; use factory helpers like `Change.create` and `with_updated_…` functions instead of mutating attributes.
- Config loader/resolve path (`config/loader.py`, `config/resolver.py`) merges system → user → local and rejects duplicate files per scope; rely on `resolver.determine_config_root` before touching disk.
- Engine adapters register through `register_engine(..., replace=True)` at import time; snapshot and restore `ENGINE_REGISTRY` in tests to avoid contaminating later cases.

## Patterns & Conventions
- Every module begins with `from __future__ import annotations`, defines `__all__`, and groups imports stdlib → third-party → local.
- Time handling always goes through `sqlitch.utils.time` helpers (`ensure_timezone`, `parse_iso_datetime`, `isoformat_utc`); never construct naive `datetime` objects.
- Template discovery for `sqlitch add` must reuse `_discover_template_directories` (`cli/commands/add.py`) to search project, config, `~/.sqitch`, and `/etc/{sqlitch,sqitch}` roots.
- CLI tests should build contexts with `tests` fixtures in `cli/_context.py` and `CliRunner` utilities—avoid manually crafting env dicts.
- Golden comparisons (`tests/support/golden/`) are byte-for-byte: preserve trailing whitespace and newline conventions when regenerating fixtures.

## Developer Workflow
- Setup: `python3 -m venv .venv && source .venv/bin/activate && pip install -e .[dev]`.
- Quick guard: `python -m pytest` (coverage ≥90% enforced); isolate runs from your real `~/.sqitch` dir per `README.md` warning.
- Full gate: `python -m tox` mirrors CI lint, type, and security checks.
- Spec edits: run `python scripts/check-skips.py T123` (replace ID) before lifting a skip tied to a tracked task.

## Testing Playbook
- Integration parity suites live in `tests/cli/commands/`, `tests/regression/`, and tutorial harness data under `tests/support/tutorial_parity/` (env overrides in `env_overrides.json`).
- Use `tests/support/README.md` for fixture contracts and `tests/support/golden/README.md` when regenerating outputs.
- For engine work, consult `docs/architecture/registry-lifecycle.md` and ensure registries are restored in `try/finally` blocks.

## Quick Reference
- Logging contract: `docs/architecture/registry-lifecycle.md` and `sqlitch/utils/logging.py` outline event names expected by downstream tooling.
- Tutorial walkthrough: `specs/004-sqlitch-tutorial-parity/quickstart.md` documents the expected CLI transcript.
- Don’t modify `sqitch/` or tutorial fixtures directly; add mirrors under `tests/support` if new comparisons are required.
