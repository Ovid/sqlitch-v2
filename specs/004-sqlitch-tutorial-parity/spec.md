# Feature Specification: SQLite Tutorial Parity

**Feature Branch**: `004-sqlitch-tutorial-parity`  
**Created**: 2025-10-06  
**Status**: Draft  
**Prerequisites**: Feature 003 (CLI Command Parity) complete

## Execution Flow (main)
```
1. Analyze the Sqitch SQLite tutorial (sqitch/lib/sqitchtutorial-sqlite.pod)
2. Identify all workflows, commands, and expected behaviors demonstrated in the tutorial
3. Define which commands need functional implementation vs remaining stubs
4. Map tutorial scenarios to acceptance criteria
5. Capture quality gates and ensure ≥90% coverage
6. Document deviations and implementation priorities
7. Review with stakeholders before planning
```

---

## ⚡ Quick Guidelines
- Implement the minimum command functionality required to complete the SQLite tutorial end-to-end
- Focus on the "happy path" workflows: init, add, deploy, revert, verify, status, log, tag
- Maintain CLI parity established in Feature 003
- Ensure all tutorial examples work identically with `sqlitch` as they do with `sqitch`
- Default output MUST remain byte-aligned with Sqitch
- Structured logging remains available via flags but not in default output
- ≥90% test coverage maintained
- All public APIs documented with docstrings

---

## Tutorial Analysis

### Source Document
**Location**: `sqitch/lib/sqitchtutorial-sqlite.pod` (1,253 lines)

### Tutorial Structure
The Sqitch SQLite tutorial demonstrates a complete workflow for managing database changes in a fictional "Flipr" antisocial networking application. Key sections:

1. **Starting a New Project** - Initialize Git repo and Sqitch project
2. **Our First Change** - Create and deploy the `users` table
3. **Trust, But Verify** - Verify scripts and validation
4. **Status, Revert, Log, Repeat** - Change management workflows
5. **On Target** - Configure and manage deployment targets
6. **Deploy with Dependency** - Create dependent changes (`flips` table)
7. **View to a Thrill** - Create database views (`userflips`)
8. **Ship It!** - Tag releases (v1.0.0-dev1)
9. **Making a Hash of Things** - Conflict resolution and merges
10. **Emergency** - Hotfix workflows
11. **Merges Mastered** - Branch merging strategies
12. **In Place Changes** - Reworking existing changes with tags

### Commands Used in Tutorial

**Must Be Functional** (tutorial-critical):
- [x] `sqitch init` - Initialize project with name, URI, engine ✅ (stub exists)
- [ ] `sqitch config` - Get/set configuration values
- [ ] `sqitch add` - Add new changes with dependencies
- [ ] `sqitch deploy` - Deploy changes to database
- [ ] `sqitch verify` - Verify deployed changes
- [ ] `sqitch revert` - Revert changes
- [ ] `sqitch status` - Show deployment status
- [ ] `sqitch log` - Show change history
- [ ] `sqitch tag` - Tag releases
- [ ] `sqitch rework` - Create in-place change modifications

**Can Remain Stubs** (not used in tutorial):
- [ ] `sqitch bundle` - Package changes for distribution
- [ ] `sqitch checkout` - Switch between branches
- [ ] `sqitch rebase` - Rebase changes
- [ ] `sqitch upgrade` - Upgrade registry schema
- [ ] `sqitch engine` - Manage engine configurations
- [ ] `sqitch target` - Manage deployment targets
- [ ] `sqitch plan` - Display plan
- [ ] `sqitch show` - Show change details
- [ ] `sqitch help` - Display help (already functional)

### Key Workflows Demonstrated

1. **Project Initialization**
   ```bash
   sqitch init flipr --uri https://github.com/... --engine sqlite
   sqitch config --user user.name 'Marge N. O'Vera'
   sqitch config --user user.email 'marge@example.com'
   ```

