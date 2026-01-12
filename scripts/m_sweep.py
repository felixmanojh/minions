#!/usr/bin/env python3
"""Sweep codebase for files needing polish and batch-fix them."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Auto-bootstrap venv and dependencies
from llm_gc.bootstrap import ensure_venv
ensure_venv()

import argparse
import ast
import asyncio
import json
from dataclasses import dataclass, field


@dataclass
class FileCandidate:
    """A file that needs polish."""
    file: str
    lines: int
    missing: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str | None = None


def check_missing_docstrings(filepath: Path) -> list[str]:
    """Check what a file is missing."""
    missing = []

    try:
        content = filepath.read_text()
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return []

    # Check module docstring
    if not ast.get_docstring(tree):
        missing.append("module docstring")

    # Check functions and classes
    funcs_without_docs = 0
    classes_without_docs = 0

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            if not ast.get_docstring(node) and not node.name.startswith("_"):
                funcs_without_docs += 1
        elif isinstance(node, ast.ClassDef):
            if not ast.get_docstring(node):
                classes_without_docs += 1

    if funcs_without_docs:
        missing.append(f"{funcs_without_docs} functions without docstrings")
    if classes_without_docs:
        missing.append(f"{classes_without_docs} classes without docstrings")

    return missing


def check_missing_types(filepath: Path) -> list[str]:
    """Check for missing type hints."""
    missing = []

    try:
        content = filepath.read_text()
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return []

    funcs_without_types = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            # Check return annotation
            has_return = node.returns is not None
            # Check at least one arg has annotation
            has_args = any(
                arg.annotation is not None
                for arg in node.args.args
                if arg.arg != "self"
            )
            if not has_return and not has_args:
                funcs_without_types += 1

    if funcs_without_types:
        missing.append(f"{funcs_without_types} functions without type hints")

    return missing


def discover_candidates(
    directory: Path,
    task: str,
    max_lines: int = 500,
) -> tuple[list[FileCandidate], list[FileCandidate]]:
    """Discover files that need polish.

    Returns:
        Tuple of (candidates, skipped)
    """
    candidates = []
    skipped = []

    for filepath in directory.rglob("*.py"):
        # Skip common non-source directories
        parts = filepath.parts
        if any(p in parts for p in [".venv", "venv", "__pycache__", ".git", "node_modules", "build", "dist"]):
            continue

        try:
            content = filepath.read_text()
            line_count = len(content.splitlines())
        except (OSError, UnicodeDecodeError):
            continue

        candidate = FileCandidate(
            file=str(filepath.relative_to(directory)),
            lines=line_count,
        )

        # Check size limit
        if line_count > max_lines:
            candidate.skipped = True
            candidate.skip_reason = f">{max_lines} lines"
            skipped.append(candidate)
            continue

        # Check what's missing based on task
        if task in ("docstrings", "all"):
            candidate.missing.extend(check_missing_docstrings(filepath))
        if task in ("types", "all"):
            candidate.missing.extend(check_missing_types(filepath))
        if task == "headers":
            try:
                tree = ast.parse(content)
                if not ast.get_docstring(tree):
                    candidate.missing.append("module docstring")
            except SyntaxError:
                pass

        if candidate.missing:
            candidates.append(candidate)

    return candidates, skipped


async def run_sweep(
    directory: Path,
    task: str,
    apply: bool = False,
    max_lines: int = 500,
    preset: str | None = None,
    num_ctx: int | None = None,
    backup: bool = False,
    no_lint: bool = False,
    no_validate: bool = False,
    lint_cmd: str | None = None,
    max_retries: int | None = None,
) -> dict:
    """Sweep directory for files needing polish."""
    candidates, skipped = discover_candidates(directory, task, max_lines)

    result = {
        "candidates": [
            {"file": c.file, "lines": c.lines, "missing": c.missing}
            for c in candidates
        ],
        "skipped": [
            {"file": s.file, "reason": s.skip_reason}
            for s in skipped
        ],
        "total_candidates": len(candidates),
        "total_skipped": len(skipped),
    }

    if not apply:
        return result

    # Apply polish to all candidates
    from scripts.m_polish import run_polish

    files = [directory / c.file for c in candidates]
    if not files:
        result["applied"] = True
        result["files_modified"] = 0
        result["changes"] = []
        return result

    polish_result = await run_polish(
        files=files,
        task=task,
        preset=preset,
        num_ctx=num_ctx,
        backup=backup,
        no_lint=no_lint,
        no_validate=no_validate,
        lint_cmd=lint_cmd,
        max_retries=max_retries,
    )

    result["applied"] = polish_result["applied"]
    result["files_modified"] = len(polish_result["files_modified"])
    result["changes"] = polish_result["changes"]
    result["errors"] = polish_result["errors"]
    result["stats"] = polish_result["stats"]

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep codebase for files needing polish"
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Directory to sweep",
    )
    parser.add_argument(
        "--task",
        default="all",
        choices=["docstrings", "types", "headers", "all"],
        help="What to check for (default: all)",
    )
    parser.add_argument(
        "--discover",
        action="store_true",
        help="Only discover, don't apply (default)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply polish to discovered files",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=500,
        help="Skip files larger than this (default: 500)",
    )
    parser.add_argument(
        "--preset",
        choices=["lite", "medium", "large"],
        default=None,
        help="Model preset",
    )
    parser.add_argument(
        "--num-ctx",
        type=int,
        default=None,
        help="Context window size",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create .bak backup before modifying",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON result",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    result = await run_sweep(
        directory=args.directory,
        task=args.task,
        apply=args.apply,
        max_lines=args.max_lines,
        preset=args.preset,
        num_ctx=args.num_ctx,
        backup=args.backup,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\n=== Sweep Results ===")
        print(f"Candidates: {result['total_candidates']}")
        print(f"Skipped: {result['total_skipped']}")

        if result["candidates"]:
            print(f"\nFiles needing polish:")
            for c in result["candidates"][:10]:
                print(f"  {c['file']} ({c['lines']} lines): {', '.join(c['missing'])}")
            if len(result["candidates"]) > 10:
                print(f"  ... and {len(result['candidates']) - 10} more")

        if args.apply and "stats" in result:
            print(f"\nApplied: {result['stats']['applied']}/{result['stats']['total']}")


if __name__ == "__main__":
    asyncio.run(main())
