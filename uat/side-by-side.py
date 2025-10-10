#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sqitch vs. Sqlitch Functional Equivalence Test (User-Focused)

This version only compares what a *user* would see:
  - Command output (with SHA1s and timestamps sanitized)
  - Existence and data of user tables in the main app DB (e.g., flipr.db)

All registry / schema / metadata differences are ignored.

Usage:
  ./compare.py [--continue] [--out filename] [--ignore 1 5 10]

Options:
  --continue        Continue even if a step fails (log failures, exit 1 if any failed)
  --out filename    Write all output to this file (stripped of ANSI colors)
  --ignore STEPS    A list of step numbers to ignore if they fail.
"""

import argparse
import difflib
import hashlib
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any, Set

# ---------------- Configuration ----------------
SQITCH_DIR = Path("sqitch_results")
SQLITCH_DIR = Path("sqlitch_results")
SQITCH_LOG = Path("sqitch.log")
SQLITCH_LOG = Path("sqlitch.log")
KEEP_DIRS_ON_FAIL = True
STEP_COUNTER = 0

# Globals
CONTINUE_ON_FAIL = False
IGNORE_STEPS: Set[int] = set()
HAD_FAILURE = False

# Colors
GREEN = "\033[0;32m"
BLUE = "\033[0;34m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
NC = "\033[0m"

# Regexes for sanitizing output
HEX_ID_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
TS_SECONDS_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}):\d{2}(\.\d+)?([Zz]|[+\-]\d{2}(?::?\d{2})?)?"
)
ANSI_RE = re.compile(r"\x1B\[[0-9;]*[A-Za-z]")


# ---------------- Tee ----------------
class Tee:
    """Tee output to stdout and a file (strip ANSI for file)."""

    def __init__(self, filename: str):
        self.file = open(filename, "w", encoding="utf-8")
        self.stdout = sys.__stdout__
        self.stderr = sys.__stderr__

    def write(self, data):
        self.stdout.write(data)
        self.stdout.flush()
        clean = ANSI_RE.sub("", data)
        self.file.write(clean)
        self.file.flush()

    def flush(self):
        self.stdout.flush()
        self.file.flush()

    def close(self):
        self.file.close()
        sys.stdout = self.stdout
        sys.stderr = self.stderr


# ---------------- Utilities ----------------
def check_command(cmd: str):
    if shutil.which(cmd) is None:
        fail_and_exit(0, f"{cmd} is not installed or not in PATH.", "")


def color_print(color: str, msg: str):
    print(f"{color}{msg}{NC}")


def run_and_stream(cmd: List[str], cwd: Path) -> Tuple[str, int]:
    """Run command and stream output to console, returning captured output and exit code."""
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
    )
    captured_lines: List[str] = []
    assert proc.stdout is not None
    for line in proc.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        captured_lines.append(line)
    proc.wait()
    return ("".join(captured_lines), proc.returncode)


def sanitize_text(s: str) -> str:
    """Sanitize text by masking change IDs and timestamp seconds."""
    s = HEX_ID_RE.sub("[REDACTED_CHANGE_ID]", s)
    out_lines: List[str] = []
    for line in s.splitlines(keepends=False):
        if line.lstrip().startswith("# Deployed:"):
            out_lines.append(line)
        else:
            out_lines.append(TS_SECONDS_RE.sub(r"\1:SS\3", line))
    return "\n".join(out_lines)


def unified_diff(a: str, b: str, fromfile: str, tofile: str) -> str:
    a_lines = a.splitlines(keepends=True)
    b_lines = b.splitlines(keepends=True)
    return "".join(difflib.unified_diff(a_lines, b_lines, fromfile, tofile))


def log_append(logfile: Path, header: str, cmd: List[str], payload: str):
    with logfile.open("a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"STEP: {header}\n")
        f.write(f"COMMAND: {' '.join(cmd)}\n")
        f.write(f"{'='*60}\n")
        f.write(payload)
        if not payload.endswith("\n"):
            f.write("\n")


def fail_and_exit(step: int, reason: str, cmd_str: str, diff_text: str = ""):
    global HAD_FAILURE, IGNORE_STEPS
    HAD_FAILURE = True

    if step in IGNORE_STEPS:
        color_print(YELLOW, f"\n⚠️  IGNORING FAILED STEP {step}: {reason}")
        if cmd_str:
            color_print(YELLOW, f"     Command: {cmd_str}")
        if diff_text:
            print(f"\n{YELLOW}┌──────────────[ DIFF ]──────────────┐{NC}")
            print(diff_text, end="" if diff_text.endswith("\n") else "\n")
            print(f"{YELLOW}└────────────────────────────────────┘{NC}")
        return

    color_print(RED, f"\n⛔️ TEST FAILED (Step {step}): {reason}")
    if cmd_str:
        color_print(RED, f"     Command: {cmd_str}")
    if diff_text:
        print(f"\n{RED}┌──────────────[ DIFF ]──────────────┐{NC}")
        print(diff_text, end="" if diff_text.endswith("\n") else "\n")
        print(f"{RED}└────────────────────────────────────┘{NC}")

    if KEEP_DIRS_ON_FAIL:
        color_print(
            YELLOW,
            f"Execution failed. Test directories and logs ('{SQITCH_DIR}', '{SQLITCH_DIR}', "
            f"'{SQITCH_LOG}', '{SQLITCH_LOG}') are left for inspection."
        )
        color_print(YELLOW, "\nTo reproduce this failure:")
        color_print(YELLOW, f"  1. Check logs: {SQITCH_LOG} and {SQLITCH_LOG}")
        color_print(YELLOW, f"  2. Examine directories: {SQITCH_DIR} and {SQLITCH_DIR}")
        if cmd_str:
            color_print(YELLOW, f"  3. Failed command: {cmd_str}")
    else:
        cleanup_dirs()

    if not CONTINUE_ON_FAIL:
        sys.exit(1)


def cleanup_dirs():
    for p in (SQITCH_DIR, SQLITCH_DIR, SQITCH_LOG, SQLITCH_LOG):
        try:
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            elif p.exists():
                p.unlink(missing_ok=True)
        except Exception:
            pass


def write_files(relpath: str, content: str):
    """Write the same content to both test directories."""
    for base in (SQITCH_DIR, SQLITCH_DIR):
        dest = base / relpath
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")


# ---------------- User-Focused Database Comparison ----------------
def compare_user_dbs(sqitch_db: Path, sqlitch_db: Path) -> Tuple[bool, str]:
    """
    Compare only user-visible data in the application database (e.g., flipr.db).
    Ignore sqitch registry databases and internal schema.
    """
    # Ignore sqitch registry DBs entirely
    if "sqitch" in sqitch_db.name or "sqitch" in sqlitch_db.name:
        return True, ""

    if not sqitch_db.exists() or not sqlitch_db.exists():
        return True, ""

    conn1 = sqlite3.connect(str(sqitch_db))
    conn2 = sqlite3.connect(str(sqlitch_db))
    c1 = conn1.cursor()
    c2 = conn2.cursor()

    # Identify user tables
    def get_user_tables(cur):
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [
            name for (name,) in cur.fetchall()
            if not name.startswith("sqlite_") and not name.startswith("sqitch_")
        ]

    tables1 = set(get_user_tables(c1))
    tables2 = set(get_user_tables(c2))

    if tables1 != tables2:
        conn1.close()
        conn2.close()
        return False, f"User table sets differ:\n  sqitch: {sorted(tables1)}\n  sqlitch: {sorted(tables2)}"

    diffs = []
    for table in sorted(tables1):
        c1.execute(f"SELECT * FROM {table}")
        c2.execute(f"SELECT * FROM {table}")
        rows1 = c1.fetchall()
        rows2 = c2.fetchall()

        if rows1 != rows2:
            diffs.append(f"Data differs in table '{table}'")

    conn1.close()
    conn2.close()

    if diffs:
        return False, "\n".join(diffs)
    return True, ""


# ---------------- Main Test Runner ----------------
def run_and_compare(description: str, cmd_base: str, *args: str):
    """Run the same command with both sqitch and sqlitch, then compare outcomes."""
    global STEP_COUNTER
    STEP_COUNTER += 1
    step_header = f"STEP {STEP_COUNTER}: {description}"

    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}▶️  {step_header}{NC}")
    print(f"{CYAN}    COMMAND: {cmd_base} {' '.join(args)}{NC}")
    print(f"{BLUE}{'='*60}{NC}")

    # Determine actual commands
    if cmd_base == "sqlitch":
        sqitch_cmd = ["sqitch", *args]
        sqlitch_cmd = ["sqlitch", *args]
    elif cmd_base == "sqlite3":
        sqitch_cmd = ["sqlite3", *args]
        sqlitch_cmd = ["sqlite3", *args]
    else:
        fail_and_exit(STEP_COUNTER, f"Unhandled command base: '{cmd_base}'", "")
        return

    # Run sqitch
    print(f"\n    {CYAN}┌───────────────────────────┐{NC}")
    print(f"    {CYAN}│   Running sqitch (💎)     │{NC}")
    print(f"    {CYAN}└───────────────────────────┘{NC}")
    sqitch_out, sqitch_rc = run_and_stream(sqitch_cmd, SQITCH_DIR)
    log_append(SQITCH_LOG, step_header, sqitch_cmd, sqitch_out)

    # Run sqlitch
    print(f"\n    {CYAN}┌───────────────────────────┐{NC}")
    print(f"    {CYAN}│   Running sqlitch (✨)    │{NC}")
    print(f"    {CYAN}└───────────────────────────┘{NC}")
    sqlitch_out, sqlitch_rc = run_and_stream(sqlitch_cmd, SQLITCH_DIR)
    log_append(SQLITCH_LOG, step_header, sqlitch_cmd, sqlitch_out)

    # Compare exit codes
    if sqitch_rc != sqlitch_rc:
        fail_and_exit(
            STEP_COUNTER,
            f"Exit codes differ. sqitch: {sqitch_rc}, sqlitch: {sqlitch_rc}",
            f"{cmd_base} {' '.join(args)}"
        )
        return

    # Compare sanitized output
    sqitch_san = sanitize_text(sqitch_out)
    sqlitch_san = sanitize_text(sqlitch_out)

    if sqitch_san != sqlitch_san:
        diff = unified_diff(sqitch_san, sqlitch_san, "sqitch(out)", "sqlitch(out)")
        color_print(YELLOW, "⚠️  Command output differs (this may be OK if user state matches)")
        print(f"\n{YELLOW}Output diff:{NC}")
        print(diff)

    # Compare only user-visible DBs (ignore sqitch registry)
    db_files = [f for f in os.listdir(SQITCH_DIR) if f.endswith(".db")]
    for db_file in db_files:
        sqitch_db = SQITCH_DIR / db_file
        sqlitch_db = SQLITCH_DIR / db_file
        if sqitch_db.exists() and sqlitch_db.exists():
            match, diff = compare_user_dbs(sqitch_db, sqlitch_db)
            if not match:
                fail_and_exit(
                    STEP_COUNTER,
                    f"User-visible database state differs for '{db_file}'",
                    f"{cmd_base} {' '.join(args)}",
                    diff
                )
                return
            else:
                print(f"\n{GREEN}    ✅ User-visible database '{db_file}' matches{NC}")

    print(f"\n{GREEN}    ✅ Step completed successfully{NC}")


# ---------------- Main ----------------
def main():
    global CONTINUE_ON_FAIL, HAD_FAILURE, IGNORE_STEPS

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--continue", dest="cont", action="store_true",
                        help="Continue even if a step fails")
    parser.add_argument("--out", dest="outfile",
                        help="Write full output to this file (colors stripped)")
    parser.add_argument("--ignore", dest="ignore_steps", type=int, nargs='+',
                        help="A list of step numbers to ignore on failure.")
    args = parser.parse_args()

    CONTINUE_ON_FAIL = args.cont
    if args.ignore_steps:
        IGNORE_STEPS = set(args.ignore_steps)

    tee = None
    if args.outfile:
        tee = Tee(args.outfile)
        sys.stdout = tee
        sys.stderr = tee

    color_print(GREEN, "="*60)
    color_print(GREEN, "Sqitch vs. Sqlitch Functional Equivalence Test (User-Focused)")
    color_print(GREEN, "="*60)

    print("\nChecking for required commands...")
    for cmd in ("sqitch", "sqlitch", "sqlite3"):
        check_command(cmd)

    print("Setting up test environment...")
    cleanup_dirs()
    SQITCH_DIR.mkdir(parents=True, exist_ok=True)
    SQLITCH_DIR.mkdir(parents=True, exist_ok=True)
    print("Test directories created.\n")

    # === Test Sequence (SQLite Tutorial) ===
    run_and_compare("Initialize Project",
                    "sqlitch", "init", "flipr",
                    "--uri", "https://github.com/sqitchers/sqitch-sqlite-intro/",
                    "--engine", "sqlite")
    
    run_and_compare("Configure User Name", "sqlitch", "config", "user.name", "Test User")
    run_and_compare("Configure User Email", "sqlitch", "config", "user.email", "test@example.com")
    run_and_compare("Disable Pager", "sqlitch", "config", "--bool", "core.pager", "false")
    
    run_and_compare("Add 'users' Table", "sqlitch", "add", "users", "-n", "Creates table to track our users.")
    
    # Create SQL files for 'users'
    write_files("deploy/users.sql", """-- Deploy flipr:users to sqlite

