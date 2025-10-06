# Research: SQLite Tutorial Parity

**Feature**: 004-sqlitch-tutorial-parity  
**Date**: October 6, 2025  
**Status**: Complete

---

## Executive Summary

This research document analyzes the existing SQLitch codebase to understand what's already implemented and what needs to be built for Feature 004. Key findings:

**Already Implemented** (≥80% done):
- ✅ Registry schema (SQLite) - 100% complete
- ✅ Plan parsing and formatting - 100% complete
- ✅ Config loading/resolution - 100% complete
- ✅ Command scaffolding - 100% complete (all stubs exist)
- ✅ `init` command - ~80% complete (file generation works)
- ✅ `add` command - ~80% complete (script generation works)

**Needs Implementation** (~20% remaining):
- ⚠️ `config` command - Get/set operations missing
- ❌ `deploy` command - Core deploy logic missing
- ❌ `verify` command - Verification execution missing
- ❌ `status` command - Registry queries missing
- ❌ `revert` command - Revert logic missing
- ❌ `log` command - Event display missing
- ❌ `tag` command - Tag management missing
- ❌ `rework` command - Rework logic missing

**Key Insight**: The foundation is solid. Most of the infrastructure exists—we just need to implement the command-specific business logic that interacts with the registry database and executes SQL scripts.

---

## 1. Registry Schema Analysis

### Location
- **File**: `sqlitch/registry/migrations.py`
- **SQLite Schema**: `_SQLITE_BASELINE` (lines 19-100)

### Tables Present (100% Complete)

#### 1.1 `releases` Table
```sql
CREATE TABLE releases (
    version         FLOAT       PRIMARY KEY,
    installed_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    installer_name  TEXT        NOT NULL,
    installer_email TEXT        NOT NULL
);
```
**Purpose**: Track registry schema versions  
**Usage**: Created during first deploy, queried for migrations

#### 1.2 `projects` Table
```sql
CREATE TABLE projects (
    project         TEXT        PRIMARY KEY,
    uri             TEXT            NULL UNIQUE,
    created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator_name    TEXT        NOT NULL,
    creator_email   TEXT        NOT NULL
);
```
**Purpose**: Store project metadata  
**Usage**: One row per project; inserted during first deploy

####1.3 `changes` Table
```sql
CREATE TABLE changes (
    change_id       TEXT        PRIMARY KEY,
    script_hash     TEXT            NULL,
    change          TEXT        NOT NULL,
    project         TEXT        NOT NULL REFERENCES projects(project),
    note            TEXT        NOT NULL DEFAULT '',
    committed_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    committer_name  TEXT        NOT NULL,
    committer_email TEXT        NOT NULL,
    planned_at      DATETIME    NOT NULL,
    planner_name    TEXT        NOT NULL,
    planner_email   TEXT        NOT NULL,
    UNIQUE(project, script_hash)
);
```
**Purpose**: Track currently deployed changes  
**Usage**: INSERT on deploy, DELETE on revert, SELECT for status

#### 1.4 `tags` Table
```sql
CREATE TABLE tags (
    tag_id          TEXT        PRIMARY KEY,
    tag             TEXT        NOT NULL,
    project         TEXT        NOT NULL REFERENCES projects(project),
    change_id       TEXT        NOT NULL REFERENCES changes(change_id),
    note            TEXT        NOT NULL DEFAULT '',
    committed_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    committer_name  TEXT        NOT NULL,
    committer_email TEXT        NOT NULL,
    planned_at      DATETIME    NOT NULL,
    planner_name    TEXT        NOT NULL,
    planner_email   TEXT        NOT NULL,
    UNIQUE(project, tag)
);
```
**Purpose**: Track tags applied to database  
**Usage**: INSERT when deploying to tag, SELECT for status/log

#### 1.5 `dependencies` Table
```sql
CREATE TABLE dependencies (
    change_id       TEXT        NOT NULL REFERENCES changes(change_id),
    type            TEXT        NOT NULL,
    dependency      TEXT        NOT NULL,
    dependency_id   TEXT            NULL REFERENCES changes(change_id),
    PRIMARY KEY (change_id, dependency),
    CHECK (
        (type = 'require'  AND dependency_id IS NOT NULL)
     OR (type = 'conflict' AND dependency_id IS NULL)
    )
);
```
**Purpose**: Track satisfied dependencies  
**Usage**: INSERT on deploy, DELETE on revert, SELECT for validation

