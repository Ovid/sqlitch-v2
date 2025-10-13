"""SQLitch CLI entry point for direct execution.

This module enables running SQLitch directly from source with:
    python src/sqlitch

Due to the src layout, we need to manipulate sys.path to make the package
importable when running directly from source tree (before installation).
"""

from __future__ import annotations

import os
import sys

# Make CLI runnable from source tree with: python src/sqlitch
# This is a workaround for src layout before editable installation
if not __package__:
    package_source_path = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, package_source_path)

from sqlitch.cli.main import main  # noqa: E402

if __name__ == "__main__":
    main()
