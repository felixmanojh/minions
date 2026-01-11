"""Robust patch application with fallback strategies.

Inspired by Aider's flexible search/replace with multiple strategies.
"""

from __future__ import annotations

import difflib
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from diff_match_patch import diff_match_patch


@dataclass
class PatchAttempt:
    """Result of a patch attempt."""

    success: bool
    result: str | None = None
    strategy: str | None = None
    error: str | None = None


def apply_exact_patch(original: str, search: str, replace: str) -> str | None:
    """Try exact string replacement."""
    if search in original:
        return original.replace(search, replace, 1)
    return None


def apply_fuzzy_patch(
    original: str,
    search: str,
    replace: str,
    threshold: float = 0.6,
) -> str | None:
    """Try fuzzy matching with diff-match-patch.

    Args:
        original: Original file content
        search: Text to search for
        replace: Text to replace with
        threshold: Match threshold (0-1, lower = more fuzzy)

    Returns:
        Modified content or None if no match found
    """
    dmp = diff_match_patch()
    dmp.Match_Threshold = threshold

    # Try to find a fuzzy match
    location = dmp.match_main(original, search, 0)

    if location == -1:
        return None

    # Found a match - apply the replacement
    # Find the actual matched text by looking for similar length
    match_end = location + len(search)

    # Adjust end to find actual match boundaries
    # Look for best matching substring
    best_ratio = 0
    best_end = match_end

    for end in range(match_end - 20, match_end + 20):
        if end <= location or end > len(original):
            continue
        candidate = original[location:end]
        ratio = difflib.SequenceMatcher(None, search, candidate).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_end = end

    if best_ratio < threshold:
        return None

    return original[:location] + replace + original[best_end:]


def apply_unified_diff(original: str, patch: str) -> str | None:
    """Apply a unified diff patch.

    Args:
        original: Original file content
        patch: Unified diff format patch

    Returns:
        Patched content or None if patch fails
    """
    # Check if it looks like a unified diff
    if not re.search(r"^@@\s*-\d+", patch, re.MULTILINE):
        return None

    try:
        # Try to apply using Python's difflib
        lines = original.splitlines(keepends=True)
        patch_lines = patch.splitlines(keepends=True)

        # Parse hunks
        result_lines = list(lines)
        offset = 0

        for i, line in enumerate(patch_lines):
            if line.startswith("@@"):
                # Parse hunk header
                match = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
                if not match:
                    continue

                old_start = int(match.group(1)) - 1 + offset
                # Apply hunk
                j = i + 1
                while j < len(patch_lines) and not patch_lines[j].startswith("@@"):
                    pline = patch_lines[j]
                    if pline.startswith("-"):
                        if old_start < len(result_lines):
                            result_lines.pop(old_start)
                            offset -= 1
                    elif pline.startswith("+"):
                        result_lines.insert(old_start, pline[1:])
                        old_start += 1
                        offset += 1
                    else:
                        old_start += 1
                    j += 1

        return "".join(result_lines)
    except Exception:
        return None


def apply_git_patch(filepath: str, patch: str) -> str | None:
    """Apply patch using git apply.

    Args:
        filepath: Path to the file
        patch: Patch content (unified diff)

    Returns:
        Patched content or None if git apply fails
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return None

        original = path.read_text()

        # Write patch to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
            f.write(patch)
            patch_file = f.name

        try:
            # Try git apply with --check first
            result = subprocess.run(
                ["git", "apply", "--check", patch_file],
                cwd=path.parent,
                capture_output=True,
                timeout=10,
            )

            if result.returncode != 0:
                return None

            # Apply for real
            subprocess.run(
                ["git", "apply", patch_file],
                cwd=path.parent,
                capture_output=True,
                check=True,
                timeout=10,
            )

            return path.read_text()
        finally:
            Path(patch_file).unlink(missing_ok=True)
            # Restore original if needed
            if path.read_text() != original:
                pass  # Keep the change
            else:
                path.write_text(original)

    except (subprocess.SubprocessError, OSError):
        return None


def apply_line_replace(original: str, old_line: str, new_line: str) -> str | None:
    """Replace a single line, tolerating whitespace differences.

    Args:
        original: Original content
        old_line: Line to find (stripped)
        new_line: Line to replace with

    Returns:
        Modified content or None
    """
    old_stripped = old_line.strip()
    lines = original.splitlines(keepends=True)

    for i, line in enumerate(lines):
        if line.strip() == old_stripped:
            # Preserve original indentation
            indent = len(line) - len(line.lstrip())
            lines[i] = " " * indent + new_line.strip() + "\n"
            return "".join(lines)

    return None


# Strategy pipeline: most literal to most flexible
PATCH_STRATEGIES = [
    ("exact", apply_exact_patch),
    ("line_replace", apply_line_replace),
    ("fuzzy", apply_fuzzy_patch),
    ("unified_diff", apply_unified_diff),
]


def apply_patch_robust(
    original: str,
    search: str,
    replace: str,
    filepath: str | None = None,
) -> PatchAttempt:
    """Try multiple strategies to apply a patch.

    Args:
        original: Original file content
        search: Text to search for / old content
        replace: Text to replace with / new content
        filepath: Optional filepath for git-based strategies

    Returns:
        PatchAttempt with result and strategy used
    """
    # Try each strategy in order
    for name, strategy in PATCH_STRATEGIES:
        try:
            if name in ("exact", "fuzzy", "line_replace"):
                result = strategy(original, search, replace)
            elif name == "unified_diff":
                # Treat replace as a unified diff
                result = strategy(original, replace)
            else:
                result = None

            if result is not None and result != original:
                return PatchAttempt(
                    success=True,
                    result=result,
                    strategy=name,
                )
        except Exception:
            continue

    # Try git apply if we have a filepath
    if filepath:
        result = apply_git_patch(filepath, replace)
        if result is not None and result != original:
            return PatchAttempt(
                success=True,
                result=result,
                strategy="git_apply",
            )

    return PatchAttempt(
        success=False,
        error="No strategy could apply the patch",
    )


def generate_unified_diff(
    original: str,
    modified: str,
    filepath: str = "file",
) -> str:
    """Generate a unified diff between two strings."""
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{filepath}",
        tofile=f"b/{filepath}",
    )

    return "".join(diff)


__all__ = [
    "PatchAttempt",
    "apply_patch_robust",
    "apply_exact_patch",
    "apply_fuzzy_patch",
    "apply_unified_diff",
    "apply_git_patch",
    "apply_line_replace",
    "generate_unified_diff",
    "PATCH_STRATEGIES",
]
