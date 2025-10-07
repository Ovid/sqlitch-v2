# Data Model: SQLite Tutorial Parity

**Feature**: 004-sqlitch-tutorial-parity  
**Date**: October 6, 2025  
**Status**: Complete

---

## Overview

This document defines all data structures, relationships, and validation rules needed for Feature 004. Models are organized by domain:

1. **Project Domain** - Project metadata and configuration
2. **Plan Domain** - Changes, tags, dependencies (EXISTING - from plan/model.py)
3. **Registry Domain** - Database deployment state (EXISTING - from registry tables)
4. **Command Domain** - Command execution context and results
5. **Script Domain** - Script content and execution

---

## 1. Project Domain

### 1.1 Project Configuration

**Existing**: Loaded via `ConfigProfile` in config/loader.py

```python
@dataclass(frozen=True)
class ConfigProfile:
    """Materialized configuration data and metadata."""
    root_dir: Path
    files: tuple[Path, ...]
    settings: Mapping[str, Mapping[str, str]]
    active_engine: str | None
```

**Usage**: All commands use this via `CLIContext.config`

**Validation Rules**:
- root_dir MUST be an existing directory
- files MUST be readable
- settings MAY be empty (no config files found)
- active_engine SHOULD be present (from [core] engine)

### 1.2 Project Metadata

**NEW**: Extracted from plan pragmas and config

```python
@dataclass(frozen=True, slots=True)
class ProjectMetadata:
    """Project identification and settings."""
    
    name: str
    uri: str | None
    engine: str
    plan_file: Path
    top_dir: Path
    deploy_dir: Path
    revert_dir: Path
    verify_dir: Path
    
    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Project name is required")
        if not self.engine:
            raise ValueError("Project engine is required")
        # Validate directories exist
        for dir_path in (self.top_dir, self.deploy_dir, self.revert_dir, self.verify_dir):
            if not dir_path.is_dir():
                raise ValueError(f"Directory {dir_path} does not exist")
    
    @classmethod
    def from_plan_and_config(
        cls,
        plan: Plan,
        config: ConfigProfile,
        plan_file: Path,
    ) -> ProjectMetadata:
        """Create from existing plan and config."""
        top_dir = config.root_dir / config.settings.get("core", {}).get("top_dir", ".")
        return cls(
            name=plan.project_name,
            uri=plan.uri,
            engine=plan.default_engine,
            plan_file=plan_file,
            top_dir=top_dir,
            deploy_dir=top_dir / "deploy",
            revert_dir=top_dir / "revert",
            verify_dir=top_dir / "verify",
        )
```

**Usage**: 
- Passed to all command implementations
- Provides consistent access to project paths
- Validates project structure

---

## 2. Plan Domain (EXISTING)

### 2.1 Change Model

**Location**: `sqlitch/plan/model.py`

```python
@dataclass(frozen=True, slots=True)
class Change:
    """Represents a deployable change entry within a plan."""
    
    name: str
    script_paths: Mapping[str, Path | str | None]
    planner: str
    planned_at: datetime
    notes: str | None = None
    change_id: UUID | None = None
    dependencies: Sequence[str] = field(default_factory=tuple)
    tags: Sequence[str] = field(default_factory=tuple)
```

**Relationships**:
- `dependencies` references other Change.name values
- `tags` references Tag.name values
- `script_paths` maps kind → Path ("deploy", "revert", "verify")

**Validation** (existing in __post_init__):
- name MUST NOT be empty
- planner MUST NOT be empty
- planned_at MUST be timezone-aware
- dependencies MUST be tuple (immutable)
- tags MUST be tuple (immutable)

**Additional Validation Needed**:
- name SHOULD match pattern: `[a-z0-9_]+`
- script_paths SHOULD contain "deploy", "revert", "verify" keys

### 2.2 Tag Model

**Location**: `sqlitch/plan/model.py`

```python
@dataclass(frozen=True, slots=True)
class Tag:
    """Represents a tag entry within a plan."""
    
    name: str
    change_ref: str
    planner: str
    tagged_at: datetime
    note: str | None = None
```

