#!/usr/bin/env python3
"""sqitch → sqlitch backward compatibility harness placeholder."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Iterable

import sys

if __package__ in {None, ""}:
    PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
    if str(PACKAGE_ROOT) not in sys.path:
        sys.path.insert(0, str(PACKAGE_ROOT))
    from uat import sanitization
    from uat.test_steps import TUTORIAL_STEPS
else:
    from .. import sanitization
    from ..test_steps import TUTORIAL_STEPS

_SKIP_ENV = "SQLITCH_UAT_SKIP_EXECUTION"


def _write_log(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line.rstrip("\n"))
            handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out", required=True, metavar="PATH", help="Destination file for sanitized log output"
    )
    args = parser.parse_args()

    log_path = Path(args.out).expanduser()

    header = "Backward compatibility harness (sqitch → sqlitch)"
    print(header)

    skip_execution = os.getenv(_SKIP_ENV, "").strip() not in {"", "0", "false", "False"}
    if skip_execution:
        message = (
            "Skipping execution because SQLITCH_UAT_SKIP_EXECUTION is set."
        )
        print(message)
        _write_log(log_path, [header, message])
        return 0

    placeholder = (
        "Backward compatibility execution is not yet implemented. "
        "Set SQLITCH_UAT_SKIP_EXECUTION=1 during development or implement T117."
    )
    print(placeholder)
    sanitized = sanitization.sanitize_output(placeholder)
    _write_log(log_path, [header, sanitized])

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
