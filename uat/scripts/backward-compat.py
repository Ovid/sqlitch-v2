#!/usr/bin/env python3
"""sqitch → sqlitch backward compatibility harness.

This script replays the SQLite tutorial using Sqitch first for each step,
then validates that SQLitch can continue the workflow from that state. This
tests backward compatibility: can SQLitch work with databases deployed by Sqitch?

The workflow alternates:
  1. Sqitch executes step N
  2. SQLitch executes step N+1
  3. Sqitch executes step N+2
  4. And so on...

This ensures that SQLitch can always pick up where Sqitch left off.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
    if str(PACKAGE_ROOT) not in sys.path:
        sys.path.insert(0, str(PACKAGE_ROOT))
    from uat import comparison, sanitization
    from uat.test_steps import TUTORIAL_STEPS, Step
else:
    from .. import comparison, sanitization
    from ..test_steps import TUTORIAL_STEPS, Step

_SKIP_ENV = "SQLITCH_UAT_SKIP_EXECUTION"

# Test working directory
WORK_DIR = Path("uat/backward_compat_results")
LOG_FILE = WORK_DIR / "backward-compat.log"

# Colors
GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
NC = "\033[0m"


def color_print(color: str, msg: str) -> None:
    """Print colored message to stdout."""
    print(f"{color}{msg}{NC}")


def check_command(cmd: str) -> None:
    """Verify that a command exists in PATH."""
    if shutil.which(cmd) is None:
        color_print(RED, f"⛔️ ERROR: {cmd} is not installed or not in PATH")
        sys.exit(1)


def log_append(header: str, cmd: list[str], output: str) -> None:
    """Append command execution details to log file."""
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"STEP: {header}\n")
        f.write(f"COMMAND: {' '.join(cmd)}\n")
        f.write(f"{'='*60}\n")
        f.write(output)
        if not output.endswith("\n"):
            f.write("\n")


def run_command(cmd: list[str], cwd: Path, tool_name: str) -> tuple[str, int]:
    """Run command and capture output."""
    color_print(CYAN, f"    Running {tool_name}: {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )
    captured_lines: list[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(f"      {line}")
        sys.stdout.flush()
        captured_lines.append(line)
    proc.wait()
    return ("".join(captured_lines), proc.returncode)


def write_sql_files(step_num: int) -> None:
    """Write SQL files for specific tutorial steps that require them."""
    # Users table (after step 5)
    if step_num == 5:
        (WORK_DIR / "deploy").mkdir(parents=True, exist_ok=True)
        (WORK_DIR / "revert").mkdir(parents=True, exist_ok=True)
        (WORK_DIR / "verify").mkdir(parents=True, exist_ok=True)
        
        (WORK_DIR / "deploy/users.sql").write_text(
            """-- Deploy flipr:users to sqlite

BEGIN;

