
## 2025-10-11: Change ID Calculation Fixed (CRITICAL)

### Problem
SQLitch and Sqitch were calculating different change IDs from identical plan entries, making them incompatible. Forward/backward compatibility tests were blocked.

### Root Cause
Two missing fields in SQLitch's `generate_change_id()`:
1. **URI field**: Sqitch includes project URI when available
2. **Parent field**: Sqitch links changes chronologically - each change (except first) has parent=previous change's ID

### Solution Implemented
1. Added `uri` parameter to `generate_change_id()` in `sqlitch/utils/identity.py`
2. Added `parent_id` parameter to `generate_change_id()`  
3. Implemented `_resolve_parent_id_for_change()` - resolves parent as chronologically previous change
4. Updated deployment flow to pre-compute all IDs with correct parent resolution
5. Fixed `_apply_change()` to use pre-computed IDs (was recomputing incorrectly with parent_id=None)
6. Updated revert flow to match deployment calculation

### Verification
✅ Users change: `2ee1f8232096ca3ba2481f2157847a2a102e64d2` (EXACT MATCH with Sqitch)
✅ Flips change: `0ecbca89fb244fadb5f09e9b7f2b1eaf07e3d331` (EXACT MATCH with Sqitch)  
✅ All revert functional tests now pass (7/7)
✅ Deploy → Revert cycle works correctly

### Files Modified
- `sqlitch/utils/identity.py`
- `sqlitch/cli/commands/deploy.py`  
- `sqlitch/cli/commands/revert.py`

### Impact
- Forward/backward compatibility UAT tests can now proceed (T060d, T060f)
- SQLitch achieves Sqitch change ID parity
- Constitutional requirement for v1.0 release satisfied