#### 1.6 `events` Table
```sql
CREATE TABLE events (
    event           TEXT        NOT NULL CHECK (
        event IN ('deploy', 'revert', 'fail', 'merge')
    ),
    change_id       TEXT        NOT NULL,
    change          TEXT        NOT NULL,
    project         TEXT        NOT NULL REFERENCES projects(project),
    note            TEXT        NOT NULL DEFAULT '',
    requires        TEXT        NOT NULL DEFAULT '',
    conflicts       TEXT        NOT NULL DEFAULT '',
    tags            TEXT        NOT NULL DEFAULT '',
    committed_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    committer_name  TEXT        NOT NULL,
    committer_email TEXT        NOT NULL,
    planned_at      DATETIME    NOT NULL,
    planner_name    TEXT        NOT NULL,
    planner_email   TEXT        NOT NULL,
    PRIMARY KEY (change_id, committed_at)
);
```
**Purpose**: Full audit history of all deployment events  
**Usage**: INSERT on every deploy/revert/fail, SELECT for log command

### Registry Operations Needed

**For Deploy**:
1. Check if registry exists, create if needed (via migrations.py)
2. INSERT or UPDATE project
3. SELECT existing changes to determine what's deployed
4. For each pending change:
   - Validate dependencies exist in `changes` table
   - Execute deploy script
   - INSERT into `changes` table
   - INSERT dependencies into `dependencies` table
   - INSERT event into `events` table

**For Revert**:
1. SELECT deployed changes in reverse order
2. For each change to revert:
   - Check no deployed changes depend on it
   - Execute revert script
   - DELETE from `changes` table
   - DELETE dependencies from `dependencies` table
   - INSERT revert event into `events` table

**For Verify**:
1. SELECT all changes from `changes` table
2. Execute verify script for each
3. Report success/failure (no registry updates)

**For Status**:
1. SELECT from `changes`, `tags`, `projects` tables
2. Compare deployed changes to plan file
3. Display current state

**For Log**:
1. SELECT from `events` table
2. Format and display chronologically
3. Support filtering by change name

---

## 2. Plan File Handling

### Location
- **Parser**: `sqlitch/plan/parser.py`
- **Formatter**: `sqlitch/plan/formatter.py`
- **Models**: `sqlitch/plan/model.py`

### Capabilities (100% Complete)

#### 2.1 Plan Parsing (`parse_plan`)
```python
def parse_plan(path: Path | str, *, default_engine: str | None = None) -> Plan
```

**Features**:
- ✅ Parses pragmas (%project, %uri, %syntax-version, %default_engine)
- ✅ Parses changes with dependencies: `users [other_change] 2024-...`
- ✅ Parses tags: `@v1.0.0 2024-...`
- ✅ Parses compact format (without 'change' keyword)
- ✅ Validates project and engine headers present
- ✅ Computes plan checksum
- ✅ Returns typed `Plan` object with `Change` and `Tag` entries

**Models Available**:
```python
@dataclass
class Change:
    name: str
    timestamp: datetime
    planner: str
    note: str = ""
    requires: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    # ...

@dataclass
class Tag:
    name: str
    timestamp: datetime
    planner: str
    note: str = ""
    # ...

@dataclass
class Plan:
    project_name: str
    file_path: Path
    entries: tuple[PlanEntry, ...]
    checksum: str
    default_engine: str
    syntax_version: str = "1.0.0"
    uri: str | None = None
```

#### 2.2 Plan Writing (`write_plan`)
```python
def write_plan(plan: Plan, *, output_path: Path | None = None) -> None
```

**Features**:
- ✅ Writes pragmas with proper formatting
- ✅ Writes blank line after pragmas (FR-020 compliance)
- ✅ Writes changes with dependencies
- ✅ Writes tags with proper formatting
- ✅ Preserves UTF-8 encoding

### Plan Operations Needed

**For Add**:
1. Parse existing plan
2. Create new `Change` object
3. Append to plan entries
4. Write updated plan

**For Tag**:
1. Parse existing plan
2. Create new `Tag` object
3. Insert after current change
4. Write updated plan

