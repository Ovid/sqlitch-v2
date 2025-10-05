"""Test helpers for setting up SQLite-backed SQLitch projects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

from sqlitch.plan.formatter import write_plan
from sqlitch.plan.model import Change

__all__ = [
    "ChangeScript",
    "SQLiteProject",
    "create_sqlite_project",
    "create_failing_change_project",
    "registry_path_for",
]


@dataclass(frozen=True, slots=True)
class ChangeScript:
    """Represents the on-disk scripts for a deployable change."""

    name: str
    deploy_sql: str
    revert_sql: str = "-- revert placeholder"
    verify_sql: str | None = None


@dataclass(frozen=True, slots=True)
class SQLiteProject:
    """Container describing a temporary SQLitch project layout."""

    project_root: Path
    plan_path: Path
    scripts_dir: Path
    registry_path: Path
    change_files: Mapping[str, Path]


def create_sqlite_project(tmp_path: Path, *, changes: Iterable[ChangeScript]) -> SQLiteProject:
    """Write a SQLitch-compatible plan and scripts under ``tmp_path``.

    The helper mirrors Sqitch defaults:

    * Plan file written to ``sqitch.plan`` at the project root.
    * Deploy, revert, and verify scripts stored beneath ``deploy/``, ``revert/``
      and ``verify/`` directories respectively.
    * A canonical ``sqitch.db`` registry path is returned for later assertions.
    """

    project_root = Path(tmp_path)
    scripts_root = project_root
    plan_path = project_root / "sqitch.plan"

    deploy_dir = scripts_root / "deploy"
    revert_dir = scripts_root / "revert"
    verify_dir = scripts_root / "verify"
    for directory in (deploy_dir, revert_dir, verify_dir):
        directory.mkdir(parents=True, exist_ok=True)

    change_models: list[Change] = []
    change_files: dict[str, Path] = {}

    for definition in changes:
        slug = definition.name.replace("/", "_").replace(":", "_")
        deploy_path = deploy_dir / f"{slug}.sql"
        revert_path = revert_dir / f"{slug}.sql"
        verify_path = verify_dir / f"{slug}.sql"

        deploy_path.write_text(definition.deploy_sql, encoding="utf-8")
        revert_path.write_text(definition.revert_sql, encoding="utf-8")
        if definition.verify_sql is not None:
            verify_path.write_text(definition.verify_sql, encoding="utf-8")
            verify_entry: Path | None = verify_path
        else:
            verify_path.unlink(missing_ok=True)
            verify_entry = None

        change = Change.create(
            name=definition.name,
            script_paths={
                "deploy": deploy_path.relative_to(project_root),
                "revert": revert_path.relative_to(project_root),
                "verify": (
                    verify_entry.relative_to(project_root) if verify_entry else None
                ),
            },
            planner="Test User <tester@example.com>",
            planned_at=datetime.now(timezone.utc),
            notes=None,
        )
        change_models.append(change)
        change_files[definition.name] = deploy_path

    write_plan(
        project_name="demo",
        default_engine="sqlite",
        entries=tuple(change_models),
        plan_path=plan_path,
    )

    registry_path = registry_path_for(project_root)

    return SQLiteProject(
        project_root=project_root,
        plan_path=plan_path,
        scripts_dir=scripts_root,
        registry_path=registry_path,
        change_files=change_files,
    )


def create_failing_change_project(tmp_path: Path) -> SQLiteProject:
    """Return a project whose single deploy script triggers an intentional error."""

    failing_change = ChangeScript(
        name="alpha", deploy_sql="SELECT RAISE(ABORT, 'intentional failure');"
    )
    return create_sqlite_project(tmp_path, changes=[failing_change])


def registry_path_for(project_root: Path) -> Path:
    """Return the canonical registry path used for SQLite targets."""

    return Path(project_root) / "sqitch.db"
