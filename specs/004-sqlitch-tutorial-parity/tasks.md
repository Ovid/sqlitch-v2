# Tasks: SQLite Tutorial Parity

**Input**: Design documents from `/specs/004-sqlitch-tutorial-parity/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

## Execution Flow (Tutorial-Driven Implementation)
```
1. ✅ Loaded plan.md - Python 3.11, Click, pytest, sqlite3
2. ✅ Loaded data-model.md - 10 new models + 4 helpers + Plan methods
3. ✅ Loaded research.md - Technical deci### Init Command Finalization
- [X] **T051** Write tests for init directory and file creation in `tests/cli/commands/test_init_functional.py`
  - Test creates sqitch.conf with correct engine setting
  - Test creates sqitch.plan with project pragmas (%syntax-version, %project, %uri)
  - Test creates deploy/, revert/, verify/ directories
  - Test verifies directory structure matches FR-001 requirements
  - Test validates file contents match Sqitch format
  
- [X] **T052** Write tests for init engine validation in `tests/cli/commands/test_init_functional.py`
  - Test validates engine exists in ENGINE_REGISTRY
  - Test fails with clear error if engine invalid
  - Test defaults to sqlite if not specified
  
- [ ] **T053** Complete init command in `sqlitch/cli/commands/init.py`g code analysis
4. ✅ Loaded quickstart.md - 8 validation scenarios
5. ✅ Loaded sqitchtutorial-sqlite.pod - Tutorial command sequence
6. Task ordering follows tutorial flow (sqitch/lib/sqitchtutorial-sqlite.pod):
   → CHECKPOINT 1: Init + Config (lines 66-108 in tutorial)
   → CHECKPOINT 2: Add (lines 149-165)
   → CHECKPOINT 3: Deploy (lines 200-220) - requires Foundation models
   → CHECKPOINT 4: Verify + Status (lines 238-282)
   → CHECKPOINT 5: Revert + Log (lines 284-327)
   → CHECKPOINT 6: Tag + Rework (later sections)
   → CHECKPOINT 7: Integration tests + Parity validation
7. UAT validation after each checkpoint before proceeding
8. TDD: Tests before implementation for all new code
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[UAT]**: Manual user acceptance testing checkpoint
- All paths are absolute from repository root

---

## Tutorial Implementation Order

**IMPORTANT**: Tasks are implemented following the tutorial command sequence from `sqitch/lib/sqitchtutorial-sqlite.pod`. After each checkpoint, perform manual UAT validation before proceeding.

### CHECKPOINT 1: Project Setup (Tutorial Lines 66-108)
**Commands**: `sqitch init`, `sqitch config`  
**Tasks**: T051-T053 (init), T025-T028 (config)  
**UAT**: Run `sqlitch init flipr --engine sqlite` and `sqlitch config --user user.name "Your Name"`  
**Expected**: Creates sqitch.conf, sqitch.plan, deploy/, revert/, verify/ directories; config sets user.name

### CHECKPOINT 2: Adding Changes (Tutorial Lines 149-165)
**Commands**: `sqitch add`  
**Tasks**: T054-T055 (add finalization)  
**UAT**: Run `sqlitch add users -n 'Creates table to track our users.'`  
**Expected**: Creates deploy/users.sql, revert/users.sql, verify/users.sql with proper headers

### CHECKPOINT 3: Deployment (Tutorial Lines 200-220)
**Commands**: `sqitch deploy`  
**Tasks**: T001-T024 (foundation models - MUST complete first), T033-T038 (deploy)  
**UAT**: Run `sqlitch deploy db:sqlite:flipr_test.db`  
**Expected**: Creates sqitch.db registry, deploys users table, outputs "+ users .. ok"

### CHECKPOINT 4: Verification & Status (Tutorial Lines 238-282)
**Commands**: `sqitch verify`, `sqitch status`  
**Tasks**: T039-T040 (verify), T029-T030 (status)  
**UAT**: Run `sqlitch verify db:sqlite:flipr_test.db` and `sqlitch status db:sqlite:flipr_test.db`  
**Expected**: Verify shows "* users .. ok", status shows deployed change with timestamp

### CHECKPOINT 5: Revert & Log (Tutorial Lines 284-327)
**Commands**: `sqitch revert`, `sqitch log`  
**Tasks**: T041-T044 (revert), T031-T032 (log)  
**UAT**: Run `sqlitch revert db:sqlite:flipr_test.db` and `sqlitch log db:sqlite:flipr_test.db`  
**Expected**: Revert shows "- users .. ok", log shows both deploy and revert events

