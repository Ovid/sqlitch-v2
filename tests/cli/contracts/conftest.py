"""Shared test fixtures and utilities for contract tests."""

from __future__ import annotations

from pathlib import Path


def ensure_sqitch_config(project_root: Path, engine: str = "sqlite") -> Path:
    """Create a minimal sqitch.conf file if it doesn't exist.

    Sqitch doesn't store engine in plan file - it comes from config.
    This helper ensures commands can find the engine configuration.

    Args:
        project_root: Directory containing (or to contain) sqitch.conf
        engine: Database engine name (default: sqlite)

    Returns:
        Path to the created config file
    """
    config_path = project_root / "sqitch.conf"
    if not config_path.exists():
        config_path.write_text(f"[core]\n\tengine = {engine}\n", encoding="utf-8")
    return config_path