2. **Change Creation and Deployment**
   ```bash
   sqitch add users -n 'Creates table to track our users.'
   # Edit deploy/users.sql, revert/users.sql, verify/users.sql
   sqitch deploy db:sqlite:flipr_test.db
   sqitch verify db:sqlite:flipr_test.db
   sqitch status db:sqlite:flipr_test.db
   ```

3. **Dependency Management**
   ```bash
   sqitch add flips --requires users -n 'Adds table for storing flips.'
   sqitch deploy db:sqlite:flipr_test.db
   ```

4. **Views and Complex Changes**
   ```bash
   sqitch add userflips --requires users --requires flips
   # Create view in deploy script
   ```

5. **Tagging Releases**
   ```bash
   sqitch tag v1.0.0-dev1 -n 'Tag v1.0.0-dev1.'
   sqitch deploy db:sqlite:flipr_test.db
   ```

6. **Reverting Changes**
   ```bash
   sqitch revert db:sqlite:flipr_test.db --to @HEAD^
   sqitch deploy db:sqlite:flipr_test.db
   ```

7. **Change History**
   ```bash
   sqitch log db:sqlite:flipr_test.db
   ```

8. **Reworking Changes**
   ```bash
   sqitch rework userflips -n 'Add twitter column to userflips view.'
   # Creates userflips@v1.0.0-dev2.sql scripts
   ```

---

## Clarifications

### Session 2025-10-06
- Q: Should Feature 004 implement all commands or just tutorial-critical ones?
  → A: **Implement all 10 tutorial commands in the order they appear in the tutorial**
- Q: What level of config command functionality is required (just get/set or full subcommands)?
  → A: **Just enough to complete the tutorial** (get/set operations for user.name, user.email, engine.sqlite.client)
- Q: Should target management be functional or can it use in-memory targets only?
  → A: **URI-based targets as demonstrated in tutorial** (db:sqlite:path/to/db)
- Q: For rework command, what is the minimum viable implementation?
  → A: **Just enough to complete the tutorial** (create @tag suffixed scripts, update plan)
- Q: Should we support Git integration or manual plan editing only?
  → A: **Manual workflow** (user handles git commands separately)
- Q: What registry operations beyond deploy/revert are required?
  → A: **Enough to complete the tutorial, aligned with Sqitch behavior** (deploy, revert, verify events; status queries; log display)

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
Database developers following the SQLite tutorial need to successfully complete all demonstrated workflows using `sqlitch` instead of `sqitch`, achieving identical results and outputs.

### Acceptance Scenarios
1. **Given** a user follows the SQLite tutorial step-by-step, **When** they replace `sqitch` with `sqlitch` in all commands, **Then** all examples work identically with matching output, file generation, and database state.

2. **Given** a user initializes a new SQLitch project, **When** they add changes with dependencies, deploy them, verify them, tag releases, and revert changes, **Then** the registry database correctly tracks all operations and the plan file remains valid.

3. **Given** a user creates a reworked change, **When** they deploy it after tagging, **Then** SQLitch correctly handles the tagged script files and applies the new version.

### Edge Cases
- How does SQLitch handle missing registry database on first deploy?
- What happens when deploy scripts fail mid-execution?
- How are circular dependencies detected and reported?
- What if verify scripts have errors?
- How does revert handle missing revert scripts?
- What happens when target database doesn't exist?
- How are conflicts in plan files detected?

---

## Requirements *(mandatory)*

### Functional Requirements

**Configuration Management**:
- **FR-001**: SQLitch MUST support hierarchical configuration with three scopes: system (/etc/sqitch/), user (~/.sqitch/), and local (project ./), where local overrides user, and user overrides system.

- **FR-002**: Configuration files MUST use INI format with sections and key-value pairs, support multi-line values (using backslash continuation per Git config format), and preserve comments.

- **FR-003**: Config file format MUST match Sqitch conventions with 4-space indentation for values:
  ```ini
  [core]
      engine = sqlite
  
  [user]
      name = Marge N. O'Vera
      email = marge@example.com
  
  [engine "sqlite"]
      target = db:sqlite:flipr.db
  ```