### CHECKPOINT 6: Tags & Rework (Tutorial Later Sections)
**Commands**: `sqitch tag`, `sqitch rework`  
**Tasks**: T045-T047 (tag), T048-T050 (rework)  
**UAT**: Run `sqlitch tag v1.0.0-dev1 -n 'First release'` and `sqlitch rework users`  
**Expected**: Tag added to plan, rework creates @v1.0.0-dev1 suffixed scripts

### CHECKPOINT 7: Integration & Polish (Full Tutorial)
**Commands**: All commands together  
**Tasks**: T056-T063 (integration tests), T064-T072 (parity validation), T073-T077 (polish)  
**UAT**: Follow complete tutorial workflow end-to-end  
**Expected**: All tutorial scenarios pass, output matches Sqitch byte-for-byte

---

## Task Details (Organized by Technical Phase)

### Phase 3.1: Foundation Models & Helpers
- [X] **T001** [P] Write tests for DeployedChange model in `tests/registry/test_deployed_change.py`
  - ✅ Test from_registry_row() with valid data
  - ✅ Test from_registry_row() with NULL script_hash
  - ✅ Test timezone-aware datetime handling
  - ✅ Test frozen dataclass and slots
  
- [X] **T002** [P] Implement DeployedChange model in `sqlitch/registry/state.py`
  - ✅ Frozen dataclass with slots
  - ✅ from_registry_row() class method
  - ✅ All datetime fields timezone-aware
  - ✅ All 5 tests passing
  
- [X] **T003** [P] Write tests for DeploymentEvent model in `tests/registry/test_deployment_event.py` ✅
  - ✅ Test from_registry_row() with all event types (deploy, revert, fail)
  - ✅ Test parsing comma-separated lists (requires, conflicts, tags)
  - ✅ Test timezone handling
  
- [X] **T004** [P] Implement DeploymentEvent model in `sqlitch/registry/state.py` ✅
  - Frozen dataclass with slots ✅
  - from_registry_row() class method ✅
  - Parse comma-separated dependency lists ✅
  
**Tests**: 9 tests passing

- [X] **T005** [P] Write tests for DeploymentStatus model in `tests/registry/test_deployment_status.py` ✅
  - ✅ Test is_up_to_date property
  - ✅ Test deployment_count property
  - ✅ Test with empty deployed/pending lists
  - ✅ Test frozen dataclass and slots
  
- [X] **T006** [P] Implement DeploymentStatus model in `sqlitch/registry/state.py` ✅
  - ✅ Frozen dataclass with slots
  - ✅ is_up_to_date and deployment_count properties
  - ✅ Tuple fields (immutable sequences)
  
**Tests**: 8 tests passing

### Command Models (sqlitch/cli/commands/_models.py)
- [X] **T007** [P] Write tests for CommandResult model in `tests/cli/commands/test_models.py` ✅
  - ✅ Test ok() class method
  - ✅ Test error() class method
  - ✅ Test success/exit_code handling
  
- [X] **T008** [P] Implement CommandResult model in `sqlitch/cli/commands/_models.py` ✅
  - ✅ Frozen dataclass with slots
  - ✅ ok() and error() class methods
  - ✅ Optional data field with MappingProxyType
  
**Tests**: 10 tests passing

- [X] **T009** [P] Write tests for DeployOptions model in `tests/cli/commands/test_models.py` ✅
  - ✅ Test validation (to_change and to_tag mutually exclusive)
  - ✅ Test mode validation (all/change/tag only)
  - ✅ Test defaults
  
- [X] **T010** [P] Implement DeployOptions model in `sqlitch/cli/commands/_models.py` ✅
  - ✅ Frozen dataclass with slots
  - ✅ Validation in __post_init__
  - ✅ Default values for mode and verify
  
**Tests**: 6 tests passing (24 total for _models.py)

### Script Models (sqlitch/engine/scripts.py)
- [X] **T013** [P] Write tests for Script model in `tests/engine/test_scripts.py` ✅
  - ✅ Test load() class method with valid file
  - ✅ Test load() with missing file raises FileNotFoundError
  - ✅ Test frozen dataclass and slots
  