**Relationships**:
- `change_ref` references the last Change.name before this tag

**Validation** (existing):
- name MUST NOT be empty
- change_ref MUST NOT be empty
- planner MUST NOT be empty
- tagged_at MUST be timezone-aware

**Additional Validation Needed**:
- name SHOULD start with 'v' (convention for version tags)
- name MUST NOT contain whitespace

### 2.3 Plan Model

**Location**: `sqlitch/plan/model.py`

```python
@dataclass(frozen=True, slots=True)
class Plan:
    """Represents a complete deployment plan."""
    
    project_name: str
    file_path: Path
    entries: tuple[PlanEntry, ...]
    checksum: str
    default_engine: str
    syntax_version: str = "1.0.0"
    uri: str | None = None
```

**Relationships**:
- `entries` contains Change and Tag objects
- Maintains insertion order

**Validation** (existing):
- project_name MUST NOT be empty
- default_engine MUST NOT be empty
- entries MUST be tuple (immutable)

**Methods Needed**:
```python
def get_changes(self) -> list[Change]:
    """Return all Change entries in order."""
    return [e for e in self.entries if isinstance(e, Change)]

def get_tags(self) -> list[Tag]:
    """Return all Tag entries in order."""
    return [e for e in self.entries if isinstance(e, Tag)]

def find_change(self, name: str) -> Change | None:
    """Find change by name."""
    for entry in self.entries:
        if isinstance(entry, Change) and entry.name == name:
            return entry
    return None

def find_tag(self, name: str) -> Tag | None:
    """Find tag by name."""
    for entry in self.entries:
        if isinstance(entry, Tag) and entry.name == name:
            return entry
    return None

def changes_since_tag(self, tag_name: str) -> list[Change]:
    """Return changes added since a specific tag."""
    changes: list[Change] = []
    found_tag = False
    for entry in self.entries:
        if isinstance(entry, Tag) and entry.name == tag_name:
            found_tag = True
            changes.clear()
        elif isinstance(entry, Change) and found_tag:
            changes.append(entry)
    return changes
```

---

## 3. Registry Domain

### 3.1 Deployed Change Record

**NEW**: Represents a change in the registry database

```python
@dataclass(frozen=True, slots=True)
class DeployedChange:
    """Represents a change currently deployed to the database."""
    
    change_id: str
    script_hash: str | None
    change: str  # change name
    project: str
    note: str
    committed_at: datetime
    committer_name: str
    committer_email: str
    planned_at: datetime
    planner_name: str
    planner_email: str
    
    @classmethod
    def from_registry_row(cls, row: tuple) -> DeployedChange:
        """Create from database row."""
        return cls(
            change_id=row[0],
            script_hash=row[1],
            change=row[2],
            project=row[3],
            note=row[4],
            committed_at=parse_iso_datetime(row[5]),
            committer_name=row[6],
            committer_email=row[7],
            planned_at=parse_iso_datetime(row[8]),
            planner_name=row[9],
            planner_email=row[10],
        )
```

**Usage**: 
- Query from `changes` table
- Compare with plan to determine deployed/pending state
- Used by status, deploy, revert commands

### 3.2 Deployment Event

**NEW**: Represents an event in the registry

```python
@dataclass(frozen=True, slots=True)
class DeploymentEvent:
    """Represents a deployment event in the registry."""
    
    event: str  # 'deploy', 'revert', 'fail', 'merge'
    change_id: str
    change: str
    project: str
    note: str
    requires: str  # comma-separated list
    conflicts: str  # comma-separated list
    tags: str  # comma-separated list
    committed_at: datetime
    committer_name: str
    committer_email: str
    planned_at: datetime
    planner_name: str
    planner_email: str
    
    @classmethod
    def from_registry_row(cls, row: tuple) -> DeploymentEvent:
        """Create from database row."""
        return cls(
            event=row[0],
            change_id=row[1],
            change=row[2],
            project=row[3],
            note=row[4],
            requires=row[5],
            conflicts=row[6],
            tags=row[7],
            committed_at=parse_iso_datetime(row[8]),
            committer_name=row[9],
            committer_email=row[10],
            planned_at=parse_iso_datetime(row[11]),
            planner_name=row[12],
            planner_email=row[13],
        )
```