CREATE TABLE users (
    nickname TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    fullname TEXT NOT NULL,
    twitter TEXT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
""",
            encoding="utf-8",
        )
        
        (WORK_DIR / "revert/users.sql").write_text(
            """-- Revert flipr:users from sqlite

BEGIN;

DROP TABLE users;

COMMIT;
""",
            encoding="utf-8",
        )
        
        (WORK_DIR / "verify/users.sql").write_text(
            """-- Verify flipr:users on sqlite

BEGIN;

SELECT nickname, password, fullname, twitter
FROM users
WHERE 0;

ROLLBACK;
""",
            encoding="utf-8",
        )
    
    # Flips table (after step 18)
    elif step_num == 18:
        (WORK_DIR / "deploy/flips.sql").write_text(
            """-- Deploy flipr:flips to sqlite
-- requires: users

BEGIN;

CREATE TABLE flips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname TEXT NOT NULL REFERENCES users(nickname),
    body TEXT NOT NULL DEFAULT '' CHECK ( length(body) <= 180 ),
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
""",
            encoding="utf-8",
        )
        
        (WORK_DIR / "revert/flips.sql").write_text(
            """-- Revert flipr:flips from sqlite

BEGIN;

DROP TABLE flips;

COMMIT;
""",
            encoding="utf-8",
        )
        
        (WORK_DIR / "verify/flips.sql").write_text(
            """-- Verify flipr:flips on sqlite

BEGIN;

SELECT id, nickname, body, timestamp
FROM flips
WHERE 0;

ROLLBACK;
""",
            encoding="utf-8",
        )
    
    # Userflips view (after step 25)
    elif step_num == 25:
        (WORK_DIR / "deploy/userflips.sql").write_text(
            """-- Deploy flipr:userflips to sqlite
-- requires: users
-- requires: flips

BEGIN;

CREATE VIEW userflips AS
SELECT f.id, u.nickname, u.fullname, f.body, f.timestamp
FROM users u
JOIN flips f ON u.nickname = f.nickname;

COMMIT;
""",
            encoding="utf-8",
        )
        
        (WORK_DIR / "revert/userflips.sql").write_text(
            """-- Revert flipr:userflips from sqlite

BEGIN;

DROP VIEW userflips;

COMMIT;
""",
            encoding="utf-8",
        )
        
        (WORK_DIR / "verify/userflips.sql").write_text(
            """-- Verify flipr:userflips on sqlite

BEGIN;

SELECT id, nickname, fullname, body, timestamp
FROM userflips
WHERE 0;

ROLLBACK;
""",
            encoding="utf-8",
        )
    
    # Hashtags table (after step 34)
    elif step_num == 34:
        (WORK_DIR / "deploy/hashtags.sql").write_text(
            """-- Deploy flipr:hashtags to sqlite
-- requires: flips

BEGIN;

CREATE TABLE hashtags (
    flip_id INTEGER NOT NULL REFERENCES flips(id),
    hashtag TEXT NOT NULL CHECK ( length(hashtag) > 0 ),
    PRIMARY KEY (flip_id, hashtag)
);

COMMIT;
""",
            encoding="utf-8",
        )
        
        (WORK_DIR / "revert/hashtags.sql").write_text(
            """-- Revert flipr:hashtags from sqlite

BEGIN;

DROP TABLE hashtags;

COMMIT;
""",
            encoding="utf-8",
        )
        
        (WORK_DIR / "verify/hashtags.sql").write_text(
            """-- Verify flipr:hashtags on sqlite

BEGIN;

SELECT flip_id, hashtag FROM hashtags WHERE 0;

ROLLBACK;
""",
            encoding="utf-8",
        )
    
    # Reworked userflips (after step 39)
    elif step_num == 39:
        (WORK_DIR / "deploy/userflips.sql").write_text(
            """-- Deploy flipr:userflips to sqlite
-- requires: users
-- requires: flips

BEGIN;

DROP VIEW IF EXISTS userflips;

CREATE VIEW userflips AS
SELECT f.id, u.nickname, u.fullname, u.twitter, f.body, f.timestamp
FROM users u
JOIN flips f ON u.nickname = f.nickname;

COMMIT;
""",
            encoding="utf-8",
        )
        
        (WORK_DIR / "revert/userflips.sql").write_text(
            """-- Revert flipr:userflips from sqlite

BEGIN;

DROP VIEW IF EXISTS userflips;

CREATE VIEW userflips AS
SELECT f.id, u.nickname, u.fullname, f.body, f.timestamp
FROM users u
JOIN flips f ON u.nickname = f.nickname;

COMMIT;
""",
            encoding="utf-8",
        )
        
        (WORK_DIR / "verify/userflips.sql").write_text(
            """-- Verify flipr:userflips on sqlite

BEGIN;

SELECT id, nickname, fullname, twitter, body, timestamp
FROM userflips
WHERE 0;

ROLLBACK;
""",
            encoding="utf-8",
        )
    
    # Create dev directory for step 30
    elif step_num == 30:
        (WORK_DIR / "dev").mkdir(parents=True, exist_ok=True)


def execute_step(step: Step, use_sqitch: bool) -> tuple[bool, str]:
    """Execute a single tutorial step with either sqitch or sqlitch.
    
    Returns (success, error_message).
    """
    tool = "sqitch" if use_sqitch else "sqlitch"
    
    # Build command
    if step.command == "sqlitch":
        cmd = [tool] + list(step.args)
    elif step.command == "sqlite3":
        cmd = ["sqlite3"] + list(step.args)
    else:
        return False, f"Unknown command: {step.command}"
    
    # Execute command FIRST (for 'add' commands that create file structure)
    output, returncode = run_command(cmd, WORK_DIR, tool)
    log_append(f"Step {step.number}: {step.description}", cmd, output)
    
    if returncode != 0:
        return False, f"Command failed with exit code {returncode}"
    
    # Write SQL files AFTER successful execution for steps that need them
    write_sql_files(step.number)
    
    return True, ""


def cleanup() -> None:
    """Remove working directory."""
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--out", required=True, metavar="PATH", help="Destination file for sanitized log output"
    )
    args = parser.parse_args()

    log_path = Path(args.out).expanduser()

    header = "Backward compatibility harness (sqitch → sqlitch)"
    color_print(GREEN, "=" * 60)
    color_print(GREEN, header)
    color_print(GREEN, "=" * 60)

    skip_execution = os.getenv(_SKIP_ENV, "").strip() not in {"", "0", "false", "False"}
    if skip_execution:
        message = "Skipping execution because SQLITCH_UAT_SKIP_EXECUTION is set."
        color_print(YELLOW, message)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(f"{header}\n{message}\n", encoding="utf-8")
        return 0

    # Check prerequisites
    print("\nChecking for required commands...")
    for cmd in ("sqitch", "sqlitch", "sqlite3"):
        check_command(cmd)

    # Setup working directory
    print("\nSetting up test environment...")
    cleanup()
    WORK_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(f"{header}\n\n", encoding="utf-8")

    # Execute steps alternating between sqitch and sqlitch
    # For backward compat, we start with sqitch (index 0)
    had_failure = False
    for i, step in enumerate(TUTORIAL_STEPS):
        # Alternate: even indices (0, 2, 4...) use sqitch, odd use sqlitch
        use_sqitch = (i % 2) == 0
        tool_name = "sqitch" if use_sqitch else "sqlitch"
        
        color_print(BLUE, f"\n{'='*60}")
        color_print(BLUE, f"▶️  Step {step.number}: {step.description}")
        color_print(BLUE, f"    Tool: {tool_name}")
        color_print(BLUE, f"{'='*60}")
        
        success, error_msg = execute_step(step, use_sqitch)
        
        if not success:
            color_print(RED, f"\n⛔️ Step {step.number} FAILED: {error_msg}")
            color_print(YELLOW, f"Working directory preserved at: {WORK_DIR}")
            color_print(YELLOW, f"Log file: {LOG_FILE}")
            had_failure = True
            break
        
        color_print(GREEN, f"    ✅ Step {step.number} completed successfully")

    # Write final log
    if had_failure:
        color_print(RED, "\n" + "=" * 60)
        color_print(RED, "  ❌ BACKWARD COMPATIBILITY TEST FAILED")
        color_print(RED, "=" * 60)
        
        # Copy log to output location
        shutil.copy(LOG_FILE, log_path)
        return 1
    else:
        color_print(GREEN, "\n" + "=" * 60)
        color_print(GREEN, "  ✅ ALL STEPS PASSED!")
        color_print(GREEN, "  SQLitch can continue workflows started by Sqitch")
        color_print(GREEN, "=" * 60)
        
        # Sanitize and write final log
        log_content = LOG_FILE.read_text(encoding="utf-8")
        sanitized = sanitization.sanitize_output(log_content)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(sanitized, encoding="utf-8")
        
        # Cleanup
        cleanup()
        color_print(CYAN, "\nTest directory cleaned up.")
        
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        color_print(RED, "\n⛔️ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        color_print(RED, f"\n⛔️ Unexpected error: {e}")
        sys.exit(1)