**For Rework**:
1. Parse existing plan
2. Find existing change
3. Create new change entry with @tag suffix
4. Append to plan (after tag marker)
5. Write updated plan

---

## 3. Configuration Management

### Location
- **Loader**: `sqlitch/config/loader.py`
- **Resolver**: `sqlitch/config/resolver.py`

### Capabilities (100% Complete for Loading)

#### 3.1 Config Loading (`load_config`)
```python
def load_config(
    *,
    root_dir: Path | str,
    scope_dirs: Mapping[ConfigScope, Path | str],
    config_filenames: Sequence[str] | None = None,
) -> ConfigProfile
```

**Features**:
- ✅ Multi-scope support (system/user/local)
- ✅ Precedence handling (local > user > system)
- ✅ Supports both sqitch.conf and sqlitch.conf
- ✅ Detects conflicts within same scope
- ✅ Returns `ConfigProfile` with merged settings
- ✅ Extracts active engine from [core] section

**ConfigProfile Structure**:
```python
@dataclass(frozen=True)
class ConfigProfile:
    root_dir: Path
    files: tuple[Path, ...]
    settings: Mapping[str, Mapping[str, str]]
    active_engine: str | None
```

#### 3.2 Config Resolution (`resolve_config`)
```python
def resolve_config(
    *,
    root_dir: Path | str,
    user_home: Path | str | None = None,
    system_dir: Path | str | None = None,
) -> ConfigProfile
```

**Features**:
- ✅ Automatic scope directory resolution
- ✅ Handles missing home/system directories
- ✅ Returns merged configuration

### Config Operations Needed

**For config command** (NEW - ~200 lines):
1. **Get operation**: `sqlitch config core.engine`
   - Load ConfigProfile
   - Navigate to section.key
   - Print value

2. **Set operation**: `sqlitch config --user user.name "Alice"`
   - Determine scope (--local, --user, --system)
   - Load existing config file (if exists)
   - Update section.key = value
   - Write config file

3. **List operation**: `sqlitch config --list`
   - Load all scopes
   - Print all settings with source files

4. **Unset operation**: `sqlitch config --unset core.engine`
   - Load config file for scope
   - Remove key
   - Write updated file

**Implementation Note**: Config writer needs to preserve INI format:
```python
import configparser

def write_config(path: Path, settings: Mapping[str, Mapping[str, str]]) -> None:
    parser = configparser.ConfigParser()
    parser.optionxform = str  # preserve case
    for section, values in settings.items():
        if section != "DEFAULT":
            parser.add_section(section)
        for key, value in values.items():
            parser[section][key] = value
    with path.open("w", encoding="utf-8") as f:
        parser.write(f)
```

---

## 4. Command Infrastructure

### Location
- **Base**: `sqlitch/cli/commands/__init__.py`
- **Context**: `sqlitch/cli/commands/_context.py`
- **Options**: `sqlitch/cli/options.py`

### Capabilities (100% Complete)

#### 4.1 Command Registration
```python
_COMMAND_REGISTRY: dict[str, click.Command] = {}

def register_command(command: click.Command) -> click.Command:
    """Register a Click command with the CLI."""
    _COMMAND_REGISTRY[command.name] = command
    return command

@click.command("mycommand")
@register_command
def my_command_impl(...):
    ...
```

**Status**: ✅ All 19 commands registered and working

#### 4.2 CLI Context (`CLIContext`)
```python
@dataclass
class CLIContext:
    project_root: Path
    quiet: bool
    verbose: int
    env: Mapping[str, str]
    config: ConfigProfile
    engine: str | None
    target: str | None
    plan_file: Path | None
    # ...
```

**Features**:
- ✅ Resolves project root
- ✅ Loads merged config
- ✅ Provides environment access
- ✅ Available via `require_cli_context(ctx)`

#### 4.3 Global Options
```python
@global_sqitch_options  # --chdir, --no-pager, --engine, --target
@global_output_options  # --quiet, --verbose, --json
```

**Status**: ✅ All options work across commands

### Command Patterns to Follow

