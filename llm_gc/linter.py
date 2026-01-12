"""AST-based linting using tree-sitter.

Provides fast syntax checking before LLM validation.
Based on patterns from Aider (https://github.com/Aider-AI/aider).
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Try to import tree-sitter based tools
try:
    from grep_ast import filename_to_lang
    from grep_ast.tsl import get_parser
    from grep_ast import TreeContext
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


@dataclass
class LintResult:
    """Result of linting a file."""
    text: str  # Human-readable error message
    lines: list[int]  # Line numbers with errors

    @property
    def has_errors(self) -> bool:
        return len(self.lines) > 0


def basic_lint(fname: str, code: str) -> Optional[LintResult]:
    """Use tree-sitter to find syntax errors.

    Args:
        fname: Filename (used to determine language)
        code: Source code to check

    Returns:
        LintResult if errors found, None if clean.
    """
    if not TREE_SITTER_AVAILABLE:
        # Fall back to Python compile check for .py files
        if fname.endswith(".py"):
            return _python_compile_check(fname, code)
        return None

    lang = filename_to_lang(fname)
    if not lang:
        return None

    try:
        parser = get_parser(lang)
        tree = parser.parse(bytes(code, "utf-8"))
        errors = _traverse_tree(tree.root_node)

        if not errors:
            return None

        return LintResult(
            text=f"Syntax errors on lines: {errors}",
            lines=errors
        )
    except Exception:
        # If tree-sitter fails, fall back for Python
        if fname.endswith(".py"):
            return _python_compile_check(fname, code)
        return None


def _traverse_tree(node) -> list[int]:
    """Find ERROR nodes in AST."""
    errors = []
    if node.type == "ERROR" or node.is_missing:
        errors.append(node.start_point[0] + 1)  # 1-indexed
    for child in node.children:
        errors += _traverse_tree(child)
    return sorted(set(errors))


def _python_compile_check(fname: str, code: str) -> Optional[LintResult]:
    """Fallback: use Python's compile() for syntax check."""
    try:
        compile(code, fname, "exec")
        return None
    except SyntaxError as e:
        line = e.lineno or 1
        return LintResult(
            text=f"SyntaxError: {e.msg} (line {line})",
            lines=[line]
        )


def get_error_context(fname: str, code: str, line_nums: list[int]) -> str:
    """Get context around error lines, marked for LLM.

    Uses TreeContext from grep-ast to show surrounding function/class.
    Falls back to simple line extraction if not available.

    Args:
        fname: Filename
        code: Source code
        line_nums: Lines with errors

    Returns:
        Formatted error context string for LLM.
    """
    if not TREE_SITTER_AVAILABLE:
        return _simple_error_context(code, line_nums)

    try:
        context = TreeContext(
            fname,
            code,
            color=False,
            line_number=True,
            child_context=False,
            last_line=False,
            margin=0,
            mark_lois=True,  # Mark lines of interest
            loi_pad=3,       # 3 lines of context
            show_top_of_file_parent_scope=False,
        )

        context.add_lines_of_interest(set(line_nums))
        context.add_context()

        s = "s" if len(line_nums) > 1 else ""
        output = f"## See relevant line{s} below marked with █.\n\n"
        output += f"{fname}:\n"
        output += context.format()
        return output
    except Exception:
        return _simple_error_context(code, line_nums)


def _simple_error_context(code: str, line_nums: list[int]) -> str:
    """Simple fallback: show lines around errors."""
    lines = code.splitlines()
    output_lines = []

    for error_line in line_nums:
        start = max(0, error_line - 4)
        end = min(len(lines), error_line + 3)

        for i in range(start, end):
            line_no = i + 1
            marker = ">>> " if line_no == error_line else "    "
            output_lines.append(f"{marker}{line_no:4d} | {lines[i]}")
        output_lines.append("")

    return "\n".join(output_lines)


def run_external_linter(cmd: str, filepath: str, cwd: str | None = None) -> Optional[LintResult]:
    """Run user's linter command (ruff, eslint, etc.).

    Args:
        cmd: Linter command (e.g., "ruff check", "eslint")
        filepath: File to lint
        cwd: Working directory

    Returns:
        LintResult if errors found, None if clean.
    """
    try:
        result = subprocess.run(
            f"{cmd} {filepath}",
            shell=True,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=30,
        )

        if result.returncode == 0:
            return None

        errors = result.stdout + result.stderr
        linenums = _find_line_numbers(errors, filepath)

        return LintResult(
            text=f"## Running: {cmd} {filepath}\n\n{errors}",
            lines=linenums
        )
    except subprocess.TimeoutExpired:
        return LintResult(text=f"Linter timed out: {cmd}", lines=[])
    except OSError as err:
        return LintResult(text=f"Linter failed: {err}", lines=[])


def _find_line_numbers(text: str, fname: str) -> list[int]:
    """Extract line numbers from linter output."""
    # Match patterns like "filename:42:" or "filename:42:5:"
    fname_escaped = re.escape(Path(fname).name)
    pattern = re.compile(rf"(?:{fname_escaped}|{re.escape(fname)}):(\d+)")
    matches = pattern.findall(text)
    return sorted(set(int(m) for m in matches))
