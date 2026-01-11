"""Extract fenced code blocks that specify file paths."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

BLOCK_PATTERN = re.compile(
    r"```(?P<path>[^\n`]+)\n(?P<content>.+?)```",
    re.DOTALL,
)

# Common language identifiers that are NOT file paths
LANGUAGE_ONLY = frozenset({
    "python", "py", "javascript", "js", "typescript", "ts", "java", "go",
    "rust", "c", "cpp", "c++", "csharp", "cs", "ruby", "rb", "php", "swift",
    "kotlin", "scala", "bash", "sh", "shell", "zsh", "sql", "html", "css",
    "json", "yaml", "yml", "xml", "markdown", "md", "text", "txt", "diff",
})


@dataclass
class FileChange:
    """Represents a modified file emitted by the Implementer."""

    path: Path
    content: str


def parse_file_blocks(
    response: str,
    fallback_path: Path | str | None = None,
) -> list[FileChange]:
    """Parse ```path\ncontent``` blocks from an LLM response.

    Args:
        response: LLM response text containing fenced code blocks.
        fallback_path: Path to use when fence contains only a language name.
    """
    changes: list[FileChange] = []
    for match in BLOCK_PATTERN.finditer(response or ""):
        raw_path = match.group("path").strip()
        content = match.group("content")

        # If fence is just a language name, use fallback path
        if raw_path.lower() in LANGUAGE_ONLY and fallback_path:
            path = Path(fallback_path)
        else:
            path = Path(raw_path)

        # Strip trailing fence artifacts/newlines
        content = content.rstrip("`\n\r")
        changes.append(FileChange(path=path, content=content))
    return changes


__all__ = ["FileChange", "parse_file_blocks"]
