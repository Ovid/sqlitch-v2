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

### Incorrect Rework Implementation

SQLitch's `rework` command exists but has **incorrect behavior**:

**What SQLitch does (WRONG):**
```
# Before: userflips [users flips] 2025... # Creates the userflips view.
# After:  userflips [users flips] 2025... # Adds userflips.twitter.
```
It modifies the existing plan entry in place (changes the note).

**What Sqitch does (CORRECT):**
```
# Original stays: userflips [users flips] 2025... # Creates the userflips view.
# New entry added: userflips [userflips@v1.0.0-dev2] 2025... # Adds userflips.twitter.
```
It adds a NEW entry with a dependency on the previous version via tag.

### Parser Rejection (Secondary Issue)

Once the rework command is fixed, the plan parser will reject the correct format:

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
- ✅ Step 39: `sqitch rework userflips` - executes but produces wrong plan format
- ⚠️ Step 40: `deploy` reworked change - SQLitch says "nothing to deploy" (incorrect)
- ❌ Step 41: `verify` reworked schema - databases happen to match but for wrong reasons
- ❌ Step 42: `revert --to @HEAD^` - will revert wrong change (no duplicate entry exists)
- ❌ Steps 43-46: final verification and status checks

**Blocked Tasks:**
- T060b: side-by-side UAT execution (currently at step 40 with behavioral differences)
- T060c-T060f: forward/backward compatibility validation
- T060g-T060h: UAT review and PR evidence

**Actual Failure Sequence:**
1. Step 39: `rework` command executes but modifies plan incorrectly
2. Step 40: `deploy` sees no changes (because there's no new entry in plan)
3. Step 42: `revert --to @HEAD^` reverts wrong change (plan structure is wrong)
4. Even if we fix `rework` command, parser will then reject duplicate entries

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
**Goal:** Allow duplicate change names in plans

1. Add rework fields to Change model
2. **Remove duplicate name validation from Plan.__post_init__**
3. Implement dependency parsing for rework syntax `[change@tag]`
4. Implement `get_latest_version()` and `get_all_versions()` on Plan
5. Add tests for parsing rework syntax

**Files:**
- `sqlitch/plan/model.py`
- `sqlitch/plan/parser.py`
- `tests/plan/test_parser_rework.py`
- `tests/plan/test_model_rework.py`

### Phase 2: Rework Command (Fix Incorrect Behavior)
**Goal:** Make `rework` command add new entry instead of modifying existing

1. Fix `sqlitch/cli/commands/rework.py` to append new entry to plan
2. Use tag dependency syntax: `change_name [change_name@last_tag]`
3. Create new script files with `@tag` suffix (already working)
4. Update tests for correct plan modification

**Files:**
- `sqlitch/cli/commands/rework.py`
- `tests/cli/commands/test_rework.py`

### Phase 3: Deploy/Revert Logic (Handle Reworked Changes)
**Goal:** Deploy and revert commands recognize reworked changes

1. Update deploy command to detect reworked changes
2. When deploying rework: revert old version, then deploy new version
3. Update revert command to navigate through all change versions
4. Update symbolic reference resolution for reworked changes
5. Add integration tests

**Files:**
- `sqlitch/cli/commands/deploy.py`
- `sqlitch/cli/commands/revert.py`
- `sqlitch/plan/symbolic.py`
- `tests/integration/test_rework_flow.py`

### Phase 4: Status/Display Commands (Show Rework Info)
**Goal:** Other commands display rework information correctly

1. Update status/log/plan commands to show rework relationships
2. Display tag annotations (e.g., `userflips @v1.0.0-dev2`)
3. Add tests for display formatting

**Files:**
- `sqlitch/cli/commands/status.py`
- `sqlitch/cli/commands/log.py`
- `sqlitch/cli/commands/plan.py`

### Phase 5: Validation (UAT)
**Goal:** Verify behavior matches Sqitch

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