**Standard Command Structure**:
```python
@click.command("mycommand")
@click.argument("arg_name")
@click.option("--flag", help="...")
@global_sqitch_options
@global_output_options
@click.pass_context
def mycommand(
    ctx: click.Context,
    arg_name: str,
    flag: bool,
    json_mode: bool,
    verbose: int,
    quiet: bool,
) -> None:
    """Command description."""
    # 1. Get CLI context
    cli_context = require_cli_context(ctx)
    
    # 2. Load plan if needed
    plan_path = resolve_plan_path(cli_context)
    plan = parse_plan(plan_path, default_engine=cli_context.engine)
    
    # 3. Connect to database (for deploy/revert/verify)
    engine = get_engine_for_target(cli_context.target)
    conn = engine.connect_workspace(uri)
    
    # 4. Execute command logic
    # ...
    
    # 5. Output results
    if not quiet:
        click.echo("Success!")
```

---

## 5. Existing Command Implementations

### 5.1 `init` Command (~80% Complete)

**File**: `sqlitch/cli/commands/init.py` (273 lines)

**What Works**:
- ✅ Creates sqitch.conf with [core] engine
- ✅ Creates sqitch.plan with pragmas
- ✅ Creates deploy/, revert/, verify/ directories
- ✅ Validates no existing files
- ✅ Writes engine-specific config comments
- ✅ Handles --uri, --engine, --top-dir options

**What's Missing**:
- ⚠️ Doesn't validate engine is supported
- ⚠️ Doesn't write engine-specific sections properly

**Tutorial Usage**:
```bash
sqitch init flipr --uri https://github.com/.../  --engine sqlite
```

**Estimated Completion**: 1-2 hours to add engine validation

### 5.2 `add` Command (~80% Complete)

**File**: `sqlitch/cli/commands/add.py` (288 lines)

**What Works**:
- ✅ Parses existing plan
- ✅ Creates Change object with dependencies
- ✅ Generates deploy/revert/verify scripts from templates
- ✅ Writes updated plan
- ✅ Handles --requires, --conflicts, --note options
- ✅ Template discovery from multiple locations
- ✅ Script naming (uses slugified change names)

**What's Missing**:
- ⚠️ Doesn't validate dependency changes exist in plan
- ⚠️ Template rendering could be improved

**Tutorial Usage**:
```bash
sqitch add users -n 'Creates table to track our users.'
sqitch add flips --requires users -n 'Adds table for storing flips.'
```

**Estimated Completion**: 2-3 hours to add dependency validation

### 5.3 Other Commands (Stubs)

All other commands exist as stubs that print "not implemented" messages:
- `config` - 53 lines stub
- `deploy` - 1199 lines stub (with extensive options defined)
- `verify` - 61 lines stub
- `status` - 489 lines stub
- `revert` - 235 lines stub
- `log` - 363 lines stub
- `tag` - 196 lines stub
- `rework` - 218 lines stub

**Key Observation**: The stubs have proper CLI signatures and option parsing. We just need to replace the `raise CommandError("not implemented")` with actual logic.

---

## 6. SQLite Engine Adapter

### Location
- **File**: `sqlitch/engine/sqlite.py` (317 lines)
- **Base**: `sqlitch/engine/base.py` (237 lines)

### Capabilities (95% Complete - per Feature 003 testing)

#### 6.1 Connection Management
```python
class SQLiteEngine(Engine):
    def connect_workspace(self, uri: str, **kwargs) -> sqlite3.Connection:
        """Connect to workspace database."""
        # Resolves file path from URI
        # Opens SQLite connection
        # Attaches registry database as 'sqitch'
        
    def build_workspace_connect_arguments(self, uri: str) -> dict[str, Any]:
        """Build connection args for workspace."""
```

**Features**:
- ✅ URI parsing (db:sqlite:path/to/file.db)
- ✅ Registry attachment (ATTACH DATABASE)
- ✅ Registry filesystem path resolution
- ✅ Support for :memory: databases

#### 6.2 Script Execution Helpers
```python
def extract_sqlite_statements(script: str) -> list[str]:
    """Extract individual SQL statements from script."""
    
def script_manages_transactions(script: str) -> bool:
    """Check if script contains transaction control keywords."""
```

**Features**:
- ✅ Splits multi-statement scripts
- ✅ Detects transaction keywords (BEGIN, COMMIT, etc.)
- ✅ Handles string literals (ignores keywords in quotes)

### Engine Operations Needed