- [X] **T014** [P] Implement Script model in `sqlitch/engine/scripts.py` ✅
  - ✅ Frozen dataclass with slots
  - ✅ load() class method reads file content
  - ✅ path and content fields
  
- [X] **T015** [P] Write tests for ScriptResult model (combined with T013) ✅
  - ✅ Test ok() class method
  - ✅ Test error() class method
  - ✅ Test frozen dataclass and slots
  
- [X] **T016** [P] Implement ScriptResult model (combined with T014) ✅
  - ✅ Frozen dataclass with slots
  - ✅ ok() and error() class methods
  - ✅ success and error_message fields
  
**Tests**: 8 tests passing
- [ ] **T015** [P] Write tests for ScriptResult model in `tests/engine/test_scripts.py`
  - Test ok() class method
  - Test error() class method
  - Test execution_time handling
  
**Tests**: 8 tests passing

### Identity & Validation (sqlitch/utils/)
- [X] **T017** [P] Write tests for UserIdentity model in `tests/utils/test_identity.py` ✅
  - ✅ Test creates from name/email
  - ✅ Test frozen dataclass and slots
  
- [X] **T018** [P] Implement UserIdentity in `sqlitch/utils/identity.py` ✅
  - ✅ Frozen dataclass with slots
  - ✅ name and email fields
  
- [X] **T019** [P] Write tests for generate_change_id in `tests/utils/test_identity.py` ✅
  - ✅ Test SHA1 hash generation
  - ✅ Test deterministic (same inputs → same output)
  - ✅ Test format matches Sqitch
  
- [X] **T020** [P] Implement generate_change_id in `sqlitch/utils/identity.py` ✅
  - ✅ SHA1(project:change:timestamp ISO format)
  - ✅ Return hex digest string
  
**Tests**: 7 tests passing

### Plan Helpers (sqlitch/plan/model.py)
- [X] **T021** Write tests for Plan helper methods (already exist) ✅
  - ✅ `changes` property returns only Change entries
  - ✅ `tags` property returns only Tag entries  
  - ✅ `get_change(name)` finds change by name
  - ✅ `has_change(name)` checks if change exists
  - ✅ Existing tests in `tests/plan/test_model.py` cover these
  
- [X] **T022** Implement Plan helper methods (already exist) ✅
  - ✅ `changes` property → tuple[Change, ...]
  - ✅ `tags` property → tuple[Tag, ...]
  - ✅ `get_change(name)` → Change (raises KeyError if not found)
  - ✅ `has_change(name)` → bool
  - ✅ Implemented in `sqlitch/plan/model.py` lines 180-197

### Validation Functions (sqlitch/plan/validation.py)
- [X] **T023** [P] Write tests for validation functions in `tests/plan/test_validation.py` ✅
  - ✅ Test validate_change_name() accepts valid names
  - ✅ Test validate_change_name() rejects whitespace, invalid chars
  - ✅ Test validate_tag_name() accepts valid tags
  - ✅ Test validate_tag_name() rejects @ prefix, whitespace
  
- [X] **T024** [P] Implement validation functions in `sqlitch/plan/validation.py` ✅
  - ✅ validate_change_name(name) raises ValueError for invalid
  - ✅ validate_tag_name(name) raises ValueError for invalid
  
**Tests**: 9 tests passing

---

## Phase 3.2: Command Implementations
**Purpose**: Implement tutorial-critical commands  
**Estimated Time**: 4-5 weeks  
**Order**: Config → Status/Log → Deploy/Verify/Revert → Tag/Rework → Init/Add (finalize)

### Config Command (Simple - 1 day)
- [X] **T025** Write tests for config get operation in `tests/cli/commands/test_config_functional.py`
  - ✅ Test get from project config
  - ✅ Test get from user config with --user flag
  - ✅ Test get with --global (alias for --user, no --system in SQLitch)
  - ✅ Test precedence (project > user)
  - ✅ Test missing key returns exit code 1
  
- [X] **T026** Write tests for config set operation in `tests/cli/commands/test_config_functional.py`
  - ✅ Test set in project config (default)
  - ✅ Test set in user config with --user flag
  - ✅ Test set with --global (alias for --user)
  - ✅ Test creates config file if missing
  - ✅ Test updates existing value
  
- [X] **T027** Write tests for config list operation in `tests/cli/commands/test_config_functional.py`
  - ✅ Test list shows all config values
  - ✅ Test list with --user shows user config only
  - ✅ Test list with --global shows user config
  - ✅ Additional: output format tests (quiet mode, value-only)
  - ✅ Additional: error handling tests (conflicting args, invalid keys)
  
