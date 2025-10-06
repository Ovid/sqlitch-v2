# CRITICAL BUG: Plan File Format Mismatch

**Date Discovered**: 2025-10-06  
**Severity**: BLOCKING  
**Affects**: Tutorial parity, Sqitch interoperability  
**Status**: OPEN - Task T055a created

---

## Problem Summary

The SQLitch plan formatter currently outputs a **verbose metadata format** which is incompatible with Sqitch and violates the Feature 004 specification (FR-019a).

### Current Behavior (WRONG)
```
%syntax-version=1.0.0
%project=flipr
%default_engine=sqlite
%uri=https://github.com/sqitchers/sqitch-sqlite-intro/

change users deploy/users.sql revert/users.sql verify=verify/users.sql planner=poecurt planned_at=2025-10-06T19:38:09Z notes='Creates table to track our users.'
```

### Expected Behavior (Sqitch Format)
```
%syntax-version=1.0.0
%project=flipr
%uri=https://github.com/sqitchers/sqitch-sqlite-intro/

users 2025-10-06T19:38:09Z Test User <test@example.com> # Creates table to track our users.
```

---

## Root Cause

**File**: `sqlitch/plan/formatter.py`  
**Function**: `_format_change()` (lines 100+)

The formatter was designed to output a verbose format with key=value pairs, but the specification requires compact Sqitch-compatible format for interoperability.

### Current Implementation (Verbose)
```python
def _format_change(change: Change, base_path: Path) -> str:
    tokens = [
        "change",
        change.name,
        _format_script_path(change.script_paths["deploy"], base_path),
        _format_script_path(change.script_paths["revert"], base_path),
    ]
    # ... adds verify=, planner=, planned_at=, notes=, depends=, tags=, change_id=
    return " ".join(tokens)
```

### Required Implementation (Compact)
```python
def _format_change(change: Change, base_path: Path) -> str:
    # Format: <name> [dependencies] <timestamp> <planner> # <note>
    parts = [change.name]
    
    if change.dependencies:
        parts.append(f"[{' '.join(change.dependencies)}]")
    
    parts.append(_format_timestamp(change.planned_at))
    parts.append(change.planner)
    
    if change.notes:
        parts.append(f"# {change.notes}")
    
    return " ".join(parts)
```

---

## Specification Reference

From `specs/004-sqlitch-tutorial-parity/spec.md` (FR-019a):

> **Change Entry Format** (compact Sqitch-compatible format):
> ```
> <change_name> [<dependencies>] <timestamp> <planner> # <note>
> ```
> 
> **Verbose Format Support** (for internal use only):
> SQLitch parser MUST also support a verbose metadata format for backward compatibility:
> ```
> change <name> <deploy_path> <revert_path> [verify=<verify_path>] planner=<planner> ...
> ```
> 
> However, all SQLitch commands that write plan files (init, add, tag, rework) MUST output the compact Sqitch-compatible format to maintain interoperability. The verbose format exists only for parsing legacy SQLitch files.

---

## Impact Analysis

### ✅ Parser Status (CORRECT)
The parser in `sqlitch/plan/parser.py` **already supports both formats**:
- `_parse_compact_entry()` - Handles Sqitch compact format (lines 178-232)
- `_parse_change()` - Handles verbose metadata format (lines 104-141)

This is correct! The parser maintains backward compatibility.

### ❌ Formatter Status (BROKEN)
The formatter **only outputs verbose format**, violating the spec:
- `_format_change()` - Outputs verbose format (lines ~95-118)
- `_format_tag()` - Outputs verbose format (lines ~121-129)

### Affected Commands
All commands that write plan files are affected:
1. `sqlitch init` - Creates initial plan file
2. `sqlitch add` - Appends changes to plan
3. `sqlitch tag` - Adds tags to plan
4. `sqlitch rework` - Creates versioned changes in plan

### Affected Tests
Tests that will need updates:
1. `tests/plan/test_formatter.py` - Currently expects verbose format (lines 47-56)
2. `tests/cli/contracts/test_plan_contract.py` - May expect verbose format
3. All functional tests for add/init/tag/rework commands

---

## Formal Grammar (Added to Spec)

A formal EBNF-style grammar has been added to `spec.md` to clarify the format:

```ebnf
plan_file      = header_section blank_line entry_list
header_section = pragma+
pragma         = "%" key "=" value NEWLINE
blank_line     = NEWLINE
entry_list     = (change_entry | tag_entry)*

change_entry   = change_name [dependencies] timestamp planner [note] NEWLINE
change_name    = identifier
dependencies   = "[" identifier_list "]"
identifier_list= identifier (SPACE identifier)*
timestamp      = ISO8601_WITH_TZ  ; e.g., "2025-10-06T19:38:09Z"
planner        = name_email | email
name_email     = name SPACE "<" email ">"
note           = "#" text_to_eol

tag_entry      = "@" tag_name timestamp planner [note] NEWLINE
tag_name       = identifier

identifier     = [a-zA-Z0-9_:-]+
email          = [^ \t]+@[^ \t]+
name           = [^<]+  ; any characters except '<'
text_to_eol    = [^\n]+
```

