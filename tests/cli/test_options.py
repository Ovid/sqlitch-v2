"""Unit tests for sqlitch.cli.options module."""

from __future__ import annotations

from sqlitch.cli.options import (
    CredentialOverrides,
    LogConfiguration,
    generate_run_identifier,
)

__all__ = [
    "TestLogConfiguration",
    "TestCredentialOverrides",
    "TestGenerateRunIdentifier",
]


class TestLogConfiguration:
    """Tests for LogConfiguration dataclass."""

    def test_as_dict_serializes_all_fields(self) -> None:
        """Verify as_dict returns all configuration fields."""
        config = LogConfiguration(
            run_identifier="test-id-123",
            verbosity=2,
            quiet=False,
            json_mode=True,
            destination="stdout",
            rich_markup=False,
            rich_tracebacks=True,
        )

        result = config.as_dict()

        assert result == {
            "run_id": "test-id-123",
            "verbosity": 2,
            "quiet": False,
            "json": True,
            "level": "TRACE",
            "destination": "stdout",
            "rich_markup": False,
            "rich_tracebacks": True,
            "structured_logging": True,
        }

    def test_as_dict_includes_computed_properties(self) -> None:
        """Verify as_dict includes level and structured_logging properties."""
        config = LogConfiguration(
            run_identifier="abc",
            verbosity=1,
            quiet=False,
            json_mode=False,
        )

        result = config.as_dict()

        assert result["level"] == "DEBUG"
        assert result["structured_logging"] is True

    def test_level_returns_error_when_quiet(self) -> None:
        """Verify level is ERROR when quiet mode is active."""
        config = LogConfiguration(
            run_identifier="id",
            verbosity=0,
            quiet=True,
            json_mode=False,
        )

        assert config.level == "ERROR"

    def test_level_returns_trace_for_high_verbosity(self) -> None:
        """Verify level is TRACE for verbosity >= 2."""
        config = LogConfiguration(
            run_identifier="id",
            verbosity=2,
            quiet=False,
            json_mode=False,
        )

        assert config.level == "TRACE"

    def test_level_returns_debug_for_medium_verbosity(self) -> None:
        """Verify level is DEBUG for verbosity >= 1."""
        config = LogConfiguration(
            run_identifier="id",
            verbosity=1,
            quiet=False,
            json_mode=False,
        )

        assert config.level == "DEBUG"

    def test_level_returns_info_for_no_verbosity(self) -> None:
        """Verify level is INFO for verbosity == 0."""
        config = LogConfiguration(
            run_identifier="id",
            verbosity=0,
            quiet=False,
            json_mode=False,
        )

        assert config.level == "INFO"

    def test_structured_logging_enabled_when_json_mode(self) -> None:
        """Verify structured logging is enabled when json_mode is True."""
        config = LogConfiguration(
            run_identifier="id",
            verbosity=0,
            quiet=False,
            json_mode=True,
        )

        assert config.structured_logging_enabled is True

    def test_structured_logging_enabled_when_verbose(self) -> None:
        """Verify structured logging is enabled when verbosity > 0."""
        config = LogConfiguration(
            run_identifier="id",
            verbosity=1,
            quiet=False,
            json_mode=False,
        )

        assert config.structured_logging_enabled is True

    def test_structured_logging_disabled_when_neither_json_nor_verbose(self) -> None:
        """Verify structured logging is disabled when neither json nor verbose."""
        config = LogConfiguration(
            run_identifier="id",
            verbosity=0,
            quiet=False,
            json_mode=False,
        )

        assert config.structured_logging_enabled is False


class TestCredentialOverrides:
    """Tests for CredentialOverrides dataclass."""

    def test_as_dict_includes_both_credentials(self) -> None:
        """Verify as_dict returns both username and password when set."""
        creds = CredentialOverrides(
            username="testuser",
            password="testpass",
        )

        result = creds.as_dict()

        assert result == {
            "username": "testuser",
            "password": "testpass",
        }

    def test_as_dict_includes_only_username(self) -> None:
        """Verify as_dict returns only username when password is None."""
        creds = CredentialOverrides(
            username="testuser",
            password=None,
        )

        result = creds.as_dict()

        assert result == {"username": "testuser"}

    def test_as_dict_includes_only_password(self) -> None:
        """Verify as_dict returns only password when username is None."""
        creds = CredentialOverrides(
            username=None,
            password="testpass",
        )

        result = creds.as_dict()

        assert result == {"password": "testpass"}

    def test_as_dict_empty_when_all_none(self) -> None:
        """Verify as_dict returns empty dict when all fields are None."""
        creds = CredentialOverrides(
            username=None,
            password=None,
        )

        result = creds.as_dict()

        assert result == {}


class TestGenerateRunIdentifier:
    """Tests for generate_run_identifier function."""

    def test_returns_hex_string(self) -> None:
        """Verify generate_run_identifier returns a hex string."""
        run_id = generate_run_identifier()

        assert isinstance(run_id, str)
        assert len(run_id) == 32  # UUID4 hex is 32 characters
        # Verify it's valid hex
        int(run_id, 16)

    def test_returns_unique_values(self) -> None:
        """Verify generate_run_identifier returns different values each call."""
        id1 = generate_run_identifier()
        id2 = generate_run_identifier()

        assert id1 != id2