**Usage**:
- Query from `events` table
- Displayed by log command
- Audit trail for all operations

### 3.3 Deployment Status

**NEW**: Summary of deployment state

```python
@dataclass(frozen=True, slots=True)
class DeploymentStatus:
    """Summary of database deployment state."""
    
    project: str
    deployed_changes: tuple[DeployedChange, ...]
    pending_changes: tuple[Change, ...]
    deployed_tags: tuple[str, ...]
    last_deployed_change: DeployedChange | None
    
    @property
    def is_up_to_date(self) -> bool:
        """Check if all changes are deployed."""
        return len(self.pending_changes) == 0
    
    @property
    def deployment_count(self) -> int:
        """Number of deployed changes."""
        return len(self.deployed_changes)
```

**Usage**:
- Returned by status command
- Used to determine what deploy/revert should do

---

## 4. Command Domain

### 4.1 Command Context

**EXISTING**: `CLIContext` in cli/commands/_context.py

```python
@dataclass
class CLIContext:
    """Runtime context for CLI commands."""
    
    project_root: Path
    quiet: bool
    verbose: int
    env: Mapping[str, str]
    config: ConfigProfile
    engine: str | None
    target: str | None
    plan_file: Path | None
```

**Usage**: Available via `require_cli_context(ctx)` in all commands

### 4.2 Command Result

**NEW**: Standardized command result

```python
@dataclass(frozen=True, slots=True)
class CommandResult:
    """Result of command execution."""
    
    success: bool
    message: str
    exit_code: int = 0
    data: Mapping[str, Any] | None = None
    
    @classmethod
    def ok(cls, message: str, data: Mapping[str, Any] | None = None) -> CommandResult:
        """Create success result."""
        return cls(success=True, message=message, exit_code=0, data=data)
    
    @classmethod
    def error(
        cls,
        message: str,
        exit_code: int = 1,
        data: Mapping[str, Any] | None = None,
    ) -> CommandResult:
        """Create error result."""
        return cls(success=False, message=message, exit_code=exit_code, data=data)
```

**Usage**:
- Return value from command implementations
- Enables consistent error handling
- Provides structured data for JSON mode

### 4.3 Deploy Options

**NEW**: Options for deploy command

```python
@dataclass(frozen=True, slots=True)
class DeployOptions:
    """Options for deploy command."""
    
    target: str
    to_change: str | None = None
    to_tag: str | None = None
    mode: str = "all"  # 'all', 'change', 'tag'
    log_only: bool = False
    verify: bool = True
    
    def __post_init__(self) -> None:
        if self.to_change and self.to_tag:
            raise ValueError("Cannot specify both --to-change and --to-tag")
        if self.mode not in ("all", "change", "tag"):
            raise ValueError(f"Invalid mode: {self.mode}")
```

### 4.4 Revert Options

**NEW**: Options for revert command

```python
@dataclass(frozen=True, slots=True)
class RevertOptions:
    """Options for revert command."""
    
    target: str
    to_change: str | None = None
    to_tag: str | None = None
    
    def __post_init__(self) -> None:
        if not self.to_change and not self.to_tag:
            raise ValueError("Must specify either --to-change or --to-tag for revert")
```

---

## 5. Script Domain

### 5.1 Script Content

**NEW**: Represents a SQL script file

```python
@dataclass(frozen=True, slots=True)
class Script:
    """Represents a SQL script file."""
    
    kind: str  # 'deploy', 'revert', 'verify'
    path: Path
    content: str
    manages_transactions: bool
    
    @classmethod
    def load(cls, kind: str, path: Path) -> Script:
        """Load script from file."""
        if not path.exists():
            raise FileNotFoundError(f"Script {path} does not exist")
        
        content = path.read_text(encoding="utf-8")
        manages_tx = script_manages_transactions(content)
        
        return cls(
            kind=kind,
            path=path,
            content=content,
            manages_transactions=manages_tx,
        )
    
    def get_statements(self) -> list[str]:
        """Extract SQL statements from script."""
        return extract_sqlite_statements(self.content)
```