- **FR-004**: User identity resolution MUST follow this priority order:
  1. Config file `[user]` section (`user.name` and `user.email`)
  2. Environment variables (in order of preference):
     - `SQLITCH_USER_NAME` / `SQLITCH_USER_EMAIL` (preferred)
     - `SQITCH_USER_NAME` / `SQITCH_USER_EMAIL` (fallback for Sqitch compatibility)
     - `GIT_COMMITTER_NAME` / `GIT_COMMITTER_EMAIL`
     - `GIT_AUTHOR_NAME` / `GIT_AUTHOR_EMAIL`
  3. System environment (`USER`, `USERNAME` for name; `EMAIL` for email)
  4. Generated fallback (sanitized username + `@example.invalid` domain)

- **FR-005**: Environment variable handling MUST prefer `SQLITCH_*` prefixed variables over `SQITCH_*` prefixed variables for all configuration options, with `SQITCH_*` variables serving as fallback for backward compatibility with Sqitch.

- **FR-006**: Deploy and revert operations MUST record the committer identity (name and email) in the registry `events` table, using the identity resolution defined in FR-004.

**Core Commands (Tutorial-Critical)**:
- **FR-007**: `sqitch init` MUST initialize a new SQLitch project with project name, URI, engine, creating sqitch.conf, sqitch.plan, and deploy/revert/verify directories.

- **FR-008**: `sqitch config` MUST support get/set/list operations for project-local (sqitch.conf), user (~/.sqitch/sqitch.conf), and system configurations with proper precedence.

- **FR-009**: `sqitch add` MUST create deploy, revert, and verify script files with proper headers, add changes to the plan file, support dependency declarations (--requires, --conflicts), and accept change notes.

- **FR-010**: `sqitch deploy` MUST deploy pending changes to target database in plan order, execute deploy scripts within transactions (unless scripts manage their own), record deployments in registry database, validate dependencies, and skip already-deployed changes.

- **FR-011**: `sqitch verify` MUST execute verify scripts for deployed changes, report success/failure for each change, and exit with appropriate code (0=success, 1=failure).

- **FR-012**: `sqitch revert` MUST revert deployed changes in reverse order, execute revert scripts, update registry to remove change records, support --to flag for partial reverts, and validate no dependent changes exist.

- **FR-013**: `sqitch status` MUST query registry database, display current deployment state, show deployed/pending changes, and indicate project/target information.

- **FR-014**: `sqitch log` MUST display change history from registry, show deploy/revert/fail events, support filtering by change name, and format output matching Sqitch conventions.

- **FR-015**: `sqitch tag` MUST add tags to plan file, support tag notes, allow tagging at specific changes, and enable script file naming with @tag suffixes.

- **FR-016**: `sqitch rework` MUST create new script versions with @tag suffixes, update plan file with rework entries, copy existing scripts as starting point, and preserve original scripts.

**Registry Management**:
- **FR-017**: SQLitch MUST create registry database (sqitch.db) as a sibling to the target database on first deploy, create all required tables (changes, dependencies, events, projects, releases, tags), and handle SQLite ATTACH DATABASE for registry access.

- **FR-018**: Registry operations MUST be atomic with deploy/revert operations, roll back registry changes if deploy fails, and maintain referential integrity.

**Plan Management**:
- **FR-019**: Plan file operations MUST preserve pragmas (%syntax-version, %project, %uri), maintain change order, validate change names are unique, support tags and dependencies, and detect conflicts including: (a) circular require/conflicts chains, (b) duplicate change names, (c) dependencies on non-existent changes, (d) conflicts declarations creating cycles.

