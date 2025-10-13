# Identical sqitch behavior out of the box

By default, we should be 100% compatible with sqitch, howeever, we might want
mroe reasonable default for our local project. For example, in our
`sqitch.conf`, we might have this:

    [core]
        engine = sqlite
        compat = sqitch # default behavior if this is missing
        # plan_file = sqitch.plan
        # top_dir = .

But we should be able to:

    sqlitch init myproject \
        --uri https://github.com/user/project/
        --engine sqlite
        --compat sqlitch # only sqlitch or sqitch allowed

At this point, it would create a `sqlitch.conf` file similar to this:

    [core]
        engine = sqlite
        compat = sqlitch # uses sqlitch.* files
        top_dir = sqlitch
        # plan_file = sqlitch/sqlitch.plan
        # deploy_dir = sqlitch/deploy/
        # revert_dir = sqlitch/revert/
        # verify_dir = sqlitch/verify/
        # extension = sql

That avoids the issue where we have a sqitch.conf, sqitch.plan, deploy/, verify/, delete/
all dumped in your top-level directory. Instead, you'll just have a
`sqlicth/conf` and a `sqlitch/` directory, the latter of which contains all of
your files.

# SQLITCH env variables need to be fixed

# Registry Override Support

Currently, the `revert` command does not support registry override (line 245 in `sqlitch/cli/commands/revert.py`). This is a low-priority enhancement for post-lockdown release:

```python
registry_override=None,  # TODO: support registry override (see TODO.md)
```

**Impact**: Users cannot override registry location for revert operations
**Workaround**: Use default registry resolution
**Priority**: Low (post-lockdown enhancement)
**Tracked**: T156 (lockdown phase - documented and suppressed)
**Owner**: TBD
**Timeline**: Post-lockdown feature work

# Dups in _seed tests

        modified:   tests/cli/contracts/test_checkout_contract.py
        modified:   tests/cli/contracts/test_deploy_contract.py
        modified:   tests/cli/contracts/test_plan_contract.py
        modified:   tests/cli/contracts/test_rebase_contract.py
        modified:   tests/cli/contracts/test_revert_contract.py
        modified:   tests/cli/test_rework_helpers.py

# Post-1.0 Improvements (Lessons from Lockdown Phase)

## Code Quality & Type Safety
- **mypy --strict compliance**: 65 remaining type errors, primarily in CLI commands (deploy, revert, status, target). Focus on:
  - Optional type handling in CLI options
  - ConfigParser type annotations
  - Tuple unpacking in registry state
- **pydocstyle full coverage**: Lockdown modules (config, registry, identity) are compliant. Extend to all modules:
  - Fix D202 (blank line after docstring) across plan/, utils/, cli/
  - Add missing magic method docstrings
  - Use imperative mood for factory methods (D401)

## UAT & Testing
- **Multi-engine UAT support**: Extend compatibility scripts (side-by-side, forward, backward) to MySQL and PostgreSQL
  - Requires Docker orchestration
  - Need golden fixtures for each engine
  - Consider conditional execution based on available engines
- **UAT automation exploration**: Current manual execution works well but consider:
  - Nightly CI runs with flake detection
  - Performance regression tracking across releases
  - Automated evidence capture and artifact storage
- **Windows testing**: Identity fallback tests skip on non-Windows. Need Windows CI or test harness.

## Security & Dependencies
- **CVE-2025-8869 remediation**: Monitor pip 25.3 release (fixes tarfile extraction vulnerability)
  - Update as soon as available
  - Re-run pip-audit and update SECURITY.md
- **Dependency hygiene**: Consider pinning transitive dependencies for reproducible builds

## Documentation
- **API stability contract**: Before v2.0, document which modules are public API vs internal
- **Migration guides**: If registry schema changes, provide upgrade path documentation
- **Troubleshooting expansions**: Capture common issues from community feedback

## Architecture & Performance
- **Registry performance**: Large deployments may benefit from:
  - Indexed registry queries
  - Batch operations for multi-change deployments
  - Connection pooling for remote databases (MySQL/PostgreSQL)
- **Parallel deployment**: Explore concurrent change execution when dependencies allow

## Pylint Code Quality Improvements (Phase 3.8 - T147-T151)

### T147: Duplicate Code Between MySQL and PostgreSQL Engines
**Issue**: 56 duplicate-code violations detected by pylint between `sqlitch/engine/mysql.py` and `sqlitch/engine/postgres.py`

**Root Cause**: MySQL and PostgreSQL engines share significant implementation:
- Connection string parsing
- Registry initialization
- Transaction management
- Script execution patterns
- Error handling

**Recommendation**: 
1. Create `sqlitch/engine/sql_base.py` abstract base class for SQL-based engines
2. Extract common methods:
   - `_parse_connection_string()`
   - `_initialize_registry_tables()`
   - `_execute_in_transaction()`
   - `_format_error_message()`
3. Keep engine-specific SQL dialect handling in subclasses

**Priority**: Medium - engines work correctly, refactor improves maintainability

**Estimated Effort**: 4-6 hours to extract base class and update tests

**Related**: Consider extending to future engines (MariaDB, Oracle, SQL Server)

---

### T148: Function Complexity - Too Many Local Variables
**Issue**: 33 functions with >15 local variables flagged by pylint

**Primary Offenders**:
1. `sqlitch/config/loader.py::load_config()` - 24 local variables
   - Recommendation: Extract `_load_system_config()`, `_load_user_config()`, `_load_local_config()`
   
2. `sqlitch/cli/commands/deploy.py::deploy()` - 20+ local variables
   - Recommendation: Extract `_validate_deployment_context()`, `_prepare_changes()`
   