- [X] **T028** Implement config get/set/list in `sqlitch/cli/commands/config.py`
  - ✅ get: Read from ConfigProfile (already implemented)
  - ✅ set: Write to appropriate config file (already implemented)
  - ✅ list: Display all config values (already implemented)
  - ✅ --global is alias for --user (Sqitch convention)
  - ✅ User config default: ~/.config/sqlitch/sqitch.conf
  - ✅ Fallback to ~/.sqitch/sqitch.conf if it exists
  - ✅ All 18 functional tests passing

### Status Command (Medium - 2 days)
- [ ] **T029** Write tests for status query logic in `tests/cli/commands/test_status_functional.py`
  - Test with no registry (empty database)
  - Test with deployed changes
  - Test with pending changes
  - Test output format matches Sqitch
  - Test exit code 0 when up-to-date
  
- [ ] **T030** Implement status command in `sqlitch/cli/commands/status.py` (~300 lines)
  - Query registry changes table via engine.get_deployed_changes()
  - Compare with plan changes to find pending
  - Build DeploymentStatus object
  - Format output matching Sqitch convention
  - Display project/target info, deployed/pending counts

### Log Command (Simple - 2 days)
- [ ] **T031** Write tests for log display in `tests/cli/commands/test_log_functional.py`
  - Test display all events
  - Test filter by change name
  - Test reverse chronological order
  - Test event type display (deploy/revert/fail)
  - Test output format matches Sqitch
  
- [ ] **T032** Implement log command in `sqlitch/cli/commands/log.py` (~250 lines)
  - Query registry events table via engine.get_events()
  - Filter by change name if provided
  - Format output matching Sqitch log display
  - Show committer, timestamp, note for each event

### Deploy Command (Complex - 4 days)
- [X] **T033** Write tests for deploy with no registry in `tests/cli/commands/test_deploy_functional.py`
  - Test creates sqitch.db on first run ✅
  - Test creates all registry tables ✅
  - Test inserts project record ✅
  - Test inserts release record ✅
  - Test outputs "Adding registry tables" message ✅
  - **Status**: ✅ COMPLETE (2025-10-06) - 5 tests passing
  - **Discovery**: Deploy command ~80% implemented already, only needed output message
  - **Files Created**: `tests/cli/commands/test_deploy_functional.py`
  - **Files Modified**: `sqlitch/cli/commands/deploy.py` (added registry initialization message)
  
- [X] **T034** Write tests for deploy with single change in `tests/cli/commands/test_deploy_functional.py`
  - Test loads deploy script ✅
  - Test executes script in transaction ✅
  - Test inserts change record ✅
  - Test inserts event record ✅
  - Test calculates script_hash correctly ✅
  - Test outputs deployment success message ✅
  - **Status**: ✅ COMPLETE (2025-10-06) - 5 tests passing
  - **Discovery**: All functionality already implemented and working correctly
  
- [X] **T035** Write tests for deploy with multiple changes in `tests/cli/commands/test_deploy_functional.py`
  - Test deploys in plan order ✅
  - Test skips already-deployed changes ✅
  - Test stops on first failure ✅
  - Test rolls back on error ✅
  - **Status**: ✅ COMPLETE (2025-10-06) - 4 tests passing
  - **Discovery**: Rollback and error handling working perfectly
  
- [X] **T036** Write tests for deploy dependency validation in `tests/cli/commands/test_deploy_functional.py`
  - Test validates dependencies before deploy ✅
  - Test fails if required dependency not deployed ✅
  - Test dependency recorded in registry ✅
  - **Status**: ✅ COMPLETE (2025-10-06) - 2 tests passing
  - **Discovery**: Dependency validation fully functional
  
- [X] **T037** Write tests for deploy script execution in `tests/cli/commands/test_deploy_functional.py`
  - Test wraps script in transaction if needed ✅
  - Test doesn't wrap if script manages transactions ✅
  - **Status**: ✅ COMPLETE (2025-10-06) - 2 tests passing
  - **Discovery**: Transaction management working correctly
  - **Note**: Script hash calculation already tested in T034
  
