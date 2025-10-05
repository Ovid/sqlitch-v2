# Registry Lifecycle and Test Isolation

SQLitch maintains two global registries to coordinate pluggable behaviour across the engine and CLI layers. Both registries follow the same high-level lifecycle:

1. **Registration phase** – modules import and register their implementations exactly once during process start up.
2. **Operational phase** – the application treats the registry as immutable and reads from it without synchronization.
3. **Test isolation** – automated tests may temporarily patch registrations but must restore the pre-test state before exiting.

This document records the expected lifecycle, initialization order, and approved reset patterns for each registry so contributors can reason about global state without introducing flaky tests or hard-to-debug side-effects.

## Engine Registry (`sqlitch.engine.base.ENGINE_REGISTRY`)

### Purpose
The engine registry maps canonical engine identifiers (for example `"sqlite"`, `"pg"`, `"mysql"`) to concrete subclasses of `Engine`. CLI commands and deployment orchestration use the registry to instantiate the correct adapter by calling `create_engine()`.

### Registration Phase
- Engine modules call `register_engine()` when they are imported. The SQLite adapter (`sqlitch.engine.sqlite`) registers itself as part of module import, and future adapters (MySQL, PostgreSQL) will follow the same pattern.
- Registration happens deterministically during interpreter start up or explicitly in tests that are exercising registration behaviour.
- Registrations must use canonical names (`canonicalize_engine_name()`) to ensure aliases resolve to the same implementation.

### Operational Phase
- After registration completes, the registry is effectively immutable. Code that needs an engine implementation should call `create_engine()` or `registered_engines()` and **must not** mutate the dictionary directly.
- The registry is a plain dictionary but behaves immutably by convention; writes are limited to the bootstrapping code path.
- Because only reads occur during the operational phase, the registry is safe to use without additional synchronisation under CPython’s dictionary semantics.

### SQLite Registry Attachment Flow
- SQLite deployments resolve a canonical registry URI using `sqlitch.config.resolver.resolve_registry_uri()`. For file-based workspaces the helper derives a sibling `sqitch.db` path (for example `flipr_test.db` → `sqitch.db`), while in-memory or relative targets fall back to a project-root `sqitch.db` unless the user supplies an explicit override.
- `sqlitch.engine.sqlite.SQLiteEngine.connect_workspace()` transparently `ATTACH`es the resolved registry under the canonical alias `sqitch` (`REGISTRY_ATTACHMENT_ALIAS`). Application code always reads and writes registry tables through this alias, guaranteeing parity with the Perl implementation.
- The deploy command coordinates workspace migrations and registry writes inside a single `BEGIN IMMEDIATE` / `COMMIT` block. Any exception triggers a rollback that unwinds both user schema mutations and registry state, satisfying **FR-021** and **FR-022**.
- Test fixtures should prepare registry state via the helpers under `tests.support.sqlite_fixtures` or derive the registry path with `derive_sqlite_registry_uri()` to keep expectations aligned with the production attachment logic.

### Stub Engine Registrations
- The MySQL and PostgreSQL adapters register during import but raise `NotImplementedError` with deterministic parity messaging (see `sqlitch.engine.mysql` / `sqlitch.engine.postgres`). This preserves registry wiring parity and allows the CLI to surface informative errors until full adapters are implemented.
- Tests that temporarily replace these stubs must continue to restore the prior registration, matching the isolation pattern described above.

### Test Isolation
- Tests that temporarily replace a registration must always restore the original value. The recommended pattern is to capture the previous implementation returned by `register_engine(..., replace=True)` and re-register it inside a `try`/`finally` block. If no previous implementation exists, call `unregister_engine()` in the `finally` block instead.
- Avoid clearing the registry wholesale; doing so hides assumptions baked into other tests. Prefer targeted replace/restore logic so fixture order remains deterministic.
- Example:

  ```python
  previous = register_engine("sqlite", FakeEngine, replace=True)
  try:
      ...  # exercise behaviour
  finally:
      if previous is not None:
          register_engine("sqlite", previous, replace=True)
      else:
          unregister_engine("sqlite")
  ```

- Use this pattern whenever a test registers custom engines or inspects the registry contents.

## Command Registry (`sqlitch.cli.commands._COMMAND_REGISTRY`)

### Purpose
The command registry stores lazy wiring callables that attach individual Click commands to the root CLI group. Each command module registers a callable via `@register_command()`.

### Registration Phase
- Modules under `sqlitch.cli.commands` invoke `register_command()` at import time. The `COMMAND_MODULES` tuple controls which modules are imported by `load_commands()` during CLI bootstrap.
- Registration order matches the order of `COMMAND_MODULES`, ensuring deterministic CLI command ordering.

### Operational Phase
- The CLI calls `wire_commands()` (indirectly through `iter_command_registrars()` in `sqlitch.cli.main`) exactly once during start up. After wiring completes, the registry is treated as frozen—commands should not register or deregister themselves at runtime.
- Application code reads the registry via `iter_command_registrars()` or by inspecting `COMMAND_MODULES`, but must never mutate `_COMMAND_REGISTRY` directly outside of controlled registration helpers.

### Test Isolation
- CLI tests must start with a clean registry to avoid leaking registration side-effects across test cases. Use the private helper `_clear_registry()` in module teardown or fixtures to reset state.
- When tests import command modules manually, they should call `_clear_registry()` once the assertions finish to mirror the behaviour of a fresh process.
- Example:

  ```python
  from sqlitch.cli.commands import _clear_registry, add_command

  def teardown_module() -> None:
      _clear_registry()
  ```

- The helper clears only the in-memory command map; it does not modify `COMMAND_MODULES`, allowing tests to simulate custom wiring without disturbing global defaults.

## Cross-Cutting Guidance
- Documented patterns above satisfy **FR-018** (global state minimisation) by constraining when and how registries may change.
- Developers should treat both registries as immutable after initialisation and prefer dependency injection or explicit parameters for behaviour that varies at runtime.
- When adding new registries, follow the same format: describe the registration/operational phases and provide sanctioned test hooks.
