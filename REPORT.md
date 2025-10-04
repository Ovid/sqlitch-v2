grep -r "TODO\|FIXME\|XXX\|HACK" sqlitch/
pylint sqlitch/
mypy sqlitch/
bandit -r sqlitch/
# SQLitch Python Code Review Report – 2025-10-04

**Reviewer**: GitHub Copilot (automated)

## Scope and References
- Constitution v1.5.0 (`spec/memory/constitution.md`)
- Feature spec & plan (`specs/002-sqlite/spec.md`, `specs/002-sqlite/plan.md`)
- Contract and unit tests under `tests/`
- Implementation in `sqlitch/` (focus on CLI commands, registry, utilities)

---

## Code Quality & Pythonic Style

### 1. Mixed tab/space indentation breaks linters
- **Location**: `sqlitch/cli/commands/bundle.py:L110-L115`, `sqlitch/cli/commands/checkout.py:L154-L159`
- **Issue**: Arguments in `_resolve_plan_path` are indented with a literal tab while surrounding code uses spaces.
- **Why it matters**: Violates PEP 8/ruff `E101`, causing formatting and lint gates to fail; also complicates future diffs.
- **Severity**: Medium

### 2. Unused import in target command
- **Location**: `sqlitch/cli/commands/target.py:L10`
- **Issue**: `config_resolver` is imported but never used.
- **Why it matters**: Fails strict lint gates (flake8 F401) mandated by the constitution; signals incomplete refactor.
- **Severity**: Low

---

## Design & Architecture

### 3. Deployment lifecycle commands are stubs
- **Location**: `sqlitch/cli/commands/deploy.py:L126-L139`, `revert.py:L125-L138`, `rebase.py:L121-L137`, `checkout.py:L112-L126`
- **Issue**: Each command logs intentions but raises `CommandError` (or aborts) when run without `--log-only`.
- **Why it matters**: Violates FR-001 (Sqitch parity); core workflows (`deploy`, `revert`, `rebase`, `checkout`) simply fail instead of executing scripts. Users cannot migrate databases.
- **Severity**: Critical

### 4. Verify and upgrade silently succeed without doing work
- **Location**: `sqlitch/cli/commands/verify.py:L33-L38`, `upgrade.py:L22-L37`
- **Issue**: Both commands print optimistic messages and ignore their arguments instead of touching the registry.
- **Why it matters**: Misleads operators into thinking verification/upgrades ran; breaks Sqitch parity and observability (FR-001, NFR-001).
- **Severity**: High

### 5. Target command ignores config root and quiet mode
- **Location**: `sqlitch/cli/commands/target.py:L39-L184`, `_resolve_config_path` at L187-L199
- **Issue**: Writes directly under `project_root` regardless of the global `--config-root`/`CLIContext.config_root`; emissions ignore `--quiet`.
- **Why it matters**: Global configuration overrides mandated by spec FR-009 are dropped, so user-scoped targets never persist. Violates constitution section V (observability toggles) and causes data to land in the wrong config tree.
- **Severity**: High

### 6. Target list output omits URI column
- **Location**: `sqlitch/cli/commands/target.py:L170-L183`
- **Issue**: The list view prints name/engine/registry but drops the actual `uri`, unlike Sqitch.
- **Why it matters**: Diverges from contract parity (FR-001); users cannot confirm targets without running `show` per target.
- **Severity**: Medium

---

## Maintainability Issues

### 7. `config_command` mixes four workflows in one 120+ line function
- **Location**: `sqlitch/cli/commands/config.py:L33-L120`
- **Issue**: Get/set/unset/list behaviours are interwoven with nested branching.
- **Why it matters**: Difficult to reason about and extend (e.g., adding registry scope support); increases risk of regressions because shared validation logic is duplicated across branches.
- **Severity**: Medium

### 8. Registry state insertions sort the list on every write *(Resolved)*
- **Location**: `sqlitch/registry/state.py`
- **Resolution**: `_insert_entry` now uses bisect insertion with a cached ordering key to maintain sorted order without re-sorting the full list, keeping inserts `O(log n)`.
- **Validation**: `python -m pytest tests/registry -k sort -q` *(fails: No module named pytest in current environment)*

---

## AI-Generated Code Smells

### 9. Exported symbol missing implementation *(Resolved)*
- **Location**: `sqlitch/registry/state.py`
- **Resolution**: Implemented `sort_registry_entries_by_deployment` with deterministic ordering and refactored `deserialize_registry_rows` plus unit tests covering forward and reverse sorts.
- **Validation**: `python -m pytest tests/registry -k sort -q` *(fails: No module named pytest in current environment)*

### 10. Target config helper honours CLI config root *(Resolved)*
- **Location**: `sqlitch/cli/commands/target.py` (`_resolve_config_path`)
- **Resolution**: Helper now checks the CLI `config_root` override before falling back to the project root, reusing Sqitch-compatible filename precedence without the placeholder comment.
- **Validation**: `python -m pytest tests/cli -k target -q` *(fails: No module named pytest in current environment)*

---

## Summary
- **Critical**: Deployment/reversion/rebase/checkout must be implemented to meet FR-001.
- **High**: Fix verify/upgrade placeholders, honour global config/quiet flags, restore missing exports.
- **Medium/Low**: Address style violations, refactor large functions, and improve data structure efficiency to keep quality gates green and performance predictable.

Please tackle critical/high items before continuing feature work to stay constitutionally compliant.