- [X] **T038** Implement deploy command core logic in `sqlitch/cli/commands/deploy.py` (~500 lines)
  - Load plan and get pending changes ✅
  - Validate dependencies via validate_dependencies() ✅
  - For each change:
    * Load Script via Script.load() ✅
    * Execute via engine.execute_script() ✅
    * Calculate script_hash ✅
    * Insert into registry changes table ✅
    * Insert dependencies into dependencies table ✅
    * Insert event into events table ✅
  - Handle --to flag (deploy up to change/tag) ✅
  - Handle --verify flag (run verify after deploy) ✅
  - Resolve committer identity via UserIdentity.from_env/from_config ✅
  - **Status**: ✅ COMPLETE (2025-10-06) - Already implemented
  - **Discovery**: Deploy command fully implemented in Feature 002 (SQLite), verified by 18 functional tests

### Verify Command (Medium - 2 days)
- [ ] **T039** Write tests for verify execution in `tests/cli/commands/test_verify_functional.py`
  - Test executes verify scripts for deployed changes
  - Test reports success for each change
  - Test reports failure with error details
  - Test exit code 0 if all pass, 1 if any fail
  - Test output format matches Sqitch
  
- [ ] **T040** Implement verify command in `sqlitch/cli/commands/verify.py` (~250 lines)
  - Query registry for deployed changes
  - For each change:
    * Load verify script via Script.load()
    * Execute via engine.execute_script()
    * Capture result in ScriptResult
  - Display results (OK/NOT OK for each change)
  - Exit with code 1 if any verification fails

### Revert Command (Complex - 3 days)
- [ ] **T041** Write tests for revert to tag in `tests/cli/commands/test_revert_functional.py`
  - Test reverts changes after tag in reverse order
  - Test stops at tag boundary
  - Test validates no dependent changes deployed
  - Test output format matches Sqitch
  
- [ ] **T042** Write tests for revert to change in `tests/cli/commands/test_revert_functional.py`
  - Test reverts up to specified change
  - Test validates dependencies
  - Test fails if dependent changes exist
  
- [ ] **T043** Write tests for revert script execution in `tests/cli/commands/test_revert_functional.py`
  - Test loads revert script
  - Test executes in transaction
  - Test rolls back on error
  - Test removes from registry on success
  
- [ ] **T044** Implement revert command in `sqlitch/cli/commands/revert.py` (~400 lines)
  - Query deployed changes
  - Determine changes to revert based on --to flag
  - Validate no dependent changes deployed
  - For each change in reverse order:
    * Load revert script via Script.load()
    * Execute via engine.execute_script()
    * Delete from registry changes table
    * Insert revert event into events table
  - Resolve committer identity

### Tag Command (Medium - 2 days)
- [ ] **T045** Write tests for tag creation in `tests/cli/commands/test_tag_functional.py`
  - Test adds tag to plan file
  - Test tag references last change
  - Test validates tag name
  - Test output format matches Sqitch
  
- [ ] **T046** Write tests for tag listing in `tests/cli/commands/test_tag_functional.py`
  - Test lists all tags with no arguments
  - Test shows tag name and referenced change
  
- [ ] **T047** Implement tag command in `sqlitch/cli/commands/tag.py` (~300 lines)
  - Parse plan via parse_plan()
  - Create Tag object with validated name
  - Append tag to plan entries
  - Write plan via write_plan()
  - Resolve planner identity
  - Default action: list tags when no arguments

### Rework Command (Complex - 4 days)
- [ ] **T048** Write tests for rework with latest tag in `tests/cli/commands/test_rework_functional.py`
  - Test creates scripts with @tag suffix
  - Test copies existing scripts as starting point
  - Test updates plan with rework entry
  - Test validates change exists
  
- [ ] **T049** Write tests for rework with specific tag in `tests/cli/commands/test_rework_functional.py`
  - Test uses --from-tag to specify source tag
  - Test copies scripts from tagged version
  - Test creates @tag suffixed files
  
- [ ] **T050** Implement rework command in `sqlitch/cli/commands/rework.py` (~400 lines)
  - Find change in plan via Plan.find_change()
  - Find latest tag or use --from-tag
  - Copy existing scripts to @tag suffixed files
  - Update plan with rework entry (preserves original)
  - Validate change name
  - Resolve planner identity

### Init Command Finalization (1 day)
- [ ] **T051** Write tests for init directory and file creation in `tests/cli/commands/test_init_functional.py`
  - Test creates sqitch.conf with correct engine setting
  - Test creates sqitch.plan with project pragmas (%syntax-version, %project, %uri)
  - Test creates deploy/, revert/, verify/ directories
  - Test verifies directory structure matches FR-001 requirements
  - Test validates file contents match Sqitch format
  
