"""Parity tests for packaged SQLite templates."""

from __future__ import annotations

from pathlib import Path

import pytest

from sqlitch.plan.formatter import compute_checksum

pytestmark = pytest.mark.skip(reason="Pending template packaging (see T012h)")


REPO_ROOT = Path(__file__).resolve().parents[2]
SQLITCH_TEMPLATE_DIR = REPO_ROOT / "sqlitch" / "templates" / "sqlite"

# Sqitch-derived SHA-256 digests captured via compute_checksum to provide
# deterministic parity checks without reading the vendored Sqitch tree at test
# time. Update these only when upstream templates change.
EXPECTED_CHECKSUMS: dict[str, str] = {
    "deploy": "08e23e467eb7b1433e7aef38aaa8f30c49cb48909985968333b73d45400d923f",
    "revert": "b7f0663019aafd805c253598fa993fb4ec044fc570c5a6ad8e1861d521cc8125",
    "verify": "8de4b0a48d52e37b5c68bf003999d7a008434e668c7ec4ad6d037402e1f7c2aa",
}


@pytest.mark.parametrize("kind", sorted(EXPECTED_CHECKSUMS))
def test_sqlite_templates_match_sqitch(kind: str) -> None:
    """Packaged SQLite templates must remain byte-identical to Sqitch."""

    sqlitch_template = SQLITCH_TEMPLATE_DIR / f"{kind}.tmpl"

    assert sqlitch_template.exists(), f"Missing SQLitch template: {sqlitch_template}"

    sqlitch_checksum = compute_checksum(sqlitch_template.read_text(encoding="utf-8"))

    assert sqlitch_checksum == EXPECTED_CHECKSUMS[kind], (
        "SQLite template diverged from Sqitch fixture; regenerate from upstream or"
        f" replace {sqlitch_template.relative_to(REPO_ROOT)}"
    )
