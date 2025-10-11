"""Tutorial step manifest shared across UAT harnesses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

__all__ = ["Step", "TUTORIAL_STEPS"]


@dataclass(frozen=True)
class Step:
    """Represents a single tutorial command invocation.

    Attributes
    ----------
    number:
        Sequential identifier corresponding to the tutorial order.
    description:
        Human-readable description of the step.
    command:
        Executable invoked for the step (``sqlitch`` or ``sqlite3``).
    args:
        Positional command arguments.
    """

    number: int
    description: str
    command: str
    args: Tuple[str, ...]


TUTORIAL_STEPS: list[Step] = [
    Step(
        1,
        "Initialize Project",
        "sqlitch",
        (
            "init",
            "flipr",
            "--uri",
            "https://github.com/sqitchers/sqitch-sqlite-intro/",
            "--engine",
            "sqlite",
        ),
    ),
    Step(2, "Configure User Name", "sqlitch", ("config", "user.name", "Test User")),
    Step(3, "Configure User Email", "sqlitch", ("config", "user.email", "test@example.com")),
    Step(4, "Disable Pager", "sqlitch", ("config", "--bool", "core.pager", "false")),
    Step(
        5,
        "Add 'users' Table",
        "sqlitch",
        ("add", "users", "-n", "Creates table to track our users."),
    ),
    Step(6, "Deploy 'users' Table", "sqlitch", ("deploy", "db:sqlite:flipr_test.db")),
    Step(7, "Verify 'users' Deployment", "sqlitch", ("verify", "db:sqlite:flipr_test.db")),
    Step(8, "Check Status After Deploy", "sqlitch", ("status", "db:sqlite:flipr_test.db")),
    Step(9, "Check DB Schema with sqlite3", "sqlite3", ("flipr_test.db", ".tables")),
    Step(10, "Revert 'users' Table", "sqlitch", ("revert", "db:sqlite:flipr_test.db", "-y")),
    Step(11, "Verify Revert with sqlite3", "sqlite3", ("flipr_test.db", ".tables")),
    Step(12, "Check Sqitch Log", "sqlitch", ("log", "db:sqlite:flipr_test.db")),
    Step(
        13,
        "Add Target 'flipr_test'",
        "sqlitch",
        ("target", "add", "flipr_test", "db:sqlite:flipr_test.db"),
    ),
    Step(14, "Add Engine for Target", "sqlitch", ("engine", "add", "sqlite", "flipr_test")),
    Step(
        15,
        "Enable Deploy Verification",
        "sqlitch",
        ("config", "--bool", "deploy.verify", "true"),
    ),
    Step(
        16,
        "Enable Rebase Verification",
        "sqlitch",
        ("config", "--bool", "rebase.verify", "true"),
    ),
    Step(17, "Deploy Again with Target", "sqlitch", ("deploy",)),
    Step(
        18,
        "Add 'flips' Table",
        "sqlitch",
        ("add", "flips", "--requires", "users", "-n", "Adds table for storing flips."),
    ),
    Step(19, "Deploy 'flips' Table", "sqlitch", ("deploy",)),
    Step(20, "Verify All Deployments", "sqlitch", ("verify",)),
    Step(21, "Check DB Schema for 'users' and 'flips'", "sqlite3", ("flipr_test.db", ".tables")),
    Step(22, "Partial Revert to HEAD^", "sqlitch", ("revert", "--to", "@HEAD^", "-y")),
    Step(23, "Verify Partial Revert", "sqlite3", ("flipr_test.db", ".tables")),
    Step(24, "Deploy All Again", "sqlitch", ("deploy",)),
    Step(
        25,
        "Add 'userflips' View",
        "sqlitch",
        (
            "add",
            "userflips",
            "--requires",
            "users",
            "--requires",
            "flips",
            "-n",
            "Creates the userflips view.",
        ),
    ),
    Step(26, "Deploy 'userflips' View", "sqlitch", ("deploy",)),
    Step(27, "Full Revert", "sqlitch", ("revert", "-y")),
    Step(28, "Full Redeploy", "sqlitch", ("deploy",)),
    Step(
        29,
        "Tag Release v1.0.0-dev1",
        "sqlitch",
        ("tag", "v1.0.0-dev1", "-n", "Tag v1.0.0-dev1."),
    ),
    Step(30, "Deploy Tag to New DB", "sqlitch", ("deploy", "db:sqlite:dev/flipr.db")),
    Step(31, "Check Status of Tagged DB", "sqlitch", ("status", "db:sqlite:dev/flipr.db")),
    Step(32, "Create Bundle", "sqlitch", ("bundle",)),
    Step(
        33,
        "Deploy Bundle to New DB",
        "sqlitch",
        ("deploy", "db:sqlite:flipr_prod.db", "-C", "bundle"),
    ),
    Step(
        34,
        "Add 'hashtags' Table",
        "sqlitch",
        ("add", "hashtags", "--requires", "flips", "-n", "Adds table for storing hashtags."),
    ),
    Step(35, "Deploy 'hashtags' Table", "sqlitch", ("deploy",)),
    Step(36, "Check Status with Tags", "sqlitch", ("status", "--show-tags")),
    Step(37, "Rebase Plan", "sqlitch", ("rebase", "-y")),
    Step(
        38,
        "Tag Release v1.0.0-dev2",
        "sqlitch",
        ("tag", "v1.0.0-dev2", "-n", "Tag v1.0.0-dev2."),
    ),
    Step(
        39,
        "Rework 'userflips' View",
        "sqlitch",
        ("rework", "userflips", "-n", "Adds userflips.twitter."),
    ),
    Step(40, "Deploy Reworked View", "sqlitch", ("deploy",)),
    Step(41, "Verify Reworked Schema", "sqlite3", ("flipr_test.db", ".schema userflips")),
    Step(42, "Revert Reworked Change", "sqlitch", ("revert", "--to", "@HEAD^", "-y")),
    Step(43, "Verify Revert of Rework", "sqlite3", ("flipr_test.db", ".schema userflips")),
    Step(44, "Final Deployment", "sqlitch", ("deploy",)),
    Step(45, "Final Verification", "sqlitch", ("verify",)),
    Step(46, "Final Status Check", "sqlitch", ("status",)),
]
