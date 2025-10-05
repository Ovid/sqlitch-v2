"""Regression expectations for credential precedence resolution."""

from __future__ import annotations

from sqlitch.cli.options import CredentialOverrides
from sqlitch.config import resolver as config_resolver


def test_cli_credential_precedence(tmp_path) -> None:
    system_dir = tmp_path / "system"
    system_dir.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "sqitch.conf"
    config_file.write_text(
        """
[target "demo"]
username = config_user
password = config_pass
""".strip()
        + "\n",
        encoding="utf-8",
    )

    profile = config_resolver.resolve_config(
        root_dir=tmp_path,
        config_root=config_dir,
        system_path=system_dir,
        env={},
    )

    env = {
        "SQLITCH_USERNAME": "env_user",
        "SQLITCH_PASSWORD": "env_pass",
    }

    cli_overrides = CredentialOverrides(username="cli_user", password="cli_pass")
    resolved = config_resolver.resolve_credentials(
        target="demo",
        profile=profile,
        env=env,
        cli_overrides=cli_overrides,
    )
    assert resolved.username == "cli_user"
    assert resolved.password == "cli_pass"
    assert resolved.sources["username"] == "cli"
    assert resolved.sources["password"] == "cli"

    resolved_env = config_resolver.resolve_credentials(
        target="demo",
        profile=profile,
        env=env,
        cli_overrides=CredentialOverrides(),
    )
    assert resolved_env.username == "env_user"
    assert resolved_env.password == "env_pass"
    assert resolved_env.sources["username"] == "env"
    assert resolved_env.sources["password"] == "env"

    resolved_config = config_resolver.resolve_credentials(
        target="demo",
        profile=profile,
        env={},
        cli_overrides=None,
    )
    assert resolved_config.username == "config_user"
    assert resolved_config.password == "config_pass"
    assert resolved_config.sources["username"] == "config"
    assert resolved_config.sources["password"] == "config"