---

## Implementation Plan (Task T055a)

### 1. Update Formatter (2-3 hours)
**File**: `sqlitch/plan/formatter.py`

#### Changes to `_format_change()`:
```python
def _format_change(change: Change, base_path: Path) -> str:
    """Format a change entry in compact Sqitch format.
    
    Format: <name> [dependencies] <timestamp> <planner> # <note>
    
    Note: Script paths are NOT included in compact format (Sqitch infers them).
          Verify path, change_id, and tags are also omitted from compact format.
    """
    parts = [change.name]
    
    # Add dependencies in square brackets if present
    if change.dependencies:
        parts.append(f"[{' '.join(change.dependencies)}]")
    
    # Add timestamp in ISO 8601 format with Z suffix
    parts.append(_format_timestamp(change.planned_at))
    
    # Add planner (name <email> or just email)
    parts.append(change.planner)
    
    # Add note as comment if present
    if change.notes:
        parts.append(f"# {change.notes}")
    
    return " ".join(parts)
```

#### Changes to `_format_tag()`:
```python
def _format_tag(tag: Tag) -> str:
    """Format a tag entry in compact Sqitch format.
    
    Format: @<name> <timestamp> <planner> # <note>
    
    Note: Tag implicitly references the immediately preceding change,
          so change_ref is NOT included in compact format.
    """
    parts = [f"@{tag.name}"]
    
    # Add timestamp
    parts.append(_format_timestamp(tag.tagged_at))
    
    # Add planner
    parts.append(tag.planner)
    
    # Add note if present
    if tag.note:
        parts.append(f"# {tag.note}")
    
    return " ".join(parts)
```

### 2. Update Tests (2-3 hours)

#### Update `tests/plan/test_formatter.py`:
```python
def test_format_plan_generates_compact_sqitch_format(tmp_path: Path) -> None:
    """Verify formatter outputs compact Sqitch-compatible format."""
    plan_path = tmp_path / "plan"
    change_core = Change(
        name="core:init",
        script_paths={"deploy": "deploy/core.sql", "revert": "revert/core.sql"},
        planner="alice@example.com",
        planned_at=_dt("2025-10-03T12:30:00+00:00"),
        change_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
    )
    change_widgets = Change(
        name="widgets:add",
        script_paths={
            "deploy": "deploy/widgets.sql",
            "revert": "revert/widgets.sql",
            "verify": "verify/widgets.sql",
        },
        planner="Alice Cooper <alice@example.com>",
        planned_at=_dt("2025-10-03T12:34:56+00:00"),
        notes="Add widgets table.",
        dependencies=("core:init",),
        tags=("v1.0",),
        change_id=UUID("223e4567-e89b-12d3-a456-426614174000"),
    )
    tag_v1 = Tag(
        name="v1.0",
        change_ref="widgets:add",
        planner="Alice Cooper <alice@example.com>",
        tagged_at=_dt("2025-10-03T12:35:30+00:00"),
        note="First release",
    )

    plan_text = formatter.format_plan(
        project_name="widgets",
        default_engine="pg",
        entries=[change_core, change_widgets, tag_v1],
        base_path=plan_path.parent,
    )

    # Expected compact format (note: no script paths, no change_id, no tags field)
    expected = (
        "%syntax-version=1.0.0\n"
        "%project=widgets\n"
        "%default_engine=pg\n"
        "\n"
        "core:init 2025-10-03T12:30:00Z alice@example.com\n"
        "widgets:add [core:init] 2025-10-03T12:34:56Z Alice Cooper <alice@example.com> # Add widgets table.\n"
        "@v1.0 2025-10-03T12:35:30Z Alice Cooper <alice@example.com> # First release\n"
    )

    assert plan_text == expected
```

#### Add Regression Test (compare with Sqitch):
```python
def test_formatter_output_matches_sqitch_tutorial_example(tmp_path: Path) -> None:
    """Verify output matches exact format from Sqitch tutorial."""
    # This is the exact example from sqitchtutorial-sqlite.pod
    change_users = Change(
        name="users",
        script_paths={
            "deploy": "deploy/users.sql",
            "revert": "revert/users.sql", 
            "verify": "verify/users.sql"
        },
        planner="Test User <test@example.com>",
        planned_at=_dt("2025-10-06T19:38:09+00:00"),
        notes="Creates table to track our users.",
    )
    
    plan_text = formatter.format_plan(
        project_name="flipr",
        default_engine="sqlite",
        entries=[change_users],
        base_path=tmp_path,
        uri="https://github.com/sqitchers/sqitch-sqlite-intro/",
    )
    
    expected = (
        "%syntax-version=1.0.0\n"
        "%project=flipr\n"
        "%default_engine=sqlite\n"
        "%uri=https://github.com/sqitchers/sqitch-sqlite-intro/\n"
        "\n"
        "users 2025-10-06T19:38:09Z Test User <test@example.com> # Creates table to track our users.\n"
    )
    
    assert plan_text == expected
```