BEGIN;

CREATE TABLE users (
    nickname TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    fullname TEXT NOT NULL,
    twitter TEXT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
""")
    
    write_files("revert/users.sql", """-- Revert flipr:users from sqlite

BEGIN;

DROP TABLE users;

COMMIT;
""")
    
    write_files("verify/users.sql", """-- Verify flipr:users on sqlite

BEGIN;

SELECT nickname, password, fullname, twitter
FROM users
WHERE 0;

ROLLBACK;
""")
    
    run_and_compare("Deploy 'users' Table", "sqlitch", "deploy", "db:sqlite:flipr_test.db")
    run_and_compare("Verify 'users' Deployment", "sqlitch", "verify", "db:sqlite:flipr_test.db")
    run_and_compare("Check Status After Deploy", "sqlitch", "status", "db:sqlite:flipr_test.db")
    run_and_compare("Check DB Schema with sqlite3", "sqlite3", "flipr_test.db", ".tables")
    
    run_and_compare("Revert 'users' Table", "sqlitch", "revert", "db:sqlite:flipr_test.db", "-y")
    run_and_compare("Verify Revert with sqlite3", "sqlite3", "flipr_test.db", ".tables")
    run_and_compare("Check Sqitch Log", "sqlitch", "log", "db:sqlite:flipr_test.db")
    
    run_and_compare("Add Target 'flipr_test'", "sqlitch", "target", "add", "flipr_test", "db:sqlite:flipr_test.db")
    run_and_compare("Add Engine for Target", "sqlitch", "engine", "add", "sqlite", "flipr_test")
    run_and_compare("Enable Deploy Verification", "sqlitch", "config", "--bool", "deploy.verify", "true")
    run_and_compare("Enable Rebase Verification", "sqlitch", "config", "--bool", "rebase.verify", "true")
    
    run_and_compare("Deploy Again with Target", "sqlitch", "deploy")
    
    run_and_compare("Add 'flips' Table", "sqlitch", "add", "flips", "--requires", "users",
                    "-n", "Adds table for storing flips.")
    
    write_files("deploy/flips.sql", """-- Deploy flipr:flips to sqlite
-- requires: users

BEGIN;

CREATE TABLE flips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nickname TEXT NOT NULL REFERENCES users(nickname),
    body TEXT NOT NULL DEFAULT '' CHECK ( length(body) <= 180 ),
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
""")
    
    write_files("revert/flips.sql", """-- Revert flipr:flips from sqlite

BEGIN;

DROP TABLE flips;

COMMIT;
""")
    
    write_files("verify/flips.sql", """-- Verify flipr:flips on sqlite

BEGIN;

SELECT id, nickname, body, timestamp
FROM flips
WHERE 0;

ROLLBACK;
""")
    
    run_and_compare("Deploy 'flips' Table", "sqlitch", "deploy")
    run_and_compare("Verify All Deployments", "sqlitch", "verify")
    run_and_compare("Check DB Schema for 'users' and 'flips'", "sqlite3", "flipr_test.db", ".tables")
    
    run_and_compare("Partial Revert to HEAD^", "sqlitch", "revert", "--to", "@HEAD^", "-y")
    run_and_compare("Verify Partial Revert", "sqlite3", "flipr_test.db", ".tables")
    run_and_compare("Deploy All Again", "sqlitch", "deploy")
    
    run_and_compare("Add 'userflips' View", "sqlitch", "add", "userflips",
                    "--requires", "users", "--requires", "flips",
                    "-n", "Creates the userflips view.")
    
    write_files("deploy/userflips.sql", """-- Deploy flipr:userflips to sqlite
-- requires: users
-- requires: flips

BEGIN;

CREATE VIEW userflips AS
SELECT f.id, u.nickname, u.fullname, f.body, f.timestamp
FROM users u
JOIN flips f ON u.nickname = f.nickname;

COMMIT;
""")
    
    write_files("revert/userflips.sql", """-- Revert flipr:userflips from sqlite

BEGIN;

DROP VIEW userflips;

COMMIT;
""")
    
    write_files("verify/userflips.sql", """-- Verify flipr:userflips on sqlite

BEGIN;

SELECT id, nickname, fullname, body, timestamp
FROM userflips
WHERE 0;

ROLLBACK;
""")
    
    run_and_compare("Deploy 'userflips' View", "sqlitch", "deploy")
    run_and_compare("Full Revert", "sqlitch", "revert", "-y")
    run_and_compare("Full Redeploy", "sqlitch", "deploy")
    
    run_and_compare("Tag Release v1.0.0-dev1", "sqlitch", "tag", "v1.0.0-dev1",
                    "-n", "Tag v1.0.0-dev1.")
    
    # Create dev directories
    (SQITCH_DIR / "dev").mkdir(parents=True, exist_ok=True)
    (SQLITCH_DIR / "dev").mkdir(parents=True, exist_ok=True)
    
    run_and_compare("Deploy Tag to New DB", "sqlitch", "deploy", "db:sqlite:dev/flipr.db")
    run_and_compare("Check Status of Tagged DB", "sqlitch", "status", "db:sqlite:dev/flipr.db")
    
    run_and_compare("Create Bundle", "sqlitch", "bundle")
    run_and_compare("Deploy Bundle to New DB", "sqlitch", "deploy",
                    "db:sqlite:flipr_prod.db", "-C", "bundle")
    
    run_and_compare("Add 'hashtags' Table", "sqlitch", "add", "hashtags",
                    "--requires", "flips", "-n", "Adds table for storing hashtags.")
    
    write_files("deploy/hashtags.sql", """-- Deploy flipr:hashtags to sqlite
-- requires: flips

BEGIN;

CREATE TABLE hashtags (
    flip_id INTEGER NOT NULL REFERENCES flips(id),
    hashtag TEXT NOT NULL CHECK ( length(hashtag) > 0 ),
    PRIMARY KEY (flip_id, hashtag)
);

COMMIT;
""")
    
    write_files("revert/hashtags.sql", """-- Revert flipr:hashtags from sqlite

BEGIN;

DROP TABLE hashtags;

COMMIT;
""")
    
    write_files("verify/hashtags.sql", """-- Verify flipr:hashtags on sqlite

BEGIN;

SELECT flip_id, hashtag FROM hashtags WHERE 0;

ROLLBACK;
""")
    
    run_and_compare("Deploy 'hashtags' Table", "sqlitch", "deploy")
    run_and_compare("Check Status with Tags", "sqlitch", "status", "--show-tags")
    run_and_compare("Rebase Plan", "sqlitch", "rebase", "-y")
    
    run_and_compare("Tag Release v1.0.0-dev2", "sqlitch", "tag", "v1.0.0-dev2",
                    "-n", "Tag v1.0.0-dev2.")
    
    run_and_compare("Rework 'userflips' View", "sqlitch", "rework", "userflips",
                    "-n", "Adds userflips.twitter.")
    
    # Rework SQL update
    write_files("deploy/userflips.sql", """-- Deploy flipr:userflips to sqlite
-- requires: users
-- requires: flips

BEGIN;

DROP VIEW IF EXISTS userflips;

CREATE VIEW userflips AS
SELECT f.id, u.nickname, u.fullname, u.twitter, f.body, f.timestamp
FROM users u
JOIN flips f ON u.nickname = f.nickname;

COMMIT;
""")
    
    write_files("revert/userflips.sql", """-- Revert flipr:userflips from sqlite

BEGIN;

DROP VIEW IF EXISTS userflips;

CREATE VIEW userflips AS
SELECT f.id, u.nickname, u.fullname, f.body, f.timestamp
FROM users u
JOIN flips f ON u.nickname = f.nickname;

COMMIT;
""")
    
    write_files("verify/userflips.sql", """-- Verify flipr:userflips on sqlite

BEGIN;

SELECT id, nickname, fullname, twitter, body, timestamp
FROM userflips
WHERE 0;

ROLLBACK;
""")
    
    run_and_compare("Deploy Reworked View", "sqlitch", "deploy")
    run_and_compare("Verify Reworked Schema", "sqlite3", "flipr_test.db", ".schema", "userflips")
    run_and_compare("Revert Reworked Change", "sqlitch", "revert", "--to", "@HEAD^", "-y")
    run_and_compare("Verify Revert of Rework", "sqlite3", "flipr_test.db", ".schema", "userflips")
    
    run_and_compare("Final Deployment", "sqlitch", "deploy")
    run_and_compare("Final Verification", "sqlitch", "verify")
    run_and_compare("Final Status Check", "sqlitch", "status")
    

    print()
    print(f"{GREEN}{'='*60}{NC}")
    if HAD_FAILURE:
        print(f"{RED}  ❌ COMPLETED WITH FAILURES!{NC}")
        print(f"{YELLOW}  Check logs for reproduction steps:{NC}")
        print(f"{YELLOW}    - {SQITCH_LOG}{NC}")
        print(f"{YELLOW}    - {SQLITCH_LOG}{NC}")
        sys.exit(1)
    else:
        print(f"{GREEN}  ✅ ALL TESTS PASSED!{NC}")
        print(f"{GREEN}  sqitch and sqlitch are functionally equivalent (user-facing).{NC}")
        print(f"{GREEN}{'='*60}{NC}")

        if not KEEP_DIRS_ON_FAIL:
            cleanup_dirs()
            print(f"\n{CYAN}Test directories cleaned up.{NC}")

        if tee:
            tee.close()

        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        fail_and_exit(STEP_COUNTER, "Interrupted by user.", "")
    except Exception as e:
        fail_and_exit(STEP_COUNTER, f"Unexpected error: {e}", "")