**Usage**:
- Loaded before execution
- Analyzed for transaction management
- Executed by deploy/revert/verify commands

### 5.2 Script Execution Result

**NEW**: Result of script execution

```python
@dataclass(frozen=True, slots=True)
class ScriptResult:
    """Result of executing a SQL script."""
    
    script: Script
    success: bool
    error_message: str | None = None
    execution_time: float | None = None
    
    @classmethod
    def ok(cls, script: Script, execution_time: float) -> ScriptResult:
        """Create success result."""
        return cls(
            script=script,
            success=True,
            execution_time=execution_time,
        )
    
    @classmethod
    def error(cls, script: Script, error_message: str) -> ScriptResult:
        """Create error result."""
        return cls(
            script=script,
            success=False,
            error_message=error_message,
        )
```

---

## 6. Identity and Timestamps

### 6.1 User Identity

**Status**: ✅ Implemented (2025-10-06)

**Implementation**: Function `_resolve_committer_identity()` in `sqlitch/cli/commands/deploy.py`

```python
def _resolve_committer_identity(
    env: Mapping[str, str],
    config_root: Path,
    project_root: Path,
) -> tuple[str, str]:
    """Resolve the committer name and email from config and environment variables.
    
    Resolution order:
    1. Config file (user.name and user.email)
    2. Environment variables (SQLITCH_USER_*, GIT_*, etc.)
    3. System defaults
    
    Returns:
        Tuple of (name, email)
    """
    from sqlitch.config.resolver import resolve_config
    
    # Try to load config to get user.name and user.email
    config_name = None
    config_email = None
    try:
        config = resolve_config(
            root_dir=project_root,
            config_root=config_root,
            env=env,
        )
        user_section = config.settings.get("user", {})
        config_name = user_section.get("name")
        config_email = user_section.get("email")
    except Exception:
        pass

    name = (
        config_name
        or env.get("SQLITCH_USER_NAME")
        or env.get("GIT_COMMITTER_NAME")
        or env.get("GIT_AUTHOR_NAME")
        or env.get("USER")
        or env.get("USERNAME")
        or "SQLitch User"
    )

    email = (
        config_email
        or env.get("SQLITCH_USER_EMAIL")
        or env.get("GIT_COMMITTER_EMAIL")
        or env.get("GIT_AUTHOR_EMAIL")
        or env.get("EMAIL")
    )

    if not email:
        sanitized = "".join(ch for ch in name.lower() if ch.isalnum() or ch in {".", "_"})
        sanitized = sanitized or "sqlitch"
        email = f"{sanitized}@example.invalid"

    return name, email
```

**Resolution Priority**:
1. **Config file** `[user]` section:
   - `user.name` - Full name (e.g., "Marge N. O'Vera")
   - `user.email` - Email address (e.g., "marge@example.com")
   - Config precedence: local → user → system
   
2. **Environment variables**:
   - `SQLITCH_USER_NAME` / `SQLITCH_USER_EMAIL` (SQLitch-specific)
   - `GIT_COMMITTER_NAME` / `GIT_COMMITTER_EMAIL` (Git committer)
   - `GIT_AUTHOR_NAME` / `GIT_AUTHOR_EMAIL` (Git author)
   - `USER` / `USERNAME` (system username)
   - `EMAIL` (system email)

3. **Generated fallback**:
   - Name: "SQLitch User"
   - Email: Sanitized username + "@example.invalid"

**Config File Format**:
```ini
[user]
    name = Test User
    email = test@example.com
```

**Usage**:
- Called by deploy command before recording to registry
- Identity stored in `events.committer_name` and `events.committer_email`
- Displayed in `sqlitch status` and `sqlitch log` outputs