### 3. Update Contract Tests (1 hour)
**File**: `tests/cli/contracts/test_plan_contract.py`

Review and update any tests that expect verbose format.

### 4. Verify Round-Trip Compatibility (1 hour)

Add test to verify parser can read formatter output:
```python
def test_format_parse_roundtrip_compact_format(tmp_path: Path) -> None:
    """Verify formatter output can be parsed back correctly."""
    original_change = Change(
        name="users",
        script_paths={"deploy": "deploy/users.sql", "revert": "revert/users.sql"},
        planner="Test User <test@example.com>",
        planned_at=_dt("2025-10-06T19:38:09+00:00"),
        notes="Add users table",
        dependencies=(),
        tags=(),
    )
    
    # Format to compact
    plan_text = formatter.format_plan(
        project_name="test",
        default_engine="sqlite",
        entries=[original_change],
        base_path=tmp_path,
    )
    
    # Parse back
    plan_file = tmp_path / "sqitch.plan"
    plan_file.write_text(plan_text, encoding="utf-8")
    parsed_plan = parser.parse_plan(plan_file)
    
    # Verify key fields match (script paths inferred, no change_id)
    assert len(parsed_plan.entries) == 1
    parsed_change = parsed_plan.entries[0]
    assert isinstance(parsed_change, Change)
    assert parsed_change.name == original_change.name
    assert parsed_change.planner == original_change.planner
    assert parsed_change.planned_at == original_change.planned_at
    assert parsed_change.notes == original_change.notes
```

---

## Key Design Decisions

### Q: What about script paths, change_id, tags fields?
**A**: These are **NOT included** in compact format. Sqitch infers:
- Script paths from change name (uses slugified name in deploy/, revert/, verify/ dirs)
- Change ID is computed, not stored in plan file
- Tags applied to changes don't appear in change line (only as separate @tag entries)

### Q: Should we support both formats for writing?
**A**: **NO**. Per FR-019a:
- Formatter outputs **ONLY compact format** (Sqitch-compatible)
- Parser supports **BOTH formats** (compact for Sqitch, verbose for legacy)

### Q: What about the %default_engine header?
**A**: This is a **SQLitch extension** that's fine to include. Sqitch doesn't have this header but will ignore it (treats unknown % pragmas as comments).

### Q: How do dependencies work in compact format?
**A**: Square brackets with space-separated list: `[dep1 dep2 dep3]`

### Q: How do notes work in compact format?
**A**: Everything after `#` until end of line is the note. The `#` is a comment delimiter, not metadata syntax.

---

## Testing Strategy

1. **Unit Tests** - Update existing formatter tests to expect compact format
2. **Integration Tests** - Verify `sqlitch add` writes correct format
3. **Regression Tests** - Compare against Sqitch tutorial examples byte-for-byte
4. **Round-Trip Tests** - Verify formatted output can be parsed back
5. **Interoperability Tests** - Verify Sqitch can read SQLitch-generated plans (manual)

---

## Success Criteria

- [ ] All formatter unit tests updated and passing
- [ ] All integration tests for add/init/tag/rework passing
- [ ] Plan files match Sqitch format byte-for-byte (excluding %default_engine)
- [ ] Parser still supports both compact and verbose formats
- [ ] Tutorial workflow generates Sqitch-compatible plan files
- [ ] Coverage ≥90% maintained

---

## Timeline Estimate

- **Total**: ~8-10 hours
- **Priority**: P0 (BLOCKING) - Must complete before checkpoint 2 (T056 integration tests)

---

## Related Files

### Must Change
- `sqlitch/plan/formatter.py` - Rewrite `_format_change()` and `_format_tag()`
- `tests/plan/test_formatter.py` - Update all tests to expect compact format

### May Need Changes
- `tests/cli/contracts/test_plan_contract.py` - Review contract tests
- `tests/cli/commands/test_add_functional.py` - Verify add tests still pass

### Should NOT Change
- `sqlitch/plan/parser.py` - Parser already correct (supports both formats)
- `sqlitch/plan/model.py` - Domain models unchanged

---

## Additional Notes

This bug was discovered during the Feature 004 tutorial implementation when comparing SQLitch output to Sqitch output. The parser was correctly implemented to support both formats, but the formatter only supported the verbose format, violating the interoperability requirement.

The fix should be straightforward since:
1. The compact format is simpler (fewer tokens)
2. The parser already demonstrates how to parse it
3. The specification now includes formal grammar
4. Test updates are mechanical (change expected strings)

**IMPORTANT**: The script paths are **NOT** stored in compact format. Sqitch infers them from the change name. This means when parsing compact format, the parser must reconstruct the paths (which it already does in `_parse_compact_change()`).
