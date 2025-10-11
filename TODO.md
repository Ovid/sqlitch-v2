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

Currently, the `revert` command does not support registry override (line 217 in `sqlitch/cli/commands/revert.py`). This is a low-priority enhancement for post-1.0:

```python
registry_override=None,  # TODO: support registry override
```

**Impact**: Users cannot override registry location for revert operations
**Workaround**: Use default registry resolution
**Priority**: Low (post-1.0 enhancement)
**Tracked**: T064 audit (lockdown phase)

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

