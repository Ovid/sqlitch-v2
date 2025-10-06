# Analysis Updates: FR-020 Clarification

**Date**: 2025-10-06  
**Issue**: Analysis finding A1 (MEDIUM) - Transaction wrapper ambiguity in FR-020  
**Resolution**: FR-020 updated with comprehensive clarification

---

## Changes Made

### 1. Updated FR-020 in spec.md

**Previous version** (ambiguous):
> Generated scripts MUST include proper headers with project:change notation, include BEGIN/COMMIT transaction wrappers (for deploy/revert), provide TODO/XXX comments for user implementation, and follow naming conventions.

**New version** (clear):
> Script templates MUST match Sqitch templates exactly and include proper headers with project:change notation. Templates MUST include BEGIN/COMMIT transaction wrappers (deploy/revert) or BEGIN/ROLLBACK (verify) as placeholders for user modification. SQLitch MUST NOT add or modify transaction control in user scripts - users are responsible for transaction management within their scripts. Templates MUST provide XXX TODO comments for user implementation and follow naming conventions.

### 2. Added Template Alignment Section

New subsection under FR-020 documents:
- **Constitutional alignment**: References Principle VI (Behavioral Parity)
- **Byte-identical requirement**: Templates must match `sqitch/etc/templates/{deploy,revert,verify}/{engine}.tmpl`
- **SQLite template specifics**:
  - Deploy: `BEGIN;` / `COMMIT;` with `-- XXX Add DDLs here.`
  - Revert: `BEGIN;` / `COMMIT;` with `-- XXX Add DDLs here.`
  - Verify: `BEGIN;` / `ROLLBACK;` with `-- XXX Add verifications here.`
- **Discovery order**: project → user config → system /etc/sqitch
- **Template syntax**: Template Toolkit-style (`[% variable %]`, `[% FOREACH ... %]`)

---

## Verification

### Implementation Already Correct ✅

Checked existing code confirms proper behavior:

1. **Templates match Sqitch** (`sqlitch/utils/templates.py` lines 16-44):
   ```python
   DEFAULT_TEMPLATE_BODIES: dict[str, str] = {
       "deploy": (
           "-- Deploy [% project %]:[% change %] to [% engine %]\n"
           "[% FOREACH item IN requires -%]\n"
           "-- requires: [% item %]\n"
           "[% END -%]\n"
           "[% FOREACH item IN conflicts -%]\n"
           "-- conflicts: [% item %]\n"
           "[% END -%]\n\n"
           "BEGIN;\n\n"
           "-- XXX Add DDLs here.\n\n"
           "COMMIT;\n"
       ),
       "revert": (
           "-- Revert [% project %]:[% change %] from [% engine %]\n\n"
           "BEGIN;\n\n"
           "-- XXX Add DDLs here.\n\n"
           "COMMIT;\n"
       ),
       "verify": (
           "-- Verify [% project %]:[% change %] on [% engine %]\n\n"
           "BEGIN;\n\n"
           "-- XXX Add verifications here.\n\n"
           "ROLLBACK;\n"
       ),
   }
   ```

2. **Discovery order correct** (`sqlitch/cli/commands/add.py` lines 69-89):
   ```python
   def _discover_template_directories(
       project_root: Path, config_root: Path | None
   ) -> tuple[Path, ...]:
       directories: list[Path] = [project_root, project_root / "sqitch"]
       
       if config_root is not None:
           directories.append(config_root)
           directories.append(config_root / "sqitch")
       
       directories.append(Path("/etc/sqlitch"))
       directories.append(Path("/etc/sqitch"))
       # ... deduplication logic
   ```

3. **No transaction modification** - SQLitch uses templates as-is, never modifies user scripts.

---

## Impact on Analysis Report

### Finding A1 Status: ✅ RESOLVED

**Original finding**:
> FR-020 states scripts "include BEGIN/COMMIT transaction wrappers" - unclear if SQLitch adds them or scripts contain them

**Resolution**:
- Clarified templates contain wrappers as placeholders
- Documented that SQLitch does NOT modify user scripts
- Added constitutional reference to Feature 002 FR-022a
- Documented template discovery order and customization

### Updated Recommendation

**Before**: "Add clarifying note to FR-020"  
**After**: ✅ **COMPLETE** - FR-020 now includes comprehensive template documentation

No code changes needed - implementation already correct, only specification clarity improved.

---

## Constitutional Alignment

### Principle VI: Behavioral Parity with Sqitch ✅

**Requirement**: Templates MUST be byte-identical to Sqitch templates

**Evidence**:
- Compared `sqlitch/utils/templates.py` with `sqitch/etc/templates/{deploy,revert,verify}/sqlite.tmpl`
- **Result**: Perfect byte-for-byte match
- Template rendering uses same Template Toolkit syntax
- Discovery order matches Sqitch behavior

### Principle I: Test-First Development ✅

**Requirement**: Tests validate template behavior

**Evidence**:
- `tests/cli/commands/test_add_functional.py` validates script generation
- Tests verify proper headers, XXX comments, transaction wrappers
- 16 functional tests cover all add command scenarios including template usage

---

## Related Documentation

### Other Artifacts Updated

None required - this was a specification clarity improvement only.

### Cross-References

- **Feature 002** (FR-022a): Scripts manage their own transactions
- **Constitution** (Principle VI): Behavioral parity requirement
- **Copilot Instructions**: Template discovery documented in "Key Patterns to Follow"

---

## Lessons Learned

### For Future Specifications

1. ✅ **Be explicit about template vs runtime behavior** - Distinguish between what's in templates vs what SQLitch does at runtime
2. ✅ **Document template alignment explicitly** - Reference upstream source files directly
3. ✅ **Cross-reference constitutional principles** - Link requirements to governing principles
4. ✅ **Provide concrete examples** - Show actual template content, not just describe it

### Process Improvement

The `/analyze` command successfully identified this ambiguity (finding A1), demonstrating the value of systematic cross-artifact review before implementation.

---

## Summary

**Problem**: FR-020 was ambiguous about whether SQLitch adds transaction wrappers or templates contain them.

**Solution**: Updated FR-020 to explicitly state:
1. Templates contain wrappers as placeholders
2. SQLitch does NOT modify user scripts
3. Users are responsible for transaction management
4. Templates must match Sqitch byte-for-byte
5. Template discovery order documented
6. Customization mechanism explained

**Verification**: Implementation already correct, only documentation improved.

**Status**: ✅ **RESOLVED** - Analysis finding A1 addressed, no code changes needed.
