"""Unified diff helpers for modified files."""

from __future__ import annotations

import difflib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileDiff:
    path: Path
    diff: str


def generate_diff(original: str, modified: str, filepath: Path) -> FileDiff:
    """Return a unified diff for a single file."""

    # Normalize line endings and split without keeping them
    original_lines = original.replace("\r\n", "\n").splitlines(keepends=False)
    modified_lines = modified.replace("\r\n", "\n").splitlines(keepends=False)

    # Add newlines back for difflib (it expects them for proper output)
    original_lines = [line + "\n" for line in original_lines]
    modified_lines = [line + "\n" for line in modified_lines]

    header_from = f"a/{filepath}"
    header_to = f"b/{filepath}"
    diff_lines = list(difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=header_from,
        tofile=header_to,
    ))

    # Join without extra newlines (unified_diff output already has them)
    diff_text = "".join(diff_lines)
    return FileDiff(path=filepath, diff=diff_text)


def generate_multi_diff(changes: Iterable[FileDiff]) -> str:
    """Combine multiple file diffs into a single patch string."""

    return "\n".join(diff.diff for diff in changes if diff.diff)


def generate_patch_from_files(
    file_changes: Iterable[tuple[Path, str]],
    repo_root: Path,
) -> str:
    """Generate a unified patch from file changes.

    Args:
        file_changes: Iterable of (filepath, new_content) tuples.
        repo_root: Repository root for reading original files.

    Returns:
        Combined unified diff string.
    """
    diffs: list[FileDiff] = []
    for filepath, new_content in file_changes:
        full_path = repo_root / filepath
        if full_path.exists():
            original = full_path.read_text()
        else:
            original = ""
        diff = generate_diff(original, new_content, filepath)
        diffs.append(diff)
    return generate_multi_diff(diffs)


__all__ = ["FileDiff", "generate_diff", "generate_multi_diff", "generate_patch_from_files"]