- [ ] **T052** Write tests for init engine validation in `tests/cli/commands/test_init_functional.py`
  - Test validates engine exists in ENGINE_REGISTRY
  - Test fails with clear error if engine invalid
  - Test defaults to sqlite if not specified
  
  - Test defaults to sqlite if not specified
  
- [X] **T053** Complete init command in `sqlitch/cli/commands/init.py`
  - Add engine validation (check ENGINE_REGISTRY) ✅ Already implemented
  - Verify directory creation logic is complete ✅ Confirmed by tests
  - Improve error messages ✅ Confirmed by tests
  - Verify against Sqitch init output format ✅ Confirmed by tests

### Config Command (Simple - 1 day)

### Add Command Finalization (1 day)
- [X] **T054** Write tests for add dependency validation in `tests/cli/commands/test_add_functional.py`
  - ✅ Test validates --requires references exist in plan
  - ✅ Test validates --conflicts references exist in plan  
  - ✅ Test accepts multiple dependencies
  - ✅ Additional: 16 comprehensive tests covering all add functionality
  
- [X] **T055** Complete add command in `sqlitch/cli/commands/add.py`
  - ✅ Creates deploy, revert, verify scripts with proper Sqitch headers
  - ✅ Adds change to plan with note, dependencies, tags
  - ✅ Slugifies change names for filenames
  - ✅ Validates change doesn't already exist
  - ✅ Error handling for missing plan, existing scripts
  - ✅ Quiet mode support
  - ✅ All 16 functional tests passing

---

## Phase 3.3: Integration Tests
**Purpose**: Validate complete tutorial workflows  
**Estimated Time**: 3 days

- [ ] **T056** [P] Integration test: Scenario 1 - Project initialization in `tests/integration/test_tutorial_workflows.py`
  - Test init creates proper structure
  - Test config get/set works
  - Test files have correct content
  
- [ ] **T057** [P] Integration test: Scenario 2 - First change (users table) in `tests/integration/test_tutorial_workflows.py`
  - Test add creates scripts
  - Test deploy creates registry
  - Test verify passes
  - Test status shows deployed
  
- [ ] **T058** [P] Integration test: Scenario 3 - Dependent change (flips table) in `tests/integration/test_tutorial_workflows.py`
  - Test add with --requires
  - Test deploy validates dependency
  - Test deployment succeeds
  
- [ ] **T059** [P] Integration test: Scenario 4 - View creation (userflips) in `tests/integration/test_tutorial_workflows.py`
  - Test add with multiple dependencies
  - Test deploy executes in correct order
  
- [ ] **T060** [P] Integration test: Scenario 5 - Tag release (v1.0.0-dev1) in `tests/integration/test_tutorial_workflows.py`
  - Test tag adds to plan
  - Test deploy after tag works
  
- [ ] **T061** [P] Integration test: Scenario 6 - Revert changes in `tests/integration/test_tutorial_workflows.py`
  - Test revert --to removes changes
  - Test revert executes scripts in reverse
  - Test registry updated correctly
  
- [ ] **T062** [P] Integration test: Scenario 7 - View history with log in `tests/integration/test_tutorial_workflows.py`
  - Test log shows all events
  - Test log filtering by change
  
- [ ] **T063** [P] Integration test: Scenario 8 - Rework change in `tests/integration/test_tutorial_workflows.py`
  - Test rework creates @tag suffixed scripts
  - Test rework updates plan
  - Test deploy uses new version

---

## Phase 3.4: Sqitch Parity Validation
**Purpose**: Ensure output matches Sqitch byte-for-byte  
**Estimated Time**: 2 days

- [ ] **T064** [P] Regression test: Init output parity in `tests/regression/test_tutorial_parity.py`
  - Compare sqlitch init vs sqitch init output
  - Validate file contents match
  
- [ ] **T065** [P] Regression test: Add output parity in `tests/regression/test_tutorial_parity.py`
  - Compare sqlitch add vs sqitch add output
  - Validate script headers match
  
- [ ] **T066** [P] Regression test: Deploy output parity in `tests/regression/test_tutorial_parity.py`
  - Compare sqlitch deploy vs sqitch deploy output
  - Validate registry records match
  
