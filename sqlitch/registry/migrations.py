"""Registry schema migrations aligned with Sqitch reference SQL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

LATEST_REGISTRY_VERSION = "1.1"


@dataclass(frozen=True, slots=True)
class RegistryMigration:
    """Represents a registry migration SQL script for a specific target version."""

    target_version: str
    sql: str
    is_baseline: bool = False
    source: str | None = None


_SQLITE_BASELINE = """BEGIN;

CREATE TABLE releases (
    version         FLOAT       PRIMARY KEY,
    installed_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    installer_name  TEXT        NOT NULL,
    installer_email TEXT        NOT NULL
);

CREATE TABLE projects (
    project         TEXT        PRIMARY KEY,
    uri             TEXT            NULL UNIQUE,
    created_at      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator_name    TEXT        NOT NULL,
    creator_email   TEXT        NOT NULL
);

CREATE TABLE changes (
    change_id       TEXT        PRIMARY KEY,
    script_hash     TEXT            NULL,
    change          TEXT        NOT NULL,
    project         TEXT        NOT NULL REFERENCES projects(project) ON UPDATE CASCADE,
    note            TEXT        NOT NULL DEFAULT '',
    committed_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    committer_name  TEXT        NOT NULL,
    committer_email TEXT        NOT NULL,
    planned_at      DATETIME    NOT NULL,
    planner_name    TEXT        NOT NULL,
    planner_email   TEXT        NOT NULL,
    UNIQUE(project, script_hash)
);

CREATE TABLE tags (
    tag_id          TEXT        PRIMARY KEY,
    tag             TEXT        NOT NULL,
    project         TEXT        NOT NULL REFERENCES projects(project) ON UPDATE CASCADE,
    change_id       TEXT        NOT NULL REFERENCES changes(change_id) ON UPDATE CASCADE,
    note            TEXT        NOT NULL DEFAULT '',
    committed_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    committer_name  TEXT        NOT NULL,
    committer_email TEXT        NOT NULL,
    planned_at      DATETIME    NOT NULL,
    planner_name    TEXT        NOT NULL,
    planner_email   TEXT        NOT NULL,
    UNIQUE(project, tag)
);

CREATE TABLE dependencies (
    change_id       TEXT        NOT NULL REFERENCES changes(change_id) ON UPDATE CASCADE ON DELETE CASCADE,
    type            TEXT        NOT NULL,
    dependency      TEXT        NOT NULL,
    dependency_id   TEXT            NULL REFERENCES changes(change_id) ON UPDATE CASCADE
                                         CONSTRAINT dependencies_check CHECK (
            (type = 'require'  AND dependency_id IS NOT NULL)
         OR (type = 'conflict' AND dependency_id IS NULL)
    ),
    PRIMARY KEY (change_id, dependency)
);

