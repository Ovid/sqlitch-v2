from __future__ import annotations

import re
from pathlib import Path

import pytest

from sqlitch.registry.migrations import (
    LATEST_REGISTRY_VERSION,
    RegistryMigration,
    get_registry_migrations,
)


_ROOT = Path(__file__).resolve().parent.parent.parent
_SQITCH_DIR = _ROOT / "sqitch" / "lib" / "App" / "Sqitch" / "Engine"
_REFERENCE_FILENAMES = {
    "sqlite": "sqlite",
    "mysql": "mysql",
    "pg": "pg",
}

_DEPLOY_FAIL_PATTERN = re.compile(r",\s*'deploy_fail'")


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def _assert_sql_matches_reference(
    actual: str,
    reference: str,
    *,
    allow_deploy_fail: bool = False,
) -> None:
    if actual == reference:
        return

    if allow_deploy_fail:
        normalized = _DEPLOY_FAIL_PATTERN.sub("", actual)
        if normalized == reference:
            assert "'deploy_fail'" in actual
            return

        if _normalize_whitespace(normalized) == _normalize_whitespace(reference):
            assert "'deploy_fail'" in actual
            return

    assert actual == reference


def _load_reference(engine: str, version: str | None = None) -> str:
    prefix = _REFERENCE_FILENAMES[engine]
    if version is None:
        reference = _SQITCH_DIR / f"{prefix}.sql"
    else:
        reference = _SQITCH_DIR / "Upgrade" / f"{prefix}-{version}.sql"
    return reference.read_text(encoding="utf-8")


def _index_migrations(migrations: tuple[RegistryMigration, ...]) -> dict[str, RegistryMigration]:
    return {migration.target_version: migration for migration in migrations}


def test_sqlite_migrations_match_sqitch_reference() -> None:
    migrations = get_registry_migrations("sqlite")
    baseline = [migration for migration in migrations if migration.is_baseline]
    assert len(baseline) == 1
    assert baseline[0].target_version == LATEST_REGISTRY_VERSION
    _assert_sql_matches_reference(
        baseline[0].sql,
        _load_reference("sqlite"),
        allow_deploy_fail=True,
    )

    indexed = _index_migrations(tuple(m for m in migrations if not m.is_baseline))
    assert set(indexed) == {"1.0", "1.1"}
    _assert_sql_matches_reference(
        indexed["1.0"].sql,
        _load_reference("sqlite", "1.0"),
        allow_deploy_fail=True,
    )
    assert indexed["1.1"].sql == _load_reference("sqlite", "1.1")


def test_mysql_migrations_match_sqitch_reference() -> None:
    migrations = get_registry_migrations("mysql")
    baseline = [migration for migration in migrations if migration.is_baseline]
    assert len(baseline) == 1
    assert baseline[0].target_version == LATEST_REGISTRY_VERSION
    assert baseline[0].sql == _load_reference("mysql")

    indexed = _index_migrations(tuple(m for m in migrations if not m.is_baseline))
    assert set(indexed) == {"1.0", "1.1"}
    assert indexed["1.0"].sql == _load_reference("mysql", "1.0")
    assert indexed["1.1"].sql == _load_reference("mysql", "1.1")


def test_postgres_migrations_match_sqitch_reference() -> None:
    migrations = get_registry_migrations("pg")
    baseline = [migration for migration in migrations if migration.is_baseline]
    assert len(baseline) == 1
    assert baseline[0].target_version == LATEST_REGISTRY_VERSION
    _assert_sql_matches_reference(
        baseline[0].sql,
        _load_reference("pg"),
        allow_deploy_fail=True,
    )

    indexed = _index_migrations(tuple(m for m in migrations if not m.is_baseline))
    assert set(indexed) == {"1.0", "1.1"}
    _assert_sql_matches_reference(
        indexed["1.0"].sql,
        _load_reference("pg", "1.0"),
        allow_deploy_fail=True,
    )
    assert indexed["1.1"].sql == _load_reference("pg", "1.1")


def test_postgres_aliases_pg_key() -> None:
    canonical = get_registry_migrations("pg")
    assert canonical == get_registry_migrations("postgres")
    assert canonical == get_registry_migrations("postgresql")


@pytest.mark.parametrize("engine", ["sqlserver", "oracle", "unknown"])
def test_get_registry_migrations_rejects_unknown_engines(engine: str) -> None:
    with pytest.raises(KeyError):
        get_registry_migrations(engine)
