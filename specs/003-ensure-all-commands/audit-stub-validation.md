# Audit T027: Stub Argument Validation

**Audit Date:** 1759687424.7874591
**Commands Audited:** 19
**Stub Commands Found:** 5
**Stubs with Validation:** 5

## Validation Contract

Per Sqitch convention (from Perl reference), stub commands must:

1. **Validate arguments BEFORE** showing "not implemented" message
2. **Exit with code 2** if arguments are invalid (usage error)
3. **Exit with code 1** if arguments are valid but command not implemented

This ensures users get immediate feedback on argument problems, even for unimplemented commands.

## Summary by Implementation Status

| Command | Status | Validation | Stub Type |
|---------|--------|------------|-----------|
| `add` | ✅ Implemented | N/A | - |
| `bundle` | ✅ Implemented | N/A | - |
| `checkout` | ✅ Stub | automatic (Click decorators) | message |
| `config` | ✅ Implemented | N/A | - |
| `deploy` | ✅ Implemented | N/A | - |
| `engine` | ✅ Implemented | N/A | - |
| `help` | ✅ Implemented | N/A | - |
| `init` | ✅ Implemented | N/A | - |
| `log` | ✅ Implemented | N/A | - |
| `plan` | ✅ Implemented | N/A | - |
| `rebase` | ✅ Stub | automatic (Click decorators) | message |
| `revert` | ✅ Stub | automatic (Click decorators) | message |
| `rework` | ✅ Implemented | N/A | - |
| `show` | ✅ Implemented | N/A | - |
| `status` | ✅ Implemented | N/A | - |
| `tag` | ✅ Implemented | N/A | - |
| `target` | ✅ Implemented | N/A | - |
| `upgrade` | ✅ Stub | automatic (Click decorators) | message |
| `verify` | ✅ Stub | automatic (Click decorators) | message |

## Detailed Findings

### ✅ Fully Implemented Commands (14)

- `add`
- `bundle`
- `config`
- `deploy`
- `engine`
- `help`
- `init`
- `log`
- `plan`
- `rework`
- `show`
- `status`
- `tag`
- `target`

### ✅ Stubs with Click Validation (5)

These stubs properly validate arguments via Click decorators:

- **checkout** (line 126) (options: --target, --mode, --to-change, --log-only)
- **rebase** (line 146) (options: --target, --onto, --from, --mode, --log-only)
- **revert** (line 137) (options: --target, --to-change, --to-tag, --log-only)
- **upgrade** (line 33) (options: --target, --registry, --log-only)
- **verify** (line 44) (options: --target, --to-change, --to-tag, --event, --mode, --log-only)

### ⚠️ Stubs Needing Validation Review (0)

These stubs may not validate arguments properly:

✅ All stubs use Click validation!

## Compliance Analysis

✅ **All stub commands properly validate arguments via Click decorators!**

Click automatically validates:
- Required arguments presence
- Option types and formats
- Mutually exclusive options

Invalid arguments will exit with code 2 (usage error) before reaching stub message.

## Recommendations

✅ **No action needed** - all stubs properly validate arguments!

Continue following this pattern for future stub commands:
1. Define Click decorators matching Perl command signature
2. Let Click handle automatic validation
3. Stub message only appears for valid arguments
