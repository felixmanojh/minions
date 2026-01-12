"""Generate a structural map of the repo using tree-sitter (inspired by aider)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


try:
    from grep_ast import grep
except ImportError:  # pragma: no cover
    grep = None


@dataclass
class RepoSymbol:
    """Represents a symbol in the repository."""

    path: Path
    signature: str
    kind: str


@dataclass
class RepoMap:
    """Represents the structural map of the repository."""

    symbols: list[RepoSymbol]

    def as_text(self) -> str:
        """Converts the repository map to a text representation."""
        lines = []
        for symbol in self.symbols:
            lines.append(f"{symbol.path}:")
            lines.append(f"  [{symbol.kind}] {symbol.signature}")
        return "\n".join(lines)


SUPPORTED_LANGS = {
    "python": {"extensions": {".py"}, "matcher": "function or class"},
}


def build_repomap(root: str | Path) -> RepoMap:
    """Builds the repository map for a given root directory."""
    root_path = Path(root).resolve()
    if grep is None:
        return RepoMap(symbols=[])
    symbols: list[RepoSymbol] = []
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