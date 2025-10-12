"""Output sanitization helpers shared by UAT harnesses."""

from __future__ import annotations

import re

HEX_ID_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
TS_SECONDS_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}):\d{2}(\.\d+)?([Zz]|[+\-]\d{2}(?::?\d{2})?)?"
)

__all__ = ["sanitize_output"]


def sanitize_output(payload: str) -> str:
    """Redact change identifiers and timestamp seconds in ``payload``.

    The function mirrors the behaviour used by ``uat/side-by-side.py`` so all
    harnesses emit comparable output with cosmetic differences removed.
    Lines beginning with ``# Deployed:`` retain their original content to keep
    parity-diff context for reviewers.
    """

    masked = HEX_ID_RE.sub("[REDACTED_CHANGE_ID]", payload)
    sanitized_lines: list[str] = []

    for line in masked.splitlines(keepends=False):
        if line.lstrip().startswith("# Deployed:"):
            sanitized_lines.append(line)
            continue
        sanitized_lines.append(TS_SECONDS_RE.sub(r"\1:SS\3", line))

    return "\n".join(sanitized_lines)
