"""Extract fenced code blocks that specify file paths."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

BLOCK_PATTERN = re.compile(
    r"```(?P<path>[^\n`]+)\n(?P<content>.+?)```",
    re.DOTALL,
)


@dataclass
class FileChange:
    """Represents a modified file emitted by the Implementer."""

    path: Path
    content: str


def parse_file_blocks(response: str) -> list[FileChange]:
    """Parse ```path\ncontent``` blocks from an LLM response."""

    changes: list[FileChange] = []
    for match in BLOCK_PATTERN.finditer(response or ""):
        raw_path = match.group("path").strip()
        content = match.group("content")
        path = Path(raw_path)
        # Strip trailing fence artifacts/newlines
        content = content.rstrip("`\n\r")
        changes.append(FileChange(path=path, content=content))
    return changes


__all__ = ["FileChange", "parse_file_blocks"]