**For Deploy** (NEW - core logic):
```python
def deploy_change(
    conn: sqlite3.Connection,
    change: Change,
    script_path: Path,
    project: str,
    planner: str,
) -> None:
    """Deploy a single change to the database."""
    # 1. Read deploy script
    # 2. Extract statements
    # 3. Check if script manages transactions
    # 4. Execute statements (wrapped in transaction if needed)
    # 5. INSERT into changes table
    # 6. INSERT dependencies
    # 7. INSERT event
    # 8. Commit transaction
```

**For Revert** (NEW - core logic):
```python
def revert_change(
    conn: sqlite3.Connection,
    change_id: str,
    script_path: Path,
) -> None:
    """Revert a single change from the database."""
    # 1. Read revert script
    # 2. Execute statements
    # 3. DELETE from changes table
    # 4. DELETE dependencies
    # 5. INSERT revert event
    # 6. Commit transaction
```

**For Verify** (NEW):
```python
def verify_change(
    conn: sqlite3.Connection,
    change: Change,
    script_path: Path,
) -> bool:
    """Verify a change is correctly deployed."""
    # 1. Read verify script
    # 2. Execute statements (catch errors)
    # 3. Return success/failure (no registry updates)
```

---

## 7. Template System

### Location
- **File**: `sqlitch/utils/templates.py` (177 lines)

### Capabilities (100% Complete)

```python
def resolve_template_path(
    *, kind: str, engine: str, directories: Sequence[Path], template_name: str | None
) -> Path | None:
    """Find template file in search path."""
    
def default_template_body(kind: str) -> str:
    """Return default template content."""
    
def render_template(template: str, context: Mapping[str, Any]) -> str:
    """Render template with substitutions."""
```

**Features**:
- ✅ Search multiple directories
- ✅ Engine-specific templates (e.g., deploy-sqlite.tmpl)
- ✅ Generic templates (deploy.tmpl)
- ✅ Built-in defaults
- ✅ Variable substitution

**Template Locations Searched**:
1. Project root
2. Project root / sqitch/
3. User config dir (~/.sqitch/)
4. /etc/sqlitch/
5. /etc/sqitch/

**Template Variables**:
- `{project}` - Project name
- `{change}` - Change name
- `{engine}` - Engine name
- `{timestamp}` - Current timestamp

**Default Templates**:
```
-- Deploy {project}:{change} to {engine}

BEGIN;

-- XXX Add DDLs here.

COMMIT;
```

---

## 8. Testing Infrastructure

### Location
- **Contract Tests**: `tests/cli/commands/test_*_contract.py`
- **Fixtures**: `tests/conftest.py`, `tests/support/`
- **Helpers**: `tests/cli/commands/conftest.py`

### Capabilities (Excellent Foundation)

#### 8.1 Temporary Directory Fixtures
```python
@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create temporary project directory."""
    
@pytest.fixture
def tmp_plan(tmp_path: Path) -> Path:
    """Create temporary plan file."""
```

#### 8.2 Mock Environment
```python
@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Provide controlled environment variables."""
```

#### 8.3 CLI Runner
```python
from click.testing import CliRunner

runner = CliRunner()
result = runner.invoke(command, args, env=env)
assert result.exit_code == 0
```

### Testing Strategy for Feature 004

**Unit Tests** (per command):
- Test command options parsing
- Test validation logic
- Test error handling
- Mock file/database operations

**Integration Tests** (end-to-end):
- Create real temp directories
- Create real SQLite databases
- Execute full workflows
- Verify file and database state

**Tutorial Validation Tests**:
- Run each quickstart scenario
- Assert file contents
- Assert database state
- Compare outputs to expected

**Example Test Structure**:
```python
def test_deploy_first_change(tmp_path: Path):
    """Test deploying first change creates registry and executes script."""
    # Setup: create project, plan, scripts
    init_project(tmp_path, "flipr", "sqlite")
    add_change(tmp_path, "users", deploy_sql="CREATE TABLE users (...)")
    
    # Execute: deploy
    result = deploy(tmp_path, target="db:sqlite:test.db")
    
    # Assert: success
    assert result.exit_code == 0
    assert "users .. ok" in result.output
    
    # Assert: database state
    conn = sqlite3.connect(tmp_path / "test.db")
    assert table_exists(conn, "users")
    
    # Assert: registry state
    reg_conn = sqlite3.connect(tmp_path / "sqitch.db")
    changes = reg_conn.execute("SELECT change FROM changes").fetchall()
    assert ("users",) in changes
```

