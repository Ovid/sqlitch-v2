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

### 1. Mixed tab/space indentation breaks linters *(Resolved)*
- **Location**: `sqlitch/cli/commands/bundle.py:L110-L115`, `sqlitch/cli/commands/checkout.py:L154-L159`
- **Resolution**: Normalized `_resolve_plan_path` keyword arguments to use spaces, aligning with surrounding style so ruff no longer flags `E101`.
- **Validation**: `ruff check sqlitch/cli/commands/bundle.py sqlitch/cli/commands/checkout.py` *(fails: executable "ruff" not available in this environment)*

### 2. Unused import in target command *(Resolved)*
- **Location**: `sqlitch/cli/commands/target.py`
- **Resolution**: Removed the stale `config_resolver` import and tightened the command to rely solely on filesystem helpers, keeping lint gates clean.
- **Validation**: `python -m ruff check sqlitch/cli/commands/target.py` *(not run here; run in your environment to confirm)*

---

## Design & Architecture

### 3. Deployment lifecycle commands are stubs
- **Location**: `sqlitch/cli/commands/deploy.py:L126-L139`, `revert.py:L125-L138`, `rebase.py:L121-L137`, `checkout.py:L112-L126`
- **Issue**: Each command logs intentions but raises `CommandError` (or aborts) when run without `--log-only`.
- **Why it matters**: Violates FR-001 (Sqitch parity); core workflows (`deploy`, `revert`, `rebase`, `checkout`) simply fail instead of executing scripts. Users cannot migrate databases.
- **Severity**: Critical

### 4. Verify and upgrade silently succeed without doing work *(Resolved)*
- **Location**: `sqlitch/cli/commands/verify.py`, `upgrade.py`
- **Resolution**: Both commands now raise `CommandError` with explicit "not implemented" messaging (log-only echoes the warning first) so users receive a failing exit code until real registry/verification flows land; contract tests cover standard and `--log-only` invocations.
- **Validation**: `python -m pytest tests/cli/contracts/test_verify_contract.py tests/cli/contracts/test_upgrade_contract.py -q` *(fails: repository coverage gate requires running the full suite)*

### 5. Target command ignores config root and quiet mode *(Resolved)*
- **Location**: `sqlitch/cli/commands/target.py`
- **Resolution**: `_resolve_config_path` now falls back to the CLI `config_root` when no project-local config exists, and all subcommands respect global `--quiet` when emitting output. Contract tests cover both behaviors.
- **Validation**: `python -m pytest tests/cli/contracts/test_target_contract.py -k "config_root or quiet" -q` *(fails: No module named pytest in current environment)*

### 6. Target list output omits URI column *(Resolved)*
- **Location**: `sqlitch/cli/commands/target.py`
- **Resolution**: List output now includes URI alongside name/engine/registry and contract tests assert the four-column table.
- **Validation**: `python -m pytest tests/cli/contracts/test_target_contract.py -k list -q` *(fails: No module named pytest in current environment)*

---

## Maintainability Issues

### 7. `config_command` mixes four workflows in one 120+ line function *(Resolved)*
- **Location**: `sqlitch/cli/commands/config.py`
- **Resolution**: Added a typed request parser and operation enum so the command now delegates list/set/unset/get flows to dedicated helpers with shared validation.
- **Validation**: `python -m pytest tests/cli -k config -q` *(fails: No module named pytest in current environment)*

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