**Test Coverage**:
- `tests/cli/commands/test_deploy_functional.py::TestDeployUserIdentity`
- `test_uses_user_identity_from_config_file` - verifies config file reading
- `test_falls_back_to_env_when_no_config` - verifies environment fallback

### 6.2 Change Identifier

**NEW**: Generate unique change IDs

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
    """Generate unique change ID using Git-style SHA1 hash.
    
    Matches Sqitch behavior: Git object format hash.
    Sqitch uses Git's object format: 'change <length>\0<content>'
    where content is the change info string.
    """
    from sqlitch.utils.time import isoformat_utc
    
    # Format timestamp in Sqitch format (ISO 8601 with Z suffix)
    timestamp_str = isoformat_utc(timestamp, drop_microseconds=True, use_z_suffix=True)
    
    # Build info string in Sqitch's format
    info_parts = [
        f"project {project}",
        f"change {change}",
        f"planner {planner_name} <{planner_email}>",
        f"date {timestamp_str}",
    ]
    
    # Add requires/conflicts if present
    if requires:
        info_parts.append("requires")
        for req in requires:
            info_parts.append(f"  + {req}")
    
    if conflicts:
        info_parts.append("conflicts")
        for conf in conflicts:
            info_parts.append(f"  - {conf}")
    
    # Add note if present (empty line before note)
    if note:
        info_parts.append("")
        info_parts.append(note)
    
    info = "\n".join(info_parts)
    
    # Use Git's object format: 'change <length>\0<content>'
    import hashlib
    info_bytes = info.encode("utf-8")
    git_object = f"change {len(info_bytes)}\x00".encode("utf-8") + info_bytes
    
    return hashlib.sha1(git_object).hexdigest()
```

**Usage**:
- Generate when adding change to plan
- Store in registry `changes` table
- Used as primary key in registry

---

## 7. Validation Rules

### 7.1 Change Name Validation

```python
def validate_change_name(name: str) -> None:
    """Validate change name follows conventions."""
    if not name:
        raise ValueError("Change name cannot be empty")
    
    if " " in name or "\t" in name:
        raise ValueError("Change name cannot contain whitespace")
    
    # Allow alphanumeric, underscore, colon, slash
    import re
    if not re.match(r"^[a-zA-Z0-9_:/-]+$", name):
        raise ValueError(
            "Change name must contain only letters, numbers, "
            "underscores, colons, slashes, or hyphens"
        )
```

### 7.2 Dependency Validation

```python
def validate_dependencies(
    change: Change,
    plan: Plan,
    deployed_changes: Sequence[DeployedChange],
) -> None:
    """Validate change dependencies are satisfied.
    
    Raises:
        ValueError: If required dependencies are not deployed
    """
    for required in change.dependencies:
        # Check if required change is deployed
        is_deployed = any(
            dc.change == required for dc in deployed_changes
        )
        if not is_deployed:
            raise ValueError(
                f"Change '{change.name}' requires '{required}', "
                f"but it is not deployed"
            )
```

### 7.3 Tag Name Validation

```python
def validate_tag_name(name: str) -> None:
    """Validate tag name follows conventions."""
    if not name:
        raise ValueError("Tag name cannot be empty")
    
    if name.startswith("@"):
        raise ValueError("Tag name should not start with '@' (added automatically)")
    
    if " " in name or "\t" in name:
        raise ValueError("Tag name cannot contain whitespace")
```

---

## 8. Data Flow Diagrams

### 8.1 Deploy Flow

```
Plan File (sqitch.plan)
    ↓ parse_plan()
Plan (with Change entries)
    ↓ compare with registry
Pending Changes (list[Change])
    ↓ for each change
Load Scripts (deploy, verify)
    ↓ execute deploy
Database Updated
    ↓ insert into registry
Registry Updated (changes, dependencies, events)
    ↓ execute verify (optional)
Verification Result
```

### 8.2 Status Flow

```
Registry Database (changes table)
    ↓ SELECT all changes