---

## 9. Implementation Effort Estimates

Based on code analysis and tutorial requirements:

### Easy (1-2 days each)
- **config command** (get/set only) - 1 day
  - 200 lines implementation
  - 100 lines tests
  - Config file I/O with configparser

- **status command** - 1-2 days
  - 300 lines implementation
  - 150 lines tests
  - SQL queries + formatting

- **log command** - 1-2 days
  - 250 lines implementation
  - 150 lines tests
  - SQL queries + formatting

### Medium (3-4 days each)
- **deploy command** - 3-4 days
  - 500 lines implementation
  - 300 lines tests
  - Registry creation, script execution, transaction management
  - Most complex command

- **verify command** - 2-3 days
  - 250 lines implementation
  - 200 lines tests
  - Script execution, error handling

- **revert command** - 3 days
  - 400 lines implementation
  - 250 lines tests
  - Dependency checking, reverse order execution

### Complex (4-5 days each)
- **tag command** - 2-3 days
  - 300 lines implementation
  - 200 lines tests
  - Plan manipulation, registry updates

- **rework command** - 4-5 days
  - 400 lines implementation
  - 300 lines tests
  - Complex plan manipulation, file copying with @tag suffixes

### Total Estimated Effort
- **Implementation**: 15-20 days
- **Testing**: 10-12 days
- **Integration & Polish**: 3-5 days
- **Total**: 28-37 days (4-5 weeks)

---

## 10. Key Technical Decisions

### 10.1 Registry Database Location
**Decision**: Use sibling `sqitch.db` file (following Sqitch behavior)

**Rationale**:
- Matches Perl Sqitch exactly
- Already implemented in `sqlitch/engine/sqlite.py`
- Enables ATTACH DATABASE for shared transactions

**Implementation**: `derive_sqlite_registry_uri()` in sqlite.py

### 10.2 Transaction Management
**Decision**: Auto-wrap deploy/revert scripts UNLESS they manage their own transactions

**Rationale**:
- Matches Sqitch FR-022a requirement
- Handles both simple and complex scripts
- Provides atomicity by default

**Implementation**: Use `script_manages_transactions()` to detect, wrap in BEGIN/COMMIT if False

### 10.3 Script Execution Model
**Decision**: Execute scripts directly via sqlite3.Connection.executescript()

**Rationale**:
- Native SQLite support
- Handles multi-statement scripts
- Simple error handling

**Alternative Considered**: Call sqlite3 CLI - rejected (adds complexity, harder to test)

### 10.4 Dependency Validation
**Decision**: Check dependencies at deploy time, not add time

**Rationale**:
- Matches Sqitch behavior
- Allows adding changes in any order
- Validates at execution when state matters

**Implementation**: Query `changes` table for required dependencies before deploying each change

### 10.5 Change ID Generation
**Decision**: Use change name + project name + timestamp for change_id

**Rationale**:
- Matches Sqitch behavior (uses SHA1 hash)
- Globally unique
- Stable across deployments

**Implementation**:
```python
import hashlib
from uuid import UUID

def generate_change_id(project: str, change: str, timestamp: datetime) -> str:
    content = f"{project} {change} {timestamp.isoformat()}"
    return hashlib.sha1(content.encode()).hexdigest()
```

### 10.6 Planner Identity Resolution
**Decision**: Use environment variables with fallbacks

**Order**:
1. `SQLITCH_USER_NAME` / `SQLITCH_USER_EMAIL`
2. `GIT_AUTHOR_NAME` / `GIT_AUTHOR_EMAIL`
3. Config file: `user.name` / `user.email`
4. System `USER` / `USERNAME`

**Already Implemented**: `_resolve_planner()` in add.py

### 10.7 Script File Naming
**Decision**: Use slugified change names (underscores replace colons/spaces)

**Example**: `core:init` → `core_init.sql`

**Already Implemented**: `slugify_change_name()` in plan/utils.py

### 10.8 Error Handling Strategy
**Decision**: Fail fast with clear error messages

**Patterns**:
- Validation errors: Exit code 2 (parsing error)
- Deploy failures: Exit code 1, INSERT fail event into registry
- Missing dependencies: Exit code 1 before execution
- Script errors: Exit code 1, rollback transaction, INSERT fail event