3. `sqlitch/cli/commands/revert.py::revert()` - 18+ local variables
   - Recommendation: Extract `_calculate_revert_range()`, `_validate_revert_safety()`

**Approach**: Extract logical groupings into helper functions while preserving test coverage

**Priority**: Low - functions work correctly, refactor improves readability

**Estimated Effort**: 1-2 hours per complex function

---

### T149: Function Complexity - Too Many Arguments
**Issue**: 16 functions with >5 arguments flagged by pylint

**Primary Offenders**:
1. CLI command handlers with many Click options (acceptable for CLI layer)
2. Registry state update functions with multiple fields

**Recommendation**:
- For CLI commands: Keep as-is (Click pattern, user-facing options)
- For internal functions: Consider dataclasses or TypedDict for parameter grouping
  - Example: `DeploymentContext(target, registry, engine, dry_run, ...)`

**Priority**: Low - mostly cosmetic for non-CLI code

**Estimated Effort**: 2-3 hours to introduce parameter objects

---

### T150: Unused Arguments in Function Signatures
**Issue**: 67 functions with unused arguments flagged by pylint

**Categories**:
1. **Click command handlers**: Context/options provided but not always used (67% of violations)
   - Recommendation: Prefix with `_` to signal intent: `_ctx`, `_verbose`
   
2. **Interface implementations**: Required by base class/protocol but not used in specific implementation
   - Recommendation: Add `# pylint: disable=unused-argument` with explanation
   
3. **Future extensibility**: Parameters reserved for future use
   - Recommendation: Document intent in docstring

**Approach**: 
- Review each case individually
- Rename or suppress with clear justification
- Remove if truly unnecessary

**Priority**: Low - cosmetic improvement

**Estimated Effort**: 3-4 hours to review and fix all cases

---

### T151: Missing Function Docstrings
**Issue**: 11 functions missing docstrings identified by pylint

**To Identify**: Run `pylint sqlitch --disable=all --enable=missing-function-docstring`

**Standard Format Required**:
```python
def function_name(arg1: Type1, arg2: Type2) -> ReturnType:
    """Brief one-line description.
    
    Longer description if needed, explaining purpose,
    approach, or important behaviors.
    
    Args:
        arg1: Description of arg1
        arg2: Description of arg2
        
    Returns:
        Description of return value
        
    Raises:
        ExceptionType: When and why it's raised
    """
```

**Priority**: Medium - improves API discoverability

**Estimated Effort**: 1-2 hours (15-20 minutes per docstring)

**Coordination**: Align with pydocstyle gate to avoid duplication

---

## Summary of Pylint Improvements

| Task | Issue Type | Count | Priority | Effort | Status |
|------|-----------|-------|----------|--------|--------|
| T147 | Duplicate code | 56 | Medium | 4-6h | Documented |
| T148 | Too many locals | 33 | Low | 1-2h each | Documented |
| T149 | Too many arguments | 16 | Low | 2-3h | Documented |
| T150 | Unused arguments | 67 | Low | 3-4h | Documented |
| T151 | Missing docstrings | 11 | Medium | 1-2h | Documented |

**Total Estimated Effort**: 15-25 hours for complete pylint cleanup

**Recommendation**: Address in order: T151 (docstrings), T147 (duplicate code), T148 (complexity), T150 (unused args), T149 (arguments)
- **Plugin system**: Consider extensibility for custom engines/hooks

## Developer Experience
- **Template packaging**: Templates currently discovered via filesystem search. Consider:
  - Package templates as resources
  - Support custom template repositories
  - Template validation on init
- **Error messages**: Audit error output for clarity and actionable guidance
- **Debug logging**: Add verbose mode for troubleshooting complex deployments

## Sqitch Parity Gaps
- **Registry override in revert**: Currently unsupported (tracked TODO in revert.py:217)
- **Bundle command**: Basic implementation exists; verify full parity with Sqitch
- **Upgrade command**: Verify registry migration edge cases
- **Rebase edge cases**: Review complex rebase scenarios

## Code Architecture Improvements

### Deploy Command Refactoring (Pylint T130b)
**Issue**: `sqlitch/cli/commands/deploy.py` exceeds 1000 lines (1766 total), violating maintainability best practices.

**Context**: The deploy module is the core deployment orchestration logic, handling:
- Change plan resolution and sequencing
- Dependency validation and topological sorting
- Script execution and transaction management
- Registry state tracking
- Error handling and rollback scenarios
- Progress reporting and logging

**Recommendation**: Post-lockdown refactoring to improve maintainability:
1. Extract helper modules:
   - `deploy_planner.py` - Change resolution and dependency sorting
   - `deploy_executor.py` - Script execution and transaction handling
   - `deploy_validator.py` - Pre-deployment validation checks
   - `deploy_reporter.py` - Progress and status output formatting
2. Consider state machine pattern for deployment flow
3. Extract data structures into typed dataclasses for parameter passing
4. Keep main CLI handler as thin orchestrator

**Effort**: 8-12 hours (requires careful testing to maintain behavioral parity)

**Priority**: P3 (post-lockdown, post-alpha)

**Rationale**: Splitting requires careful design to maintain Sqitch behavioral parity and avoid breaking existing tests. Current structure is complex but functional and well-tested.

---

## Community & Adoption
- **Example projects**: Create sample repositories demonstrating:
  - SQLite → PostgreSQL migration
  - Multi-environment workflows (dev/staging/prod)
  - CI/CD integration patterns
- **Blog posts / tutorials**: Complement official docs with guided walkthroughs
- **Performance benchmarks**: Publish metrics comparing SQLitch vs Sqitch execution time

---

**Captured**: 2025-10-11 (T066 - Lockdown retrospective)  
**Next Review**: After v1.0 release and initial community feedback