- [ ] **T067** [P] Regression test: Status output parity in `tests/regression/test_tutorial_parity.py`
  - Compare sqlitch status vs sqitch status output
  - Validate formatting matches
  
- [ ] **T068** [P] Regression test: Log output parity in `tests/regression/test_tutorial_parity.py`
  - Compare sqlitch log vs sqitch log output
  - Validate event display matches
  
- [ ] **T069** [P] Regression test: Verify output parity in `tests/regression/test_tutorial_parity.py`
  - Compare sqlitch verify vs sqitch verify output
  - Validate exit codes match
  
- [ ] **T070** [P] Regression test: Revert output parity in `tests/regression/test_tutorial_parity.py`
  - Compare sqlitch revert vs sqitch revert output
  - Validate behavior matches
  
- [ ] **T071** [P] Regression test: Tag output parity in `tests/regression/test_tutorial_parity.py`
  - Compare sqlitch tag vs sqitch tag output
  
- [ ] **T072** [P] Regression test: Rework output parity in `tests/regression/test_tutorial_parity.py`
  - Compare sqlitch rework vs sqitch rework output

---

## Phase 3.5: Polish & Documentation
**Purpose**: Final cleanup and documentation updates  
**Estimated Time**: 2 days

- [ ] **T073** [P] Update .github/copilot-instructions.md with Feature 004 completion
  - Document command implementation status
  - Update known working commands
  - Add tutorial completion notes
  
- [ ] **T074** [P] Update README.md with tutorial instructions
  - Add "Complete SQLite Tutorial" section
  - Link to quickstart.md
  - Document new commands
  
- [ ] **T075** Run full tutorial manually and capture output
  - Follow quickstart.md step-by-step
  - Document any deviations from Sqitch
  - Update quickstart.md with any corrections
  
- [ ] **T076** Final coverage check
  - Run pytest with coverage report
  - Ensure ≥90% coverage on all new modules
  - Add tests for any uncovered branches
  
- [ ] **T077** Performance validation
  - Test deploy with 100 changes
  - Verify completes in <5 seconds
  - Profile any slow operations

---

## Dependencies

### Foundation Phase (T001-T024)
- All tasks in this phase can run in parallel (marked [P])
- Must complete before any command implementation

### Command Phase (T025-T055)
- **T025-T028** (config) - No dependencies, start first
- **T029-T030** (status) - Requires T001-T006 (registry models)
- **T031-T032** (log) - Requires T001-T006 (registry models)
- **T033-T038** (deploy) - Requires T001-T024 (all foundation)
- **T039-T040** (verify) - Requires T013-T016 (script models), T033-T038 (deploy)
- **T041-T044** (revert) - Requires T001-T024 (all foundation), T033-T038 (deploy)
- **T045-T047** (tag) - Requires T021-T022 (plan helpers)
- **T048-T050** (rework) - Requires T021-T022 (plan helpers), T045-T047 (tag)
- **T051-T053** (init finalize) - No dependencies
- **T054-T055** (add finalize) - Requires T023-T024 (validation)

### Integration Phase (T056-T063)
- Requires T025-T055 (all commands implemented)
- All integration tests can run in parallel (marked [P])

### Parity Phase (T064-T072)
- Requires T025-T055 (all commands implemented)
- All parity tests can run in parallel (marked [P])

### Polish Phase (T073-T077)
- Requires T056-T072 (all tests passing)
- Documentation tasks (T073-T074) can run in parallel

---

## Parallel Execution Examples

### Foundation Models (can run simultaneously)
```bash
# Launch T001-T006 together (registry models):
Task: "Write tests for DeployedChange model in tests/registry/test_state.py"
Task: "Write tests for DeploymentEvent model in tests/registry/test_state.py"
Task: "Write tests for DeploymentStatus model in tests/registry/test_state.py"

# Launch T007-T012 together (command models):
Task: "Write tests for CommandResult model in tests/cli/commands/test_models.py"
Task: "Write tests for DeployOptions model in tests/cli/commands/test_models.py"
Task: "Write tests for RevertOptions model in tests/cli/commands/test_models.py"

# Launch T013-T016 together (script models):
Task: "Write tests for Script model in tests/engine/test_scripts.py"
Task: "Write tests for ScriptResult model in tests/engine/test_scripts.py"

# Launch T017-T020 together (identity):
Task: "Write tests for UserIdentity model in tests/utils/test_identity.py"
Task: "Write tests for generate_change_id in tests/utils/test_identity.py"

# Launch T023-T024 together (validation):
Task: "Write tests for validation functions in tests/plan/test_validation.py"
```