---

## 11. Risk Analysis

### High Risk
**Deploy Script Execution**
- **Risk**: Scripts may have syntax errors or destructive operations
- **Mitigation**: 
  - Transaction wrapping (auto-rollback on error)
  - Verify scripts test deployments without mutations
  - Clear error messages with line numbers

**Registry Corruption**
- **Risk**: Partial updates if crashes mid-deploy
- **Mitigation**:
  - All registry operations in same transaction as deploy
  - Atomic INSERT/DELETE operations
  - Events table captures failures

### Medium Risk
**Dependency Resolution**
- **Risk**: Complex dependency graphs may have cycles
- **Mitigation**:
  - Simple depth-first validation at deploy time
  - Sqitch doesn't detect cycles either (by design)
  - Document that circular dependencies fail at runtime

**File Path Resolution**
- **Risk**: Relative vs absolute paths, symlinks, etc.
- **Mitigation**:
  - Already handled by existing utilities
  - Test cross-platform (Windows, macOS, Linux)

### Low Risk
**Config File Corruption**
- **Risk**: Invalid INI syntax breaks config loading
- **Mitigation**:
  - configparser handles this gracefully
  - Validate on write
  - Clear error messages

**Template Rendering**
- **Risk**: Missing variables cause template errors
- **Mitigation**:
  - Default values for all variables
  - Already implemented in templates.py

---

## 12. Dependencies & Prerequisites

### Hard Dependencies
- ✅ Python 3.11
- ✅ Click 8.1+
- ✅ sqlite3 (stdlib)
- ✅ configparser (stdlib)

### Soft Dependencies
- Git (for planner identity fallback) - optional
- sqlite3 CLI tool (for manual inspection) - optional

### Internal Dependencies
- ✅ `sqlitch/registry/migrations.py` - registry schema
- ✅ `sqlitch/plan/parser.py` - plan file parsing
- ✅ `sqlitch/plan/formatter.py` - plan file writing
- ✅ `sqlitch/config/loader.py` - config file loading
- ✅ `sqlitch/engine/sqlite.py` - SQLite operations
- ✅ `sqlitch/cli/commands/_context.py` - CLI context
- ✅ `sqlitch/utils/templates.py` - template rendering

**All internal dependencies are complete and tested.**

---

## 13. Questions & Open Issues

### Resolved
- ✅ How to handle registry database creation? → Use migrations.py
- ✅ Where to place registry database? → Sibling sqitch.db file
- ✅ How to execute SQL scripts? → sqlite3.executescript()
- ✅ How to detect transaction-managed scripts? → script_manages_transactions()
- ✅ How to generate change IDs? → SHA1 hash (like Sqitch)

### Remaining
- ❓ Should we support `:memory:` databases in tutorial? → Probably not (registry needs filesystem)
- ❓ How to handle concurrent deployments? → Document as unsupported (like Sqitch)
- ❓ Should verify scripts run in transactions? → Yes, for consistency (rollback on error)
- ❓ How verbose should default output be? → Match Sqitch exactly

---

## 14. Next Steps

1. **Create data-model.md** → Define all data structures needed
2. **Create plan.md** → Break down implementation into phases
3. **Create tasks.md** → Generate detailed task list with TDD workflow
4. **Start Implementation** → Begin with config command (simplest)

---

## 15. Summary

**Foundation Assessment**: 🟢 Excellent

The SQLitch codebase has a solid foundation:
- Registry schema is complete
- Plan parsing/writing is complete
- Config loading is complete
- Command infrastructure is complete
- SQLite engine adapter is 95% complete
- Two commands (init, add) are 80% complete

**Implementation Scope**: 🟡 Medium

We need to implement 8 commands' business logic:
- 2 easy commands (config, status, log) - ~5 days
- 3 medium commands (deploy, verify, revert) - ~10 days
- 2 complex commands (tag, rework) - ~7 days
- Integration testing - ~5 days

**Confidence Level**: 🟢 High

The tutorial requirements are well-understood, the existing code is high-quality, and the patterns are consistent. The main work is implementing the command-specific logic that ties everything together.

**Estimated Timeline**: 4-5 weeks

**Ready to Proceed**: ✅ Yes

All research questions are answered. Ready to move to data model definition.

