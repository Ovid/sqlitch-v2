# Audit T025: Global Options Coverage

**Audit Date:** 1759687307.3230746
**Commands Audited:** 19
**Commands with Gaps:** 19 (100.0%)

## Summary

Required global options (from spec.md FR-005):
- `--chdir <path>`: Change working directory before executing command
- `--no-pager`: Disable pager output
- `--quiet`: Suppress informational messages
- `--verbose`: Increase verbosity

### Gap Summary by Option

| Option | Commands Missing | Coverage |
|--------|------------------|----------|
| `--chdir` | 19/19 | 0.0% |
| `--no-pager` | 19/19 | 0.0% |
| `--quiet` | 19/19 | 0.0% |
| `--verbose` | 19/19 | 0.0% |

## Detailed Results

| Command | --chdir | --no-pager | --quiet | --verbose | Status |
|---------|---------|------------|---------|-----------|--------|
| `add` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `bundle` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `checkout` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `config` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `deploy` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `engine` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `help` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `init` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `log` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `plan` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `rebase` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `revert` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `rework` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `show` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `status` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `tag` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `target` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `upgrade` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |
| `verify` | ❌ | ❌ | ❌ | ❌ | ❌ GAPS |

## Commands Requiring Fixes

**19 commands** need global option fixes:

- **add**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **bundle**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **checkout**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **config**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **deploy**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **engine**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **help**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **init**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **log**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **plan**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **rebase**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **revert**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **rework**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **show**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **status**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **tag**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **target**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **upgrade**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`
- **verify**: Missing `--verbose`, `--no-pager`, `--quiet`, `--chdir`

## Recommendations

1. **Create T028 fix task** to add missing global options to 19 commands
2. **Implementation approach**: Add decorators to command functions in `sqlitch/cli/commands/*.py`
3. **Validation**: Re-run regression tests T020-T021 after fixes

### Perl Reference Pattern

From `sqitch/lib/App/Sqitch.pm` (base class for all commands):
```perl
has plan_file => (
    is      => 'ro',
    isa     => Str,
    lazy    => 1,
    default => sub { shift->config->get(key => 'core.plan_file') || 'sqitch.plan' },
);

has verbosity => (
    is      => 'ro',
    isa     => Int,
    default => 1,  # 0=quiet, 1=normal, 2+=verbose
);
```

Global options are inherited by all commands through base class.