### Integration Tests (can run simultaneously after commands done)
```bash
# Launch T056-T063 together:
Task: "Integration test: Scenario 1 - Project initialization"
Task: "Integration test: Scenario 2 - First change (users table)"
Task: "Integration test: Scenario 3 - Dependent change (flips table)"
Task: "Integration test: Scenario 4 - View creation (userflips)"
Task: "Integration test: Scenario 5 - Tag release"
Task: "Integration test: Scenario 6 - Revert changes"
Task: "Integration test: Scenario 7 - View history with log"
Task: "Integration test: Scenario 8 - Rework change"
```

### Parity Validation (can run simultaneously after commands done)
```bash
# Launch T064-T072 together:
Task: "Regression test: Init output parity"
Task: "Regression test: Add output parity"
Task: "Regression test: Deploy output parity"
Task: "Regression test: Status output parity"
Task: "Regression test: Log output parity"
Task: "Regression test: Verify output parity"
Task: "Regression test: Revert output parity"
Task: "Regression test: Tag output parity"
Task: "Regression test: Rework output parity"
```
Task: "Integration test: Scenario 8 - Rework change"
```

### Parity Tests (can run simultaneously)
```bash
# Launch T063-T071 together:
Task: "Regression test: Init output parity"
Task: "Regression test: Add output parity"
Task: "Regression test: Deploy output parity"
Task: "Regression test: Status output parity"
Task: "Regression test: Log output parity"
Task: "Regression test: Verify output parity"
Task: "Regression test: Revert output parity"
Task: "Regression test: Tag output parity"
Task: "Regression test: Rework output parity"
```

---

## Validation Checklist
*Checked before marking feature complete*

- [x] All new models have corresponding tests (T001-T024)
- [x] All commands have functional tests (T025-T054)
- [x] All quickstart scenarios have integration tests (T055-T062)
- [x] All commands have Sqitch parity tests (T063-T071)
- [x] Tests come before implementation (TDD)
- [x] Parallel tasks are truly independent
- [x] Each task specifies exact file path
- [x] No task modifies same file as another [P] task
- [x] Coverage target ≥90% specified (T075)
- [x] Performance target <5s specified (T076)

---

## Task Execution Notes

### Test-First Development (Constitutional Requirement)
- **CRITICAL**: All test tasks (odd-numbered T001, T003, T005...) MUST be completed and tests MUST FAIL before writing implementation
- Do not skip to implementation tasks without failing tests
- Each test task should result in pytest failures that the implementation task will fix

### File Organization
- Registry models: `sqlitch/registry/state.py`
- Command models: `sqlitch/cli/commands/_models.py`
- Script models: `sqlitch/engine/scripts.py`
- Identity helpers: `sqlitch/utils/identity.py`
- Validation helpers: `sqlitch/plan/validation.py`
- Config writer: `sqlitch/config/writer.py` (new)

### Existing Code to Leverage
- Plan parsing: `sqlitch/plan/parser.py` (100% complete)
- Plan writing: `sqlitch/plan/writer.py` (100% complete)
- Config loading: `sqlitch/config/loader.py` (100% complete)
- SQLite engine: `sqlitch/engine/sqlite.py` (95% complete, well-tested)
- Registry schema: `sqlitch/registry/migrations.py` (100% complete)
- Command scaffolding: All commands registered in `sqlitch/cli/commands/__init__.py`

### Research Reference
See `research.md` for:
- Registry table schemas (section 1)
- Existing code analysis (sections 2-5)
- Technical decisions (section 6)
- Effort estimates (section 7)
- Risk analysis (section 8)

### Success Metrics
- **Coverage**: ≥90% (constitutional requirement)
- **Performance**: <5 seconds for 100 changes
- **Parity**: Byte-for-byte output match with Sqitch (excluding timestamps)
- **Tutorial**: All 8 quickstart scenarios pass
- **Quality**: All commands follow existing patterns

---

**Total Tasks**: 77  
**Estimated Duration**: 4-5 weeks  
**Parallel Opportunities**: ~40 tasks can run in parallel (marked [P])  
**Sequential Critical Path**: Foundation → Config → Deploy → Verify/Revert → Integration

**Next Step**: Begin with T001 (Write tests for DeployedChange model)
