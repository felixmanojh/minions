"""Generate a structural map of the repo using tree-sitter (inspired by aider)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

try:
    from grep_ast import grep
except ImportError:  # pragma: no cover
    grep = None


@dataclass
class RepoSymbol:
    path: Path
    signature: str
    kind: str


@dataclass
class RepoMap:
    symbols: List[RepoSymbol]

    def as_text(self) -> str:
        lines = []
        for symbol in self.symbols:
            lines.append(f"{symbol.path}:")
            lines.append(f"  [{symbol.kind}] {symbol.signature}")
        return "\n".join(lines)


SUPPORTED_LANGS = {
    "python": {"extensions": {".py"}, "matcher": "function or class"},
}


def build_repomap(root: str | Path) -> RepoMap:
    root_path = Path(root).resolve()
    if grep is None:
        return RepoMap(symbols=[])
    symbols: List[RepoSymbol] = []
    for lang, data in SUPPORTED_LANGS.items():
        matcher = data["matcher"]
        extensions = data["extensions"]
        files = [
            str(path)
            for path in root_path.rglob("*")
            if path.suffix in extensions and path.is_file()
        ]
        if not files:
            continue
        results = grep(match=matcher, files=files)
        for result in results:
            symbols.append(
                RepoSymbol(
                    path=Path(result.filename).relative_to(root_path),
                    signature=result.code.strip(),
                    kind=lang,
                )
            )
    return RepoMap(symbols=symbols)


__all__ = ["RepoMap", "RepoSymbol", "build_repomap"]
