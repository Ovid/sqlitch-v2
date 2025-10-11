# Rework Support Analysis (2025-10-11)

## Executive Summary

**Status**: 🚨 BLOCKING - Critical feature gap prevents lockdown completion

**Discovery**: UAT execution at step 39 revealed that SQLitch does not support Sqitch's `rework` command, which allows duplicate change names in the plan file. This is a constitutional violation (behavioral parity gap) that blocks all remaining UAT validation tasks.

## Background

### What is Rework?

In Sqitch, "rework" allows you to modify a deployed change by creating a new version with the same name but different content. This is essential for:
- Fixing bugs in deployed changes
- Enhancing existing schema objects
- Maintaining semantic continuity (same change name = same database object)

### Tutorial Context

The SQLite tutorial (step 39) demonstrates rework:

```bash
# After tagging v1.0.0-dev2, modify the userflips view
sqitch rework userflips -n "Adds userflips.twitter"
```

This adds a new entry to sqitch.plan:
```
userflips [userflips@v1.0.0-dev2] 2025-10-11... # Adds userflips.twitter
```

The plan now contains two entries named "userflips":
1. Original: `userflips [users flips] ...` 
2. Reworked: `userflips [userflips@v1.0.0-dev2] ...`

## Current SQLitch Behavior

### Parser Rejection

When SQLitch tries to parse a plan with reworked changes:

```python
# sqlitch/plan/model.py, line 165
def __post_init__(self):
    seen_names: set[str] = set()
    for entry in self.changes:
        if entry.name in seen_names:
            raise ValueError(f"Plan contains duplicate change name: {entry.name}")
        seen_names.add(entry.name)
```

Result: `ValueError: Plan contains duplicate change name: userflips`

### Impact

**Blocked UAT Steps:**
- Step 39: `sqitch rework userflips` - creates reworked plan that sqlitch cannot parse
- Step 40: `deploy` reworked change
- Step 41: `verify` reworked schema
- Step 42: `revert --to @HEAD^` - should revert the reworked change only
- Steps 43-46: final verification and status checks

**Blocked Tasks:**
- T060b: side-by-side UAT execution (currently at step 38/46)
- T060c-T060f: forward/backward compatibility validation
- T060g-T060h: UAT review and PR evidence

## Sqitch Implementation Analysis

### Plan File Format

From `sqitch/lib/App/Sqitch/Plan.pm`:

```perl
# When parsing the plan, Sqitch allows duplicate change names
if (my $duped = $change_named{ $params{name} }) {
    # Get rework tags by change in reverse order to reworked change.
    my @rework_tags;
    for (my $i = $#changes; $changes[$i] ne $duped; $i--) {
        push @rework_tags => $changes[$i]->tags;
    }
    # Add list of rework tags to the reworked change.
    $duped->add_rework_tags(@rework_tags, $duped->tags);
}
$change_named{ $params{name} } = $prev_change;
```

Key insights:
1. Duplicate names are **explicitly allowed**
2. Rework relationship tracked via tags in the dependency
3. Each reworked version maintains its own identity (timestamp, planner, dependencies)
4. The latest version becomes the "HEAD" for that change name

### Rework Tag Syntax

Rework dependencies use special syntax:

```
change_name [change_name@tag_name]
```

Examples:
- `userflips [userflips@v1.0.0-dev2]` - rework depends on userflips as it existed at tag v1.0.0-dev2
- `users [users@beta]` - rework depends on users as it existed at tag beta

### Internal Representation

Sqitch uses `@HEAD` suffix internally to track the latest version:
- `userflips@HEAD` refers to the most recent version of userflips
- Plain `userflips` in references also means the latest version
- Symbolic references like `@HEAD^` navigate through all changes, including reworked versions

## Required Implementation

### 1. Plan Model Changes

**File**: `sqlitch/plan/model.py`

```python
@dataclass(frozen=True)
class Change:
    """Represents a single change in the plan."""
    
    name: str
    dependencies: tuple[str, ...]
    planner: str
    planned_at: datetime
    notes: str | None
    tags: tuple[str, ...]
    
    # NEW: Track rework relationships
    rework_of: str | None = None  # e.g., "userflips@v1.0.0-dev2"
    is_rework: bool = False
    
    @classmethod
    def parse_dependencies(cls, deps: tuple[str, ...]) -> tuple[tuple[str, ...], str | None]:
        """Parse dependencies, extracting rework reference if present.
        
        Examples:
            ("users", "flips") -> (("users", "flips"), None)
            ("userflips@v1.0.0-dev2",) -> ((), "userflips@v1.0.0-dev2")
        """
        rework_ref = None
        normal_deps = []
        
        for dep in deps:
            # Check if this is a self-reference (rework indicator)
            # Pattern: <change_name>@<tag_name>
            if "@" in dep:
                base_name, tag_name = dep.split("@", 1)
                # This is a rework reference
                rework_ref = dep
            else:
                normal_deps.append(dep)
        
        return tuple(normal_deps), rework_ref


@dataclass(frozen=True)
class Plan:
    """Represents a parsed Sqitch plan file."""
    
    # Remove duplicate name check from __post_init__
    def __post_init__(self):
        # Validate references only, allow duplicate change names
        seen_tags: set[str] = set()
        for tag in self.tags:
            if tag.name in seen_tags:
                raise ValueError(f"Plan contains duplicate tag name: {tag.name}")
            seen_tags.add(tag.name)
    
    def get_latest_version(self, change_name: str) -> Change | None:
        """Get the most recent version of a change (reworked or original)."""
        # Iterate in reverse to find the latest
        for change in reversed(self.changes):
            if change.name == change_name:
                return change
        return None
    
    def get_all_versions(self, change_name: str) -> list[Change]:
        """Get all versions of a change, in order."""
        return [c for c in self.changes if c.name == change_name]
```