- **FR-019a**: Plan files MUST use Sqitch-compatible compact format by default for maximum interoperability. The plan file format consists of:
  
  **Header Section** (pragmas starting with `%`):
  ```
  %syntax-version=1.0.0
  %project=<project_name>
  %uri=<project_uri>
  %default_engine=<engine_name>  # SQLitch extension (Sqitch uses engine.sqlite.target)
  ```
  
  **Change Entry Format** (compact Sqitch-compatible format):
  ```
  <change_name> [<dependencies>] <timestamp> <planner> # <note>
  ```
  
  Where:
  - `<change_name>`: Change identifier (alphanumeric, hyphens, underscores, colons)
  - `[<dependencies>]`: Optional space-separated list of required changes in square brackets
  - `<timestamp>`: ISO 8601 timestamp with timezone (e.g., `2025-10-06T19:38:09Z`)
  - `<planner>`: Name and email in format `Name <email@example.com>` or just `email@example.com`
  - `# <note>`: Optional comment describing the change
  
  **Example Change**:
  ```
  users 2025-10-06T19:38:09Z Test User <test@example.com> # Creates table to track our users.
  flipruser [users] 2025-10-06T19:43:22Z Test User <test@example.com> # Creates flipr user.
  ```
  
  **Tag Entry Format**:
  ```
  @<tag_name> <timestamp> <planner> # <note>
  ```
  
  Where:
  - `@<tag_name>`: Tag identifier prefixed with `@`
  - Tag implicitly references the immediately preceding change
  - Timestamp and planner follow same format as changes
  
  **Example Tag**:
  ```
  @v1.0.0 2025-10-06T20:00:00Z Test User <test@example.com> # Release 1.0
  ```
  
  **Formal Grammar** (EBNF-style):
  ```
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
  
  **Verbose Format Support** (for internal use only):
  SQLitch parser MUST also support a verbose metadata format for backward compatibility:
  ```
  change <name> <deploy_path> <revert_path> [verify=<verify_path>] planner=<planner> planned_at=<timestamp> [notes=<note>] [depends=<dep1>,<dep2>] [change_id=<uuid>]
  tag <name> <change_ref> planner=<planner> tagged_at=<timestamp>
  ```
  
  However, all SQLitch commands that write plan files (init, add, tag, rework) MUST output the compact Sqitch-compatible format to maintain interoperability. The verbose format exists only for parsing legacy SQLitch files.
  
  **Critical Implementation Note**: The current `sqlitch.plan.formatter` module outputs the **verbose format**, which violates this requirement. The formatter MUST be updated to output the compact format. The parser correctly supports both formats (compact for Sqitch compatibility, verbose for legacy SQLitch files).

**Script Generation**:
- **FR-020**: Script templates MUST match Sqitch templates exactly and include proper headers with project:change notation. Templates MUST include BEGIN/COMMIT transaction wrappers (deploy/revert) or BEGIN/ROLLBACK (verify) as placeholders for user modification. SQLitch MUST NOT add or modify transaction control in user scripts - users are responsible for transaction management within their scripts. Templates MUST provide XXX TODO comments for user implementation and follow naming conventions (deploy/change.sql, revert/change.sql, verify/change.sql).

  **Template Alignment** (Constitutional Principle VI - Behavioral Parity):
  SQLitch script templates MUST be byte-identical to Sqitch templates from `sqitch/etc/templates/{deploy,revert,verify}/{engine}.tmpl`. For SQLite:
  
  - **Deploy template**: Includes `BEGIN;` / `COMMIT;` wrapper with `-- XXX Add DDLs here.` placeholder
  - **Revert template**: Includes `BEGIN;` / `COMMIT;` wrapper with `-- XXX Add DDLs here.` placeholder  
  - **Verify template**: Includes `BEGIN;` / `ROLLBACK;` wrapper with `-- XXX Add verifications here.` placeholder
  
  Templates are discovered in order: project templates → user config templates → system /etc/sqitch templates. Users may customize templates by placing modified versions in these locations. SQLitch renders templates using the same Template Toolkit-style syntax as Sqitch (`[% variable %]`, `[% FOREACH ... %]`).

**Target Management**:
- **FR-021**: SQLitch MUST parse database URIs (db:sqlite:path/to/db), resolve relative paths from project root, create target databases if they don't exist, and support in-memory databases (:memory:).

### Non-Functional Requirements

- **NFR-001**: All tutorial examples MUST complete successfully with identical outputs to Sqitch (within timezone/timestamp variations).

- **NFR-002**: Command execution MUST maintain ≥90% test coverage across all implemented commands.

- **NFR-003**: Deploy operations SHOULD complete in <5 seconds for plans with <100 changes on developer hardware (4+ cores, SSD storage, local database).

- **NFR-004**: Default CLI output MUST match Sqitch byte-for-byte (excluding timestamps/user-specific data), structured logging only appears with explicit flags.

- **NFR-005**: All error messages MUST be clear, actionable, and follow Sqitch conventions.

### Key Entities *(include if feature involves data)*

- **Project**: Initialized SQLitch project with name, URI, engine config
- **Change**: Individual database migration with deploy/revert/verify scripts
- **Tag**: Named point in deployment plan for versioning
- **Dependency**: Relationship between changes (requires, conflicts)
- **Target**: Database connection configuration
- **Registry**: SQLite database tracking deployment state
- **Event**: Deploy/revert/fail record in registry

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous  
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Tutorial analyzed
- [x] Commands catalogued
- [x] Workflows identified
- [x] Requirements drafted
- [x] Clarifications resolved
- [x] Review checklist passed

---

## Notes

### Implementation Order (Tutorial Sequence)

Based on the Sqitch SQLite tutorial, commands appear in this order:

1. **`sqitch init`** - Section: "Starting a New Project" (line 58)
   - Initialize project with name, URI, engine
   - Creates sqitch.conf, sqitch.plan, deploy/, revert/, verify/

2. **`sqitch config`** - Section: "Starting a New Project" (line 95)
   - User-level config: user.name, user.email
   - Engine-level config: engine.sqlite.client

3. **`sqitch add`** - Section: "Our First Change" (line 144)
   - Create change with deploy/revert/verify scripts
   - Update plan file

4. **`sqitch deploy`** - Section: "Our First Change" (line 202)
   - Create registry database
   - Execute deploy scripts
   - Record in registry

5. **`sqitch verify`** - Section: "Trust, But Verify" (line 240)
   - Execute verify scripts
   - Report success/failure

6. **`sqitch status`** - Section: "Status, Revert, Log, Repeat" (line 274)
   - Query registry
   - Display deployment state

7. **`sqitch revert`** - Section: "Status, Revert, Log, Repeat" (line ~300)
   - Revert changes in reverse order
   - Update registry

8. **`sqitch log`** - Section: "Status, Revert, Log, Repeat" (line ~350)
   - Display deployment history
   - Show events from registry

9. **`sqitch tag`** - Section: "Ship It!" (line ~600)
   - Add release tags to plan
   - Enable @tag suffixes in scripts

10. **`sqitch rework`** - Section: "In Place Changes" (line ~1150)
    - Create new versions of changes
    - Copy scripts with @tag suffixes

This order suggests a phased implementation approach where each command builds on the previous ones.

### Implementation Priority
Given the tutorial's structure, the recommended implementation order is:

1. **Phase 1**: Foundation (init, config)
2. **Phase 2**: Basic workflow (add, deploy, verify, status)
3. **Phase 3**: Advanced workflow (revert, log, tag)
4. **Phase 4**: Complex features (rework, dependencies)

### Out of Scope (Future Features)
- Multi-engine support (MySQL, PostgreSQL) - covered in Feature 002
- Bundle command - not tutorial-critical
- Checkout/rebase commands - not tutorial-critical  
- Engine/target management commands - basic support only
- VCS integration (git hooks, auto-commit) - manual for now

### Dependencies
- **Requires**: Feature 003 (CLI Command Parity) - ✅ Complete
- **Requires**: Feature 002 (SQLite Engine) - ⚠️ Partial (registry exists, deploy missing)
- **Blocks**: Feature 005+ (Additional database engines)

