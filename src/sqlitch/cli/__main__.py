"""Allow `python -m sqlitch.cli` execution."""

from __future__ import annotations

from .main import main

if __name__ == "__main__":
    # pylint: disable=missing-kwoa,no-value-for-parameter
    # Click decorator injects parameters at runtime
    main()