Deployed Changes (list[DeployedChange])
    ↓
Plan File (sqitch.plan)
    ↓ parse_plan()
Plan Changes (list[Change])
    ↓ compare lists
Deployment Status (deployed + pending)
    ↓ format output
Status Display
```

### 8.3 Add Flow

```
User Input (change name, dependencies, note)
    ↓ validate
Change Object
    ↓
Plan File (existing)
    ↓ parse_plan()
Plan Object
    ↓ append change
Updated Plan
    ↓ write_plan()
Updated Plan File
    ↓
Generate Scripts (from templates)
    ↓ write files
Script Files (deploy, revert, verify)
```

---

## 9. Database Schema Reference

### 9.1 Registry Tables

**changes** (current deployment state):
- change_id (PK) - SHA1 hash
- script_hash - Script content hash
- change - Change name
- project - Project name (FK)
- note - Description
- committed_at - When deployed
- committer_name, committer_email - Who deployed
- planned_at - When added to plan
- planner_name, planner_email - Who planned

**dependencies** (satisfied dependencies):
- change_id (PK, FK) - Depending change
- type (PK) - 'require' or 'conflict'
- dependency (PK) - Dependency name
- dependency_id (FK) - Resolved change_id (NULL for conflicts)

**events** (audit log):
- event (PK) - 'deploy', 'revert', 'fail', 'merge'
- change_id (PK) - Change ID
- change - Change name
- project - Project name (FK)
- note - Description
- requires - Comma-separated list
- conflicts - Comma-separated list
- tags - Comma-separated list
- committed_at (PK) - Timestamp
- committer_name, committer_email - Who committed
- planned_at - When planned
- planner_name, planner_email - Who planned

**projects** (project registry):
- project (PK) - Project name
- uri - Project URI (unique)
- created_at - When first deployed
- creator_name, creator_email - Who created

**tags** (applied tags):
- tag_id (PK) - UUID
- tag - Tag name
- project (FK) - Project name
- change_id (FK) - Last change before tag
- note - Description
- committed_at - When tagged
- committer_name, committer_email - Who tagged
- planned_at - When added to plan
- planner_name, planner_email - Who planned

**releases** (registry schema versions):
- version (PK) - Schema version (1.1)
- installed_at - When created
- installer_name, installer_email - Who created

---

## 10. Summary

### Existing Models (Ready to Use)
- ✅ `Change` - Plan change entry
- ✅ `Tag` - Plan tag entry
- ✅ `Plan` - Complete plan
- ✅ `ConfigProfile` - Configuration data
- ✅ `CLIContext` - Command context

### New Models Needed
- 📝 `ProjectMetadata` - Project paths and settings
- 📝 `DeployedChange` - Registry change record
- 📝 `DeploymentEvent` - Registry event record
- 📝 `DeploymentStatus` - Status summary
- 📝 `CommandResult` - Standardized results
- 📝 `DeployOptions` - Deploy command options
- 📝 `RevertOptions` - Revert command options
- 📝 `Script` - Script file representation
- 📝 `ScriptResult` - Script execution result
- 📝 `UserIdentity` - User name and email

### Helper Functions Needed
- 📝 `generate_change_id()` - SHA1 hash generation
- 📝 `validate_change_name()` - Name validation
- 📝 `validate_dependencies()` - Dependency validation
- 📝 `validate_tag_name()` - Tag name validation

### Implementation Notes
1. Add new models to appropriate modules:
   - Registry models → `sqlitch/registry/state.py` (NEW)
   - Command models → `sqlitch/cli/commands/_models.py` (NEW)
   - Script models → `sqlitch/engine/scripts.py` (NEW)

2. Extend existing models with helper methods:
   - `Plan.get_changes()`, `Plan.find_change()`, etc.
   - Add to `sqlitch/plan/model.py`

3. All dataclasses should be frozen and use slots
4. All datetime fields must be timezone-aware
5. All sequences should be tuples (immutable)
6. Use `MappingProxyType` for exposed dictionaries

**Ready for plan.md creation.**

