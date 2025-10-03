#!/usr/bin/env python3
"""Fail fast when active implementation tasks still have skipped tests."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping
import ast

DEFAULT_TEST_PATHS = ("tests", "xt")
ENV_TASKS = "SQLITCH_ACTIVE_TASKS"


@dataclass(frozen=True)
class SkipHit:
    task_id: str
    file_path: Path
    line: int
    snippet: str


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that skip markers referencing the supplied task identifiers have been "
            "removed before starting implementation work."
        )
    )
    parser.add_argument(
        "tasks",
        metavar="TASK",
        nargs="*",
        help="Task identifiers such as T052. If omitted, values from the SQLITCH_ACTIVE_TASKS env var are used.",
    )
    parser.add_argument(
        "--paths",
        metavar="PATH",
        nargs="*",
        default=list(DEFAULT_TEST_PATHS),
        help="Directories to scan for pytest tests (default: %(default)s).",
    )
    parser.add_argument(
        "--fail-empty",
        action="store_true",
        help="Fail if no task identifiers are supplied after considering the environment variable.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Emit additional debugging information during the scan.",
    )
    return parser.parse_args(list(argv))


def normalise_tasks(values: Iterable[str]) -> list[str]:
    tasks: list[str] = []
    for value in values:
        if not value:
            continue
        for piece in value.replace(";", ",").split(","):
            candidate = piece.strip()
            if not candidate:
                continue
            tasks.append(candidate.upper())
    return sorted(set(tasks))


def load_tasks_from_env() -> list[str]:
    raw = os.environ.get(ENV_TASKS, "")
    return normalise_tasks([raw])


def gather_task_ids(args: argparse.Namespace) -> list[str]:
    tasks = normalise_tasks(args.tasks)
    env_tasks = load_tasks_from_env()
    combined = tasks or env_tasks
    if args.verbose:
        sys.stderr.write(f"[check-skips] CLI tasks: {tasks}, env tasks: {env_tasks}\n")
    if not combined and args.fail_empty:
        sys.stderr.write(
            "[check-skips] No task identifiers were supplied. Provide them via CLI arguments or the "
            f"{ENV_TASKS} environment variable.\n"
        )
        sys.exit(1)
    return combined


def literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                return None
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = literal_string(node.left)  # type: ignore[attr-defined]
        right = literal_string(node.right)  # type: ignore[attr-defined]
        if left is not None and right is not None:
            return left + right
    return None


def collect_string_bindings(tree: ast.AST) -> Mapping[str, str]:
    bindings: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            value = literal_string(node.value)
            if value is not None:
                bindings.setdefault(node.targets[0].id, value)
        elif isinstance(node, ast.AnnAssign):
            if not isinstance(node.target, ast.Name):
                continue
            value = literal_string(node.value)
            if value is not None:
                bindings.setdefault(node.target.id, value)
    return bindings


def resolved_string(node: ast.AST, bindings: Mapping[str, str]) -> str | None:
    direct = literal_string(node)
    if direct is not None:
        return direct
    if isinstance(node, ast.Name):
        return bindings.get(node.id)
    return None


def is_skip_call(func: ast.AST) -> bool:
    if isinstance(func, ast.Attribute):
        # pytest.skip(...) or pytest.mark.skip(...)
        name = func.attr
        if name != "skip":
            return False
        value = func.value
        if isinstance(value, ast.Name) and value.id == "pytest":
            return True
        if isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name):
            return value.attr == "mark" and value.value.id == "pytest"
        return False
    if isinstance(func, ast.Name):
        return func.id == "skip"  # from pytest import skip
    return False


def iter_skip_hits(content: str, path: Path, tasks: Iterable[str]) -> Iterable[SkipHit]:
    if not tasks:
        return []
    try:
        tree = ast.parse(content, filename=str(path))
    except SyntaxError as exc:  # pragma: no cover - Pytest would fail sooner, but be defensive.
        raise RuntimeError(f"Unable to parse {path}: {exc}") from exc

    bindings = collect_string_bindings(tree)
    tasks = list(tasks)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and is_skip_call(node.func):
            string_candidates: list[str] = []
            for arg in node.args:
                resolved = resolved_string(arg, bindings)
                if resolved is not None:
                    string_candidates.append(resolved)
            for keyword in node.keywords:
                if keyword.arg in {None, "reason", "msg"}:
                    resolved = resolved_string(keyword.value, bindings)
                    if resolved is not None:
                        string_candidates.append(resolved)
            if not string_candidates:
                continue
            for task in tasks:
                for candidate in string_candidates:
                    if task in candidate:
                        line = getattr(node, "lineno", 1)
                        snippet = candidate.strip()
                        yield SkipHit(task, path, line, snippet)
        elif isinstance(node, ast.Attribute):
            # Handle bare @pytest.mark.skip without parentheses.
            if (
                node.attr == "skip"
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "mark"
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "pytest"
            ):
                for task in tasks:
                    yield SkipHit(task, path, getattr(node, "lineno", 1), "@pytest.mark.skip")


def discover_python_files(paths: Iterable[str]) -> Iterable[Path]:
    for raw in paths:
        base = Path(raw)
        if not base.exists():
            continue
        if base.is_file() and base.suffix == ".py":
            yield base
        else:
            for file_path in base.rglob("*.py"):
                if file_path.is_file():
                    yield file_path


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    tasks = gather_task_ids(args)

    if not tasks:
        if args.verbose:
            sys.stderr.write(
                "[check-skips] No tasks provided; skipping scan (set --fail-empty to make this an error).\n"
            )
        return 0

    if args.verbose:
        sys.stderr.write(f"[check-skips] Checking for tasks: {', '.join(tasks)}\n")

    hits: list[SkipHit] = []
    for file_path in discover_python_files(args.paths):
        content = file_path.read_text(encoding="utf-8")
        if not any(task in content for task in tasks):
            continue
        hits.extend(iter_skip_hits(content, file_path, tasks))

    if not hits:
        if args.verbose:
            sys.stderr.write("[check-skips] No offending skip markers detected.\n")
        return 0

    sys.stderr.write("Detected skip markers referencing active tasks:\n")
    for hit in hits:
        rel_path = hit.file_path.relative_to(Path.cwd()) if hit.file_path.is_absolute() else hit.file_path
        sys.stderr.write(f"  - {rel_path}:{hit.line} -> {hit.task_id}: {hit.snippet}\n")
    sys.stderr.write(
        "Remove these skip markers (or update the active task list) before proceeding with implementation.\n"
    )
    return 1


if __name__ == "__main__":  # pragma: no cover - exercised via CLI
    raise SystemExit(main(sys.argv[1:]))
