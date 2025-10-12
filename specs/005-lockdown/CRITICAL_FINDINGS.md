# Critical Findings: Lockdown Implementation

**Date**: 2025-10-11
**Status**: 🚨 BLOCKING ISSUE DISCOVERED
**Impact**: Cannot proceed with release until resolved

## Executive Summary

During execution of forward compatibility UAT testing (Task T060d), a **critical incompatibility** was discovered between Sqitch and SQLitch: they calculate DIFFERENT change IDs from identical plan entries. This violates the core constitutional requirement of Sqitch behavioral parity and makes the tools unable to interoperate.

## Issue Details

### The Problem

SQLitch and Sqitch use Git-style SHA1 hashes to uniquely identify changes. These IDs are calculated from the change metadata (name, timestamp, planner, dependencies, etc.). However, the two tools produce DIFFERENT IDs from the same input.

### Evidence

**Plan Entry:**
```
users 2025-10-11T13:08:16Z Test User <test@example.com> # Creates table to track our users.
```

**Calculated IDs:**
- **Sqitch**: `2ee1f8232096ca3ba2481f2157847a2a102e64d2`
- **SQLitch**: `ad8b16b7f335103ee01739bfa557b9ff702b2c63`

**Additional Example (flips change):**
```
flips [users] 2025-10-11T13:08:17Z Test User <test@example.com> # Adds table for storing flips.
```

**Calculated IDs:**
- **Sqitch**: `0ecbca89fb244fadb5f09e9b7f2b1eaf07e3d331`
- **SQLitch**: `4955468ffea7dd16dd3f468a6c0ed2e9c18ecd4c`

### How It Was Discovered

1. Forward compatibility test alternates between sqlitch and sqitch commands
2. Step 1-5: SQLitch initialized project and added "users" change
3. Step 6: Sqitch deployed "users" - calculated ID `2ee1f8...` and stored in registry
4. Step 10: Sqitch reverted "users" - deleted the change from registry
5. Step 17: SQLitch re-deployed "users" - calculated ID `ad8b16...` and stored in registry  
6. Step 20: Sqitch tried to verify - failed because:
   - Sqitch read plan file and calculated ID `2ee1f8...`
   - Queried database for that ID
   - Found entry with DIFFERENT ID `ad8b16...`
   - Reported: "Cannot find this change in sqitch.plan"

### Impact

**Immediate Impact:**
- Forward compatibility test FAILS at step 20 (sqitch verify)
- Backward compatibility test will also fail (not yet executed)
- Cannot claim Sqitch parity
- Cannot release v1.0

**Operational Impact:**
- Users cannot mix sqitch and sqlitch commands on same project
- Cannot migrate from sqitch to sqlitch (or vice versa) mid-project
- Databases deployed by one tool cannot be managed by the other
- Breaks the fundamental promise of compatibility

## Root Cause Analysis

### Current Implementation

SQLitch's change ID calculation is in `sqlitch/utils/identity.py::generate_change_id()`:

```python
def generate_change_id(
    project: str,
    change: str,
    timestamp: datetime,
    planner_name: str,
    planner_email: str,
    note: str = "",
    requires: tuple[str, ...] = (),
    conflicts: tuple[str, ...] = (),
) -> str:
    # Format timestamp
    timestamp_str = isoformat_utc(timestamp, drop_microseconds=True, use_z_suffix=True)
    
    # Build info string
    info_parts = [
        f"project {project}",
        f"change {change}",
        f"planner {planner_name} <{planner_email}>",
        f"date {timestamp_str}",
    ]
    
    if requires:
        info_parts.append("requires")
        for req in requires:
            info_parts.append(f"  + {req}")
    
    if conflicts:
        info_parts.append("conflicts")
        for conf in conflicts:
            info_parts.append(f"  - {conf}")
    
    if note:
        info_parts.append("")
        info_parts.append(note)
    
    info = "\n".join(info_parts)
    
    # Use Git's object format: 'change <length>\0<content>'
    info_bytes = info.encode("utf-8")
    git_object = f"change {len(info_bytes)}\x00".encode("utf-8") + info_bytes
    
    return hashlib.sha1(git_object).hexdigest()
```

### Verification Test

Manual test confirms SQLitch's calculation is internally consistent:

```python
>>> from sqlitch.utils.identity import generate_change_id
>>> from datetime import datetime, timezone
>>> 
>>> generate_change_id(
...     "flipr", "users", 
...     datetime(2025, 10, 11, 13, 8, 16, tzinfo=timezone.utc),
...     "Test User", "test@example.com",
...     "Creates table to track our users."
... )
'ad8b16b7f335103ee01739bfa557b9ff702b2c63'
```

This matches what's stored in the database, so SQLitch is consistent with itself. The problem is that Sqitch calculates DIFFERENTLY from the same plan entry.

### Hypotheses

Possible reasons for the mismatch:

1. **Field order**: Sqitch might order the info fields differently
2. **Whitespace**: Different line endings, indentation, or spacing
3. **Encoding**: Different UTF-8 normalization or byte encoding
4. **Git object format**: Different header format or length calculation
5. **Missing fields**: Sqitch might include additional metadata not in our implementation
6. **Field formatting**: Different formatting for timestamps, email brackets, etc.

## Required Investigation

### Step 1: Reverse Engineer Sqitch's Format

Need to determine EXACTLY what content Sqitch hashes. Approaches:

1. **Source code review**: Read `sqitch/lib/App/Sqitch/Plan/Change.pm` to find the `id()` method
2. **Dynamic analysis**: Patch Sqitch to log pre-hash content
3. **Format inference**: Use `sqitch plan --format raw` and work backwards

### Step 2: Compare Byte-for-Byte

Create test cases with known Sqitch IDs and compare:
- What SQLitch produces
- What Sqitch produces  
- Identify exact differences

### Step 3: Update SQLitch

Modify `generate_change_id()` to match Sqitch's format exactly.

### Step 4: Validate

1. Unit tests with known Sqitch IDs
2. Re-run all 46 UAT steps
3. Run forward compatibility test
4. Run backward compatibility test

## Temporary Workaround

None available. This is a fundamental incompatibility that blocks all interoperability.

## Action Items

**Priority**: P1 - CRITICAL - BLOCKING

**Owner**: Implementation team

**Tasks**:
- [ ] T068: Fix change ID calculation (see tasks.md for full details)
- [ ] Add regression tests with known Sqitch IDs
- [ ] Re-run forward/backward compatibility tests
- [ ] Update implementation report

**Timeline**: Must be resolved before proceeding with any other lockdown tasks.

## References

- **Task**: T060d, T068
- **Constitution**: Section on Sqitch Behavioral Parity
- **Files Affected**:
  - `sqlitch/utils/identity.py`
  - `sqlitch/cli/commands/deploy.py`
  - `uat/scripts/forward-compat.py`
- **Test Artifacts**:
  - `uat/forward_compat_results/` (preserved for investigation)
  - `uat/forward_compat_results/sqitch.plan`
  - `uat/forward_compat_results/sqitch.db`

## Session Continuity

If implementation is paused:
1. Working directory preserved at: `uat/forward_compat_results/`
2. Registry database: `uat/forward_compat_results/sqitch.db`
3. Events log shows the divergence
4. Resume by investigating T068

---

*This report documents a constitutional gate failure that must be resolved before 1.0 release.*
