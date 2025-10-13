"""Unit coverage for ``sqlitch.cli.commands._plan_utils`` helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from sqlitch.cli.commands import CommandError
from sqlitch.cli.commands import _plan_utils as plan_utils
from sqlitch.config.loader import ConfigProfile


@pytest.fixture()
def empty_profile(tmp_path: Path) -> ConfigProfile:
    return ConfigProfile(
        root_dir=tmp_path,
        files=(),
        settings={},
        active_engine=None,
    )


def test_resolve_default_engine_prefers_override(
    tmp_path: Path, empty_profile: ConfigProfile, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(plan_utils.config_resolver, "resolve_config", lambda **_: empty_profile)

    engine = plan_utils.resolve_default_engine(
        project_root=tmp_path,
        config_root=tmp_path / "cfg",
        env={},
        engine_override="pg",
    )

    assert engine == "pg"


def test_resolve_default_engine_uses_config_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    profile = ConfigProfile(
        root_dir=tmp_path,
        files=(),
        settings={"core": {"engine": "mysql"}},
        active_engine="mysql",
    )
    monkeypatch.setattr(plan_utils.config_resolver, "resolve_config", lambda **_: profile)

    engine = plan_utils.resolve_default_engine(
        project_root=tmp_path,
        config_root=tmp_path / "cfg",
        env={},
        engine_override=None,
    )

    assert engine == "mysql"


def test_resolve_default_engine_reads_plan_header(
    tmp_path: Path, empty_profile: ConfigProfile, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_path = tmp_path / "sqlitch.plan"
    plan_path.write_text("%project=widgets\n%default_engine=sqlite\n", encoding="utf-8")

    monkeypatch.setattr(plan_utils.config_resolver, "resolve_config", lambda **_: empty_profile)

    engine = plan_utils.resolve_default_engine(
        project_root=tmp_path,
        config_root=tmp_path / "cfg",
        env={},
        engine_override=None,
        plan_path=plan_path,
    )

    assert engine == "sqlite"


def test_resolve_default_engine_without_any_engine_source_errors(
    tmp_path: Path,
    empty_profile: ConfigProfile,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that resolve_default_engine raises an error when no engine is found."""
    plan_path = tmp_path / "sqlitch.plan"
    plan_path.write_text("%project=widgets\n", encoding="utf-8")

    monkeypatch.setattr(plan_utils.config_resolver, "resolve_config", lambda **_: empty_profile)

    with pytest.raises(CommandError, match="No default engine configured"):
        plan_utils.resolve_default_engine(
            project_root=tmp_path,
            config_root=tmp_path / "cfg",
            env={},
            engine_override=None,
            plan_path=plan_path,
        )


def test_resolve_default_engine_without_configuration_errors(
    tmp_path: Path,
    empty_profile: ConfigProfile,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan_path = tmp_path / "sqlitch.plan"
    plan_path.write_text("%project=widgets\n", encoding="utf-8")

    monkeypatch.setattr(plan_utils.config_resolver, "resolve_config", lambda **_: empty_profile)

    import sqlitch.plan.parser as parser_module

    monkeypatch.setattr(parser_module, "parse_plan", lambda *args, **kwargs: object())

    with pytest.raises(CommandError, match="No default engine configured"):
        plan_utils.resolve_default_engine(
            project_root=tmp_path,
            config_root=tmp_path / "cfg",
            env={},
            engine_override=None,
            plan_path=plan_path,
        )


def test_read_plan_default_engine_missing_file(tmp_path: Path) -> None:
    plan_path = tmp_path / "missing.plan"

    assert plan_utils._read_plan_default_engine(plan_path) is None