### 2. Parser Changes

**File**: `sqlitch/plan/parser.py`

Update `_parse_change_line` to detect and mark rework:

```python
def _parse_change_line(line: str, line_no: int) -> Change:
    """Parse a change line into a Change object."""
    # ... existing parsing logic ...
    
    # Check if this is a rework by looking for self-reference in dependencies
    normal_deps, rework_ref = Change.parse_dependencies(dependencies)
    
    return Change(
        name=name,
        dependencies=normal_deps,
        planner=planner,
        planned_at=planned_at,
        notes=notes,
        tags=(),
        rework_of=rework_ref,
        is_rework=rework_ref is not None,
    )
```

### 3. Symbolic Reference Resolution

**File**: `sqlitch/plan/symbolic.py`

Update resolution to handle reworked changes:

```python
def resolve_symbolic_reference(ref: str, changes: list[Change]) -> str:
    """Resolve a symbolic reference to the actual change name (latest version).
    
    For plain change names, returns the name itself (caller should use get_latest_version).
    For symbolic refs like @HEAD^, navigates through ALL changes (including reworks).
    """
    # ... existing logic ...
    
    # When resolving change names, consider that there might be multiple versions
    # Return the position in the full change list (which includes reworks)
```

### 4. Deploy/Revert Logic

**Files**: 
- `sqlitch/cli/commands/deploy.py`
- `sqlitch/cli/commands/revert.py`

Update to handle rework semantics:

```python
# When deploying a reworked change:
# 1. Check if the original version is deployed
# 2. Run the revert script for the old version
# 3. Run the deploy script for the new version
# 4. Update the registry to reflect the rework

# When reverting with @HEAD^:
# 1. If HEAD is a reworked change, revert to the previous version (not previous change)
# 2. Navigate the full change list including all rework versions
```

### 5. Test Coverage

**New test files:**
- `tests/plan/test_parser_rework.py` - Parse rework syntax
- `tests/plan/test_model_rework.py` - Change model with rework fields
- `tests/cli/commands/test_deploy_rework.py` - Deploy reworked changes
- `tests/cli/commands/test_revert_rework.py` - Revert reworked changes
- `tests/integration/test_rework_flow.py` - Full rework workflow

**Test scenarios:**
1. Parse plan with single rework
2. Parse plan with multiple reworks of same change
3. Parse plan with reworks of different changes
4. Deploy reworked change (should revert then deploy)
5. Revert reworked change with @HEAD^
6. Symbolic resolution with reworked changes
7. Status display showing reworked changes

## Implementation Strategy

### Phase 1: Model & Parser (Foundation)
1. Add rework fields to Change model
2. Update Plan model to allow duplicate names
3. Implement dependency parsing for rework syntax
4. Add tests for parsing rework syntax

### Phase 2: Resolution (Navigation)
1. Update symbolic reference resolution
2. Implement get_latest_version / get_all_versions
3. Add tests for resolving references with reworks

### Phase 3: Commands (Behavior)
1. Update deploy command for rework deployment
2. Update revert command for rework reversion
3. Update status/log/plan commands to display rework info
4. Add integration tests

### Phase 4: Validation (UAT)
1. Re-run side-by-side UAT from step 39
2. Verify steps 39-46 pass
3. Document any cosmetic differences
4. Complete forward/backward compat testing

## Acceptance Criteria

✅ Plan parser accepts duplicate change names
✅ Rework syntax `change [change@tag]` parsed correctly
✅ `get_latest_version("userflips")` returns reworked version
✅ `deploy` of reworked change reverts old version first
✅ `revert --to @HEAD^` reverts only the reworked version
✅ UAT steps 39-46 pass
✅ All rework tests pass with ≥90% coverage

## Timeline Estimate

- Phase 1: 2-3 hours
- Phase 2: 1-2 hours  
- Phase 3: 3-4 hours
- Phase 4: 1-2 hours
- **Total**: 7-11 hours

## Risk Assessment

**Complexity**: Medium-High
- Touches core plan model (frozen dataclass, immutability constraints)
- Affects multiple commands (deploy, revert, status, log, plan)
- Requires careful testing to avoid breaking existing functionality

**Breaking Changes**: None
- All changes are additive (new fields with defaults)
- Plans without reworks continue to work unchanged

**Testing Burden**: High
- Need comprehensive tests for rework scenarios
- Must verify existing tests still pass
- UAT coverage increased (steps 39-46)

## Conclusion

Rework support is a **non-negotiable constitutional requirement** for Sqitch parity. Without it:
- ❌ Cannot complete UAT validation (7 steps blocked)
- ❌ Cannot claim feature parity with Sqitch
- ❌ Cannot release v1.0 with integrity

**Recommendation**: Implement T067 immediately before proceeding with any other lockdown tasks. This is the highest priority item for the 005-lockdown milestone.

---

**Task Reference**: T067
**Created**: 2025-10-11
**Author**: SQLitch Agent
**Status**: Blocked - Awaiting implementation
