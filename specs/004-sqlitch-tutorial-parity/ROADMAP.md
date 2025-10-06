# Feature 004: Implementation Roadmap

**Status**: ✅ Specification Complete - Ready for Planning  
**Branch**: `004-sqlitch-tutorial-parity`  
**Date**: October 6, 2025

---

## ✅ Completed: Specification Phase

### Documents Ready
1. **spec.md** - Feature specification (COMPLETE)
   - All clarifications resolved
   - Requirements defined
   - Scope bounded

2. **quickstart.md** - Validation scenarios (COMPLETE)
   - 8 concrete test scenarios
   - Full tutorial automation script

3. **README.md** - Getting started guide (COMPLETE)
   - Overview and context

---

## 🎯 Confirmed Scope

### Commands to Implement (In Tutorial Order)

1. **`sqitch init`** → Initialize project (sqitch.conf, sqitch.plan, directories)
2. **`sqitch config`** → Get/set config (user.name, user.email, engine.sqlite.client)
3. **`sqitch add`** → Create changes (deploy/revert/verify scripts, update plan)
4. **`sqitch deploy`** → Deploy changes (execute scripts, update registry)
5. **`sqitch verify`** → Verify changes (execute verify scripts)
6. **`sqitch status`** → Show status (query registry, display state)
7. **`sqitch revert`** → Revert changes (execute revert scripts, update registry)
8. **`sqitch log`** → Show history (display events from registry)
9. **`sqitch tag`** → Tag releases (add tags to plan)
10. **`sqitch rework`** → Rework changes (create @tag versioned scripts)

### Implementation Principles

- ✅ **Tutorial-first**: Each command must work as shown in tutorial
- ✅ **Minimal scope**: Just enough to complete tutorial workflows
- ✅ **Manual Git**: User handles git commands separately
- ✅ **Sqitch alignment**: Behavior matches Perl Sqitch
- ✅ **URI-based targets**: db:sqlite:path/to/file.db
- ✅ **Registry operations**: Deploy, revert, verify events

---

## 📋 Next Steps: Planning Phase

### Step 1: Research Document
**File**: `specs/004-sqlitch-tutorial-parity/research.md`

**Purpose**: Technical investigation and decisions

**Content**:
- Existing codebase analysis (what's already implemented?)
- SQLite registry schema review (from Feature 002)
- Click command implementation patterns
- File I/O strategies (script generation, plan parsing)
- Transaction management approach
- Error handling patterns
- Testing strategy details

**Questions to Answer**:
- What parts of Feature 002 (SQLite engine) are already done?
- Which registry tables/operations exist?
- How do we handle plan file mutations?
- What's the deploy script execution model?
- How do we track dependencies?

---

### Step 2: Data Model Document
**File**: `specs/004-sqlitch-tutorial-parity/data-model.md`

**Purpose**: Define data structures and relationships

**Content**:
- **Project**: Configuration, plan, scripts
- **Change**: Name, dependencies, scripts, state
- **Tag**: Name, change reference, note
- **Registry**: Tables, relationships, queries
- **Config**: Scopes (system/user/local), keys, values
- **Target**: URI, engine, database path
- **Event**: Type (deploy/revert/verify), change, timestamp

**Models Needed**:
```python
@dataclass
class Project:
    name: str
    uri: str
    engine: str
    plan_file: Path
    # ...

@dataclass
class Change:
    name: str
    note: str | None
    requires: list[str]
    conflicts: list[str]
    # ...

# ... more models
```

---

### Step 3: Plan Document
**File**: `specs/004-sqlitch-tutorial-parity/plan.md`

**Purpose**: Implementation strategy and phases

**Content**:
- Technical context (Python 3.11, Click, SQLite, pytest)
- Constitutional compliance check
- Project structure
- Phase breakdown:
  - Phase 0: Research ✅
  - Phase 1: Data models and contracts
  - Phase 2: Core commands (init, config, add)
  - Phase 3: Deploy workflow (deploy, verify, status)
  - Phase 4: Change management (revert, log)
  - Phase 5: Advanced features (tag, rework)
  - Phase 6: Integration testing and polish

---

### Step 4: Tasks Document
**File**: `specs/004-sqlitch-tutorial-parity/tasks.md`

**Purpose**: Detailed task breakdown with test-first approach

**Content**:
- Task numbering (T001-T0XX)
- Parallel markers [P] where applicable
- Test-first workflow (contract tests → implementation)
- Dependencies and blocking relationships
- Estimated effort
- Success criteria

**Example Tasks**:
```
Phase 4.1: Foundation
- [x] T001 [P] Write contract tests for init command
- [ ] T002 [P] Implement init command
- [ ] T003 [P] Write contract tests for config command
- [ ] T004 Implement config get/set operations
...
```

---

## 🔄 Workflow Summary

```
┌─────────────────────────────────────────────────────┐
│ 1. RESEARCH (research.md)                           │
│    - Analyze existing code                          │
│    - Review registry schema                         │
│    - Plan technical approach                        │
└─────────────────────┬───────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 2. DATA MODEL (data-model.md)                       │
│    - Define dataclasses                             │
│    - Document relationships                         │
│    - Specify validation rules                       │
└─────────────────────┬───────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 3. PLAN (plan.md)                                   │
│    - Phase breakdown                                │
│    - Constitutional check                           │
│    - Implementation strategy                        │
└─────────────────────┬───────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 4. TASKS (tasks.md)                                 │
│    - Detailed task list                             │
│    - TDD workflow                                   │
│    - Dependencies mapped                            │
└─────────────────────┬───────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ 5. IMPLEMENTATION                                   │
│    - Write contract tests (RED)                     │
│    - Implement features (GREEN)                     │
│    - Refactor and polish (REFACTOR)                 │
└─────────────────────────────────────────────────────┘
```

---

## 🎯 Success Metrics

Feature 004 is complete when:

1. **All 8 tutorial scenarios pass** (quickstart.md)
2. **Tutorial automation script succeeds** end-to-end
3. **Database state matches expectations** at each step
4. **Plan and registry remain valid** throughout
5. **Output matches Sqitch** (within acceptable variations)
6. **Test coverage ≥90%** for all commands
7. **All CI checks pass**
8. **Documentation complete**

---

## 📊 Estimated Timeline

Based on Feature 003 (40 tasks, ~2 weeks):

- **Research**: 1-2 days
- **Data Model**: 1 day
- **Plan**: 1 day
- **Tasks**: 1 day
- **Implementation**:
  - Phase 1 (init, config): 2-3 days
  - Phase 2 (add): 2-3 days
  - Phase 3 (deploy, verify, status): 4-5 days
  - Phase 4 (revert, log): 2-3 days
  - Phase 5 (tag, rework): 2-3 days
- **Testing & Polish**: 2-3 days

**Total**: ~3-4 weeks

---

## 🚀 Ready to Proceed?

The specification is complete and ready for the planning phase. Next command:

```bash
# Generate research.md (analyze existing code, plan technical approach)
# This would be done by an agent or manually
```

Or if following the project's workflow, you can now:

1. **Create research.md** - Investigate existing registry, plan parsing, command patterns
2. **Create data-model.md** - Define all dataclasses and relationships
3. **Create plan.md** - Break down implementation into phases
4. **Create tasks.md** - Generate detailed task list with TDD workflow

Would you like me to start with the research phase?

