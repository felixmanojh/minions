"""Read-only file access constrained to the repo root."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class FileReadRequest:
    """Parameters for a single file read."""

    path: str
    start: int | None = None
    end: int | None = None

    def describe(self) -> str:
        if self.start is None and self.end is None:
            return self.path
        start = self.start or 1
        end = self.end or "end"
        return f"{self.path}:{start}-{end}"


class FileReader:
    """Reads files relative to a repo root with safety checks."""

    def __init__(self, root: str | Path, max_bytes: int = 8192) -> None:
        self.root = Path(root).resolve()
        self.max_bytes = max_bytes

    def read(self, request: FileReadRequest) -> str:
        path = self._resolve(request.path)
        text = path.read_text(encoding="utf-8")
        snippet = self._slice_lines(text, request)
        snippet = self._truncate(snippet)
        language = path.suffix.lstrip(".") or "text"
        header = f"File: {path.relative_to(self.root)}"
        return f"{header}\n```{language}\n{snippet}\n```"

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_bytes:
            return text
        truncated = text[: self.max_bytes]
        return truncated + "\n...\n[truncated]\n"

    @staticmethod
    def _slice_lines(text: str, request: FileReadRequest) -> str:
        if request.start is None and request.end is None:
            return text
        lines = text.splitlines()
        start = max((request.start or 1) - 1, 0)
        end = request.end
        slice_lines = lines[start:end]
        return "\n".join(slice_lines)

    def _resolve(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()
        if not str(path).startswith(str(self.root)):
            raise ValueError(f"Path escapes repo root: {relative_path}")
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(relative_path)
        return path

    def batch_read(self, requests: Iterable[FileReadRequest]) -> list[str]:
        return [self.read(req) for req in requests]