CREATE TABLE events (
    event           TEXT        NOT NULL CONSTRAINT events_event_check CHECK (
        event IN ('deploy', 'revert', 'fail', 'merge')
    ),
    change_id       TEXT        NOT NULL,
    change          TEXT        NOT NULL,
    project         TEXT        NOT NULL REFERENCES projects(project) ON UPDATE CASCADE,
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

COMMIT;
"""

_SQLITE_UPGRADE_1_0 = """BEGIN;

CREATE TABLE releases (
    version         FLOAT       PRIMARY KEY,
    installed_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    installer_name  TEXT        NOT NULL,
    installer_email TEXT        NOT NULL
);

-- Create a new changes table with script_hash.
CREATE TABLE new_changes (
    change_id       TEXT        PRIMARY KEY,
    script_hash     TEXT            NULL UNIQUE,
    change          TEXT        NOT NULL,
    project         TEXT        NOT NULL REFERENCES projects(project) ON UPDATE CASCADE,
    note            TEXT        NOT NULL DEFAULT '',
    committed_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    committer_name  TEXT        NOT NULL,
    committer_email TEXT        NOT NULL,
    planned_at      DATETIME    NOT NULL,
    planner_name    TEXT        NOT NULL,
    planner_email   TEXT        NOT NULL
);

-- Copy all the data to the new table and move it into place.
INSERT INTO new_changes
SELECT change_id, change_id, change, project, note,
       committed_at, committer_name, committer_email,
       planned_at, planner_name, planner_email
  FROM changes;
PRAGMA foreign_keys = OFF;
DROP TABLE changes;
ALTER TABLE new_changes RENAME TO changes;
PRAGMA foreign_keys = ON;

-- Create a new events table with support for "merge" events.
CREATE TABLE new_events (
    event           TEXT        NOT NULL CHECK (event IN ('deploy', 'revert', 'fail', 'merge')),
    change_id       TEXT        NOT NULL,
    change          TEXT        NOT NULL,
    project         TEXT        NOT NULL REFERENCES projects(project) ON UPDATE CASCADE,
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

INSERT INTO new_events
SELECT * FROM events;
PRAGMA foreign_keys = OFF;
DROP TABLE events;
ALTER TABLE new_events RENAME TO events;
PRAGMA foreign_keys = ON;

COMMIT;
"""

_SQLITE_UPGRADE_1_1 = """BEGIN;

-- Create a new changes table with updated unique constraint.
CREATE TABLE new_changes (
    change_id       TEXT        PRIMARY KEY,
    script_hash     TEXT            NULL,
    change          TEXT        NOT NULL,
    project         TEXT        NOT NULL REFERENCES projects(project) ON UPDATE CASCADE,
    note            TEXT        NOT NULL DEFAULT '',
    committed_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    committer_name  TEXT        NOT NULL,
    committer_email TEXT        NOT NULL,
    planned_at      DATETIME    NOT NULL,
    planner_name    TEXT        NOT NULL,
    planner_email   TEXT        NOT NULL,
    UNIQUE(project, script_hash)
);

-- Copy all the data to the new table and move it into place.
INSERT INTO new_changes
SELECT * FROM changes;
PRAGMA foreign_keys = OFF;
DROP TABLE changes;
ALTER TABLE new_changes RENAME TO changes;
PRAGMA foreign_keys = ON;
 
COMMIT;
"""

_MYSQL_BASELINE = """BEGIN;

SET SESSION sql_mode = ansi;

CREATE TABLE releases (
    version         FLOAT(4, 1)   PRIMARY KEY
                    COMMENT 'Version of the Sqitch registry.',
    installed_at    DATETIME(6)   NOT NULL
                    COMMENT 'Date the registry release was installed.',
    installer_name  VARCHAR(255)  NOT NULL
                    COMMENT 'Name of the user who installed the registry release.',
    installer_email VARCHAR(255)  NOT NULL
                    COMMENT 'Email address of the user who installed the registry release.'
) ENGINE  InnoDB,
  CHARACTER SET 'utf8',
  COMMENT 'Sqitch registry releases.'
;

CREATE TABLE projects (
    project         VARCHAR(255) PRIMARY KEY
                    COMMENT 'Unique Name of a project.',
    uri             VARCHAR(255) NULL UNIQUE
                    COMMENT 'Optional project URI',
    created_at      DATETIME(6)  NOT NULL
                    COMMENT 'Date the project was added to the database.',
    creator_name    VARCHAR(255) NOT NULL
                    COMMENT 'Name of the user who added the project.',
    creator_email   VARCHAR(255) NOT NULL
                    COMMENT 'Email address of the user who added the project.'
) ENGINE  InnoDB,
  CHARACTER SET 'utf8',
  COMMENT 'Sqitch projects deployed to this database.'
;

CREATE TABLE changes (
    change_id       VARCHAR(40)  PRIMARY KEY
                    COMMENT 'Change primary key.',
    script_hash     VARCHAR(40)      NULL
                    COMMENT 'Deploy script SHA-1 hash.',
    "change"        VARCHAR(255) NOT NULL
                    COMMENT 'Name of a deployed change.',
    project         VARCHAR(255) NOT NULL
                    COMMENT 'Name of the Sqitch project to which the change belongs.'
                    REFERENCES projects(project) ON UPDATE CASCADE,
    note            TEXT         NOT NULL
                    COMMENT 'Description of the change.',
    committed_at    DATETIME(6)  NOT NULL
                    COMMENT 'Date the change was deployed.',
    committer_name  VARCHAR(255) NOT NULL
                    COMMENT 'Name of the user who deployed the change.',
    committer_email VARCHAR(255) NOT NULL
                    COMMENT 'Email address of the user who deployed the change.',
    planned_at      DATETIME(6)  NOT NULL
                    COMMENT 'Date the change was added to the plan.',
    planner_name    VARCHAR(255) NOT NULL
                    COMMENT 'Name of the user who planed the change.',
    planner_email   VARCHAR(255) NOT NULL
                    COMMENT 'Email address of the user who planned the change.',
    UNIQUE(project, script_hash)
) ENGINE  InnoDB,
  CHARACTER SET 'utf8',
  COMMENT 'Tracks the changes currently deployed to the database.'
;

CREATE TABLE tags (
    tag_id          VARCHAR(40)  PRIMARY KEY
                    COMMENT 'Tag primary key.',
    tag             VARCHAR(255) NOT NULL
                    COMMENT 'Project-unique tag name.',
    project         VARCHAR(255) NOT NULL
                    COMMENT 'Name of the Sqitch project to which the tag belongs.'
                    REFERENCES projects(project) ON UPDATE CASCADE,
    change_id       VARCHAR(40)  NOT NULL
                    COMMENT 'ID of last change deployed before the tag was applied.'
                    REFERENCES changes(change_id) ON UPDATE CASCADE,
    note            VARCHAR(255) NOT NULL
                    COMMENT 'Description of the tag.',
    committed_at    DATETIME(6)  NOT NULL
                    COMMENT 'Date the tag was applied to the database.',
    committer_name  VARCHAR(255) NOT NULL
                    COMMENT 'Name of the user who applied the tag.',
    committer_email VARCHAR(255) NOT NULL
                    COMMENT 'Email address of the user who applied the tag.',
    planned_at      DATETIME(6)  NOT NULL
                    COMMENT 'Date the tag was added to the plan.',
    planner_name    VARCHAR(255) NOT NULL
                    COMMENT 'Name of the user who planed the tag.',
    planner_email   VARCHAR(255) NOT NULL
                    COMMENT 'Email address of the user who planned the tag.',
    UNIQUE(project, tag)
) ENGINE  InnoDB,
  CHARACTER SET 'utf8',
  COMMENT 'Tracks the tags currently applied to the database.'
;

CREATE TABLE dependencies (
    change_id       VARCHAR(40)  NOT NULL
                    COMMENT 'ID of the depending change.'
                    REFERENCES changes(change_id) ON UPDATE CASCADE ON DELETE CASCADE,
    type            VARCHAR(8)   NOT NULL
                    COMMENT 'Type of dependency.',
    dependency      VARCHAR(255) NOT NULL
                    COMMENT 'Dependency name.',
    dependency_id   VARCHAR(40)      NULL
                    COMMENT 'Change ID the dependency resolves to.'
                    REFERENCES changes(change_id) ON UPDATE CASCADE,
    PRIMARY KEY (change_id, dependency)
) ENGINE  InnoDB,
  CHARACTER SET 'utf8',
  COMMENT 'Tracks the currently satisfied dependencies.'
;

CREATE TABLE events (
    event           ENUM ('deploy', 'fail', 'merge', 'revert') NOT NULL
                    COMMENT 'Type of event.',
    change_id       VARCHAR(40)  NOT NULL
                    COMMENT 'Change ID.',
    "change"        VARCHAR(255) NOT NULL
                    COMMENT 'Change name.',
    project         VARCHAR(255) NOT NULL
                    COMMENT 'Name of the Sqitch project to which the change belongs.'
                    REFERENCES projects(project) ON UPDATE CASCADE,
    note            TEXT         NOT NULL
                    COMMENT 'Description of the change.',
    requires        TEXT         NOT NULL
                    COMMENT 'List of the names of required changes.',
    conflicts       TEXT         NOT NULL
                    COMMENT 'List of the names of conflicting changes.',
    tags            TEXT         NOT NULL
                    COMMENT 'List of tags associated with the change.',
    committed_at    DATETIME(6)  NOT NULL
                    COMMENT 'Date the event was committed.',
    committer_name  VARCHAR(255) NOT NULL
                    COMMENT 'Name of the user who committed the event.',
    committer_email VARCHAR(255) NOT NULL
                    COMMENT 'Email address of the user who committed the event.',
    planned_at      DATETIME(6)  NOT NULL
                    COMMENT 'Date the event was added to the plan.',
    planner_name    VARCHAR(255) NOT NULL
                    COMMENT 'Name of the user who planed the change.',
    planner_email   VARCHAR(255) NOT NULL
                    COMMENT 'Email address of the user who plan planned the change.',
    PRIMARY KEY (change_id, committed_at)
) ENGINE  InnoDB,
  CHARACTER SET 'utf8',
  COMMENT 'Contains full history of all deployment events.'
;

-- ## BEGIN 5.5
DELIMITER |

CREATE TRIGGER ck_insert_dependency BEFORE INSERT ON dependencies
FOR EACH ROW BEGIN
    IF (NEW.type = 'require' AND NEW.dependency_id IS NULL)
    OR (NEW.type = 'conflict' AND NEW.dependency_id IS NOT NULL)
    THEN
        SIGNAL SQLSTATE 'ERR0R' SET MESSAGE_TEXT = 'Type must be "require" with dependency_id set or "conflict" with dependency_id not set';
    END IF;
END;
|

CREATE TRIGGER ck_update_dependency BEFORE UPDATE ON dependencies
FOR EACH ROW BEGIN
    IF (NEW.type = 'require'  AND NEW.dependency_id IS NULL)
    OR (NEW.type = 'conflict' AND NEW.dependency_id IS NOT NULL)
    THEN
        SIGNAL SQLSTATE 'ERR0R' SET MESSAGE_TEXT = 'Type must be "require" with dependency_id set or "conflict" with dependency_id not set';
    END IF;
END;
|

DELIMITER ;
-- ## END 5.5

COMMIT;
"""

_MYSQL_UPGRADE_1_0 = """CREATE TABLE releases (
    version         FLOAT         PRIMARY KEY
                    COMMENT 'Version of the Sqitch registry.',
    installed_at    TIMESTAMP     NOT NULL
                    COMMENT 'Date the registry release was installed.',
    installer_name  VARCHAR(255)  NOT NULL
                    COMMENT 'Name of the user who installed the registry release.',
    installer_email VARCHAR(255)  NOT NULL
                    COMMENT 'Email address of the user who installed the registry release.'
) ENGINE  InnoDB,
  CHARACTER SET 'utf8',
  COMMENT 'Sqitch registry releases.'
;

-- Add the script_hash column to the changes table. Copy change_id for now.
ALTER TABLE changes ADD COLUMN script_hash VARCHAR(40) NULL UNIQUE AFTER change_id;
UPDATE changes SET script_hash = change_id;

-- Allow "merge" events.
ALTER TABLE events CHANGE event event ENUM ('deploy', 'fail', 'merge', 'revert') NOT NULL;
"""

_MYSQL_UPGRADE_1_1 = """DROP INDEX script_hash ON changes;
ALTER TABLE changes ADD UNIQUE(project, script_hash);
"""

_POSTGRES_BASELINE = """BEGIN;

SET client_min_messages = warning;
CREATE SCHEMA IF NOT EXISTS :"registry";

COMMENT ON SCHEMA :"registry" IS 'Sqitch database deployment metadata v1.1.';

CREATE TABLE :"registry".releases (
    version         REAL        PRIMARY KEY,
    installed_at    TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    installer_name  TEXT        NOT NULL,
    installer_email TEXT        NOT NULL
):tableopts;

COMMENT ON TABLE  :"registry".releases                 IS 'Sqitch registry releases.';
COMMENT ON COLUMN :"registry".releases.version         IS 'Version of the Sqitch registry.';
COMMENT ON COLUMN :"registry".releases.installed_at    IS 'Date the registry release was installed.';
COMMENT ON COLUMN :"registry".releases.installer_name  IS 'Name of the user who installed the registry release.';
COMMENT ON COLUMN :"registry".releases.installer_email IS 'Email address of the user who installed the registry release.';

CREATE TABLE :"registry".projects (
    project         TEXT        PRIMARY KEY,
    uri             TEXT            NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    creator_name    TEXT        NOT NULL,
    creator_email   TEXT        NOT NULL
):tableopts;

COMMENT ON TABLE  :"registry".projects                IS 'Sqitch projects deployed to this database.';
COMMENT ON COLUMN :"registry".projects.project        IS 'Unique Name of a project.';
COMMENT ON COLUMN :"registry".projects.uri            IS 'Optional project URI';
COMMENT ON COLUMN :"registry".projects.created_at     IS 'Date the project was added to the database.';
COMMENT ON COLUMN :"registry".projects.creator_name   IS 'Name of the user who added the project.';
COMMENT ON COLUMN :"registry".projects.creator_email  IS 'Email address of the user who added the project.';

CREATE TABLE :"registry".changes (
    change_id       TEXT        PRIMARY KEY,
    script_hash     TEXT            NULL,
    change          TEXT        NOT NULL,
    project         TEXT        NOT NULL REFERENCES :"registry".projects(project) ON UPDATE CASCADE,
    note            TEXT        NOT NULL DEFAULT '',
    committed_at    TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    committer_name  TEXT        NOT NULL,
    committer_email TEXT        NOT NULL,
    planned_at      TIMESTAMPTZ NOT NULL,
    planner_name    TEXT        NOT NULL,
    planner_email   TEXT        NOT NULL,
    UNIQUE(project, script_hash)
):tableopts;

COMMENT ON TABLE  :"registry".changes                 IS 'Tracks the changes currently deployed to the database.';
COMMENT ON COLUMN :"registry".changes.change_id       IS 'Change primary key.';
COMMENT ON COLUMN :"registry".changes.script_hash     IS 'Deploy script SHA-1 hash.';
COMMENT ON COLUMN :"registry".changes.change          IS 'Name of a deployed change.';
COMMENT ON COLUMN :"registry".changes.project         IS 'Name of the Sqitch project to which the change belongs.';
COMMENT ON COLUMN :"registry".changes.note            IS 'Description of the change.';
COMMENT ON COLUMN :"registry".changes.committed_at    IS 'Date the change was deployed.';
COMMENT ON COLUMN :"registry".changes.committer_name  IS 'Name of the user who deployed the change.';
COMMENT ON COLUMN :"registry".changes.committer_email IS 'Email address of the user who deployed the change.';
COMMENT ON COLUMN :"registry".changes.planned_at      IS 'Date the change was added to the plan.';
COMMENT ON COLUMN :"registry".changes.planner_name    IS 'Name of the user who planed the change.';
COMMENT ON COLUMN :"registry".changes.planner_email   IS 'Email address of the user who planned the change.';

CREATE TABLE :"registry".tags (
    tag_id          TEXT        PRIMARY KEY,
    tag             TEXT        NOT NULL,
    project         TEXT        NOT NULL REFERENCES :"registry".projects(project) ON UPDATE CASCADE,
    change_id       TEXT        NOT NULL REFERENCES :"registry".changes(change_id) ON UPDATE CASCADE,
    note            TEXT        NOT NULL DEFAULT '',
    committed_at    TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    committer_name  TEXT        NOT NULL,
    committer_email TEXT        NOT NULL,
    planned_at      TIMESTAMPTZ NOT NULL,
    planner_name    TEXT        NOT NULL,
    planner_email   TEXT        NOT NULL,
    UNIQUE(project, tag)
):tableopts;

COMMENT ON TABLE  :"registry".tags                 IS 'Tracks the tags currently applied to the database.';
COMMENT ON COLUMN :"registry".tags.tag_id          IS 'Tag primary key.';
COMMENT ON COLUMN :"registry".tags.tag             IS 'Project-unique tag name.';
COMMENT ON COLUMN :"registry".tags.project         IS 'Name of the Sqitch project to which the tag belongs.';
COMMENT ON COLUMN :"registry".tags.change_id       IS 'ID of last change deployed before the tag was applied.';
COMMENT ON COLUMN :"registry".tags.note            IS 'Description of the tag.';
COMMENT ON COLUMN :"registry".tags.committed_at    IS 'Date the tag was applied to the database.';
COMMENT ON COLUMN :"registry".tags.committer_name  IS 'Name of the user who applied the tag.';
COMMENT ON COLUMN :"registry".tags.committer_email IS 'Email address of the user who applied the tag.';
COMMENT ON COLUMN :"registry".tags.planned_at      IS 'Date the tag was added to the plan.';
COMMENT ON COLUMN :"registry".tags.planner_name    IS 'Name of the user who planed the tag.';
COMMENT ON COLUMN :"registry".tags.planner_email   IS 'Email address of the user who planned the tag.';

CREATE TABLE :"registry".dependencies (
    change_id       TEXT        NOT NULL REFERENCES :"registry".changes(change_id) ON UPDATE CASCADE ON DELETE CASCADE,
    type            TEXT        NOT NULL,
    dependency      TEXT        NOT NULL,
    dependency_id   TEXT            NULL REFERENCES :"registry".changes(change_id) ON UPDATE CASCADE CONSTRAINT dependencies_check CHECK (
            (type = 'require'  AND dependency_id IS NOT NULL)
         OR (type = 'conflict' AND dependency_id IS NULL)
    ),
    PRIMARY KEY (change_id, dependency)
):tableopts;

COMMENT ON TABLE  :"registry".dependencies               IS 'Tracks the currently satisfied dependencies.';
COMMENT ON COLUMN :"registry".dependencies.change_id     IS 'ID of the depending change.';
COMMENT ON COLUMN :"registry".dependencies.type          IS 'Type of dependency.';
COMMENT ON COLUMN :"registry".dependencies.dependency    IS 'Dependency name.';
COMMENT ON COLUMN :"registry".dependencies.dependency_id IS 'Change ID the dependency resolves to.';

CREATE TABLE :"registry".events (
    event           TEXT        NOT NULL CONSTRAINT events_event_check CHECK (
        event IN ('deploy', 'revert', 'fail', 'merge')
    ),
    change_id       TEXT        NOT NULL,
    change          TEXT        NOT NULL,
    project         TEXT        NOT NULL REFERENCES :"registry".projects(project) ON UPDATE CASCADE,
    note            TEXT        NOT NULL DEFAULT '',
    requires        TEXT[]      NOT NULL DEFAULT '{}',
    conflicts       TEXT[]      NOT NULL DEFAULT '{}',
    tags            TEXT[]      NOT NULL DEFAULT '{}',
    committed_at    TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    committer_name  TEXT        NOT NULL,
    committer_email TEXT        NOT NULL,
    planned_at      TIMESTAMPTZ NOT NULL,
    planner_name    TEXT        NOT NULL,
    planner_email   TEXT        NOT NULL,
    PRIMARY KEY (change_id, committed_at)
):tableopts;

COMMENT ON TABLE  :"registry".events                 IS 'Contains full history of all deployment events.';
COMMENT ON COLUMN :"registry".events.event           IS 'Type of event.';
COMMENT ON COLUMN :"registry".events.change_id       IS 'Change ID.';
COMMENT ON COLUMN :"registry".events.change          IS 'Change name.';
COMMENT ON COLUMN :"registry".events.project         IS 'Name of the Sqitch project to which the change belongs.';
COMMENT ON COLUMN :"registry".events.note            IS 'Description of the change.';
COMMENT ON COLUMN :"registry".events.requires        IS 'Array of the names of required changes.';
COMMENT ON COLUMN :"registry".events.conflicts       IS 'Array of the names of conflicting changes.';
COMMENT ON COLUMN :"registry".events.tags            IS 'Tags associated with the change.';
COMMENT ON COLUMN :"registry".events.committed_at    IS 'Date the event was committed.';
COMMENT ON COLUMN :"registry".events.committer_name  IS 'Name of the user who committed the event.';
COMMENT ON COLUMN :"registry".events.committer_email IS 'Email address of the user who committed the event.';
COMMENT ON COLUMN :"registry".events.planned_at      IS 'Date the event was added to the plan.';
COMMENT ON COLUMN :"registry".events.planner_name    IS 'Name of the user who planed the change.';
COMMENT ON COLUMN :"registry".events.planner_email   IS 'Email address of the user who plan planned the change.';

COMMIT;
"""

_POSTGRES_UPGRADE_1_0 = """BEGIN;

SET client_min_messages = warning;

CREATE TABLE :"registry".releases (
    version         REAL        PRIMARY KEY,
    installed_at    TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    installer_name  TEXT        NOT NULL,
    installer_email TEXT        NOT NULL
):tableopts;

COMMENT ON TABLE  :"registry".releases                 IS 'Sqitch registry releases.';
COMMENT ON COLUMN :"registry".releases.version         IS 'Version of the Sqitch registry.';
COMMENT ON COLUMN :"registry".releases.installed_at    IS 'Date the registry release was installed.';
COMMENT ON COLUMN :"registry".releases.installer_name  IS 'Name of the user who installed the registry release.';
COMMENT ON COLUMN :"registry".releases.installer_email IS 'Email address of the user who installed the registry release.';

-- Add the script_hash column to the changes table. Copy change_id for now.
ALTER TABLE :"registry".changes ADD COLUMN script_hash TEXT NULL UNIQUE;
UPDATE :"registry".changes SET script_hash = change_id;
COMMENT ON COLUMN :"registry".changes.script_hash IS 'Deploy script SHA-1 hash.';

-- Allow "merge" events.
ALTER TABLE :"registry".events DROP CONSTRAINT events_event_check;
ALTER TABLE :"registry".events ADD  CONSTRAINT events_event_check
      CHECK (event IN ('deploy', 'revert', 'fail', 'merge'));

COMMENT ON SCHEMA :"registry" IS 'Sqitch database deployment metadata v1.0.';

COMMIT;
"""

_POSTGRES_UPGRADE_1_1 = (
    "BEGIN;\n\n"
    "SET client_min_messages = warning;\n"
    "ALTER TABLE :\"registry\".changes DROP CONSTRAINT changes_script_hash_key;\n"
    "ALTER TABLE :\"registry\".changes ADD UNIQUE (project, script_hash);\n"
    "COMMENT ON SCHEMA :\"registry\" IS 'Sqitch database deployment metadata v1.1.';\n"
    "COMMIT;\n"
)

_ENGINE_ALIASES: Dict[str, str] = {
    "sqlite": "sqlite",
    "mysql": "mysql",
    "pg": "pg",
    "postgres": "pg",
    "postgresql": "pg",
}

_REGISTRY_MIGRATIONS: Dict[str, Tuple[RegistryMigration, ...]] = {
    "sqlite": (
        RegistryMigration(
            target_version=LATEST_REGISTRY_VERSION,
            sql=_SQLITE_BASELINE,
            is_baseline=True,
            source="lib/App/Sqitch/Engine/sqlite.sql",
        ),
        RegistryMigration(
            target_version="1.0",
            sql=_SQLITE_UPGRADE_1_0,
            source="lib/App/Sqitch/Engine/Upgrade/sqlite-1.0.sql",
        ),
        RegistryMigration(
            target_version="1.1",
            sql=_SQLITE_UPGRADE_1_1,
            source="lib/App/Sqitch/Engine/Upgrade/sqlite-1.1.sql",
        ),
    ),
    "mysql": (
        RegistryMigration(
            target_version=LATEST_REGISTRY_VERSION,
            sql=_MYSQL_BASELINE,
            is_baseline=True,
            source="lib/App/Sqitch/Engine/mysql.sql",
        ),
        RegistryMigration(
            target_version="1.0",
            sql=_MYSQL_UPGRADE_1_0,
            source="lib/App/Sqitch/Engine/Upgrade/mysql-1.0.sql",
        ),
        RegistryMigration(
            target_version="1.1",
            sql=_MYSQL_UPGRADE_1_1,
            source="lib/App/Sqitch/Engine/Upgrade/mysql-1.1.sql",
        ),
    ),
    "pg": (
        RegistryMigration(
            target_version=LATEST_REGISTRY_VERSION,
            sql=_POSTGRES_BASELINE,
            is_baseline=True,
            source="lib/App/Sqitch/Engine/pg.sql",
        ),
        RegistryMigration(
            target_version="1.0",
            sql=_POSTGRES_UPGRADE_1_0,
            source="lib/App/Sqitch/Engine/Upgrade/pg-1.0.sql",
        ),
        RegistryMigration(
            target_version="1.1",
            sql=_POSTGRES_UPGRADE_1_1,
            source="lib/App/Sqitch/Engine/Upgrade/pg-1.1.sql",
        ),
    ),
}


def _normalize_engine(engine: str) -> str:
    normalized = engine.lower()
    if normalized not in _ENGINE_ALIASES:
        raise KeyError(f"Unsupported registry engine: {engine}")
    return _ENGINE_ALIASES[normalized]


def get_registry_migrations(engine: str) -> Tuple[RegistryMigration, ...]:
    """Return the ordered registry migrations for the given engine."""

    key = _normalize_engine(engine)
    return _REGISTRY_MIGRATIONS[key]


def list_registry_engines() -> Tuple[str, ...]:
    """Return the canonical list of engines with registry migrations."""

    return tuple(sorted(_REGISTRY_MIGRATIONS))


__all__ = [
    "LATEST_REGISTRY_VERSION",
    "RegistryMigration",
    "get_registry_migrations",
    "list_registry_engines",
]
