"""Repository map with PageRank file ranking.

Inspired by Aider's repomap - uses import graph to find most relevant files.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import networkx as nx

from llm_gc.cache import get_cache

# Language-specific import patterns
IMPORT_PATTERNS = {
    ".py": [
        r"^import\s+([\w.]+)",
        r"^from\s+([\w.]+)\s+import",
    ],
    ".ts": [
        r'import\s+.*?from\s+["\'](.+?)["\']',
        r'import\s+["\'](.+?)["\']',
        r'require\s*\(\s*["\'](.+?)["\']\s*\)',
    ],
    ".tsx": [
        r'import\s+.*?from\s+["\'](.+?)["\']',
        r'import\s+["\'](.+?)["\']',
    ],
    ".js": [
        r'import\s+.*?from\s+["\'](.+?)["\']',
        r'require\s*\(\s*["\'](.+?)["\']\s*\)',
    ],
    ".jsx": [
        r'import\s+.*?from\s+["\'](.+?)["\']',
    ],
    ".go": [
        r'import\s+"(.+?)"',
        r'import\s+\w+\s+"(.+?)"',
    ],
    ".rs": [
        r"use\s+([\w:]+)",
        r"mod\s+(\w+)",
    ],
}


def extract_imports_python(filepath: str) -> list[str]:
    """Extract imports from Python file using AST."""
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            tree = ast.parse(f.read())

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module.split(".")[0])

        return imports
    except (SyntaxError, UnicodeDecodeError):
        return []


def extract_imports_regex(filepath: str, patterns: list[str]) -> list[str]:
    """Extract imports using regex patterns."""
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            content = f.read()

        imports = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            imports.extend(matches)

        return imports
    except OSError:
        return []


def extract_imports(filepath: str) -> list[str]:
    """Extract imports from a source file."""
    path = Path(filepath)
    suffix = path.suffix.lower()

    if suffix == ".py":
        return extract_imports_python(filepath)

    patterns = IMPORT_PATTERNS.get(suffix, [])
    if patterns:
        return extract_imports_regex(filepath, patterns)

    return []


def resolve_import_to_file(
    imp: str,
    source_file: Path,
    all_files: list[Path],
) -> Path | None:
    """Try to resolve an import to an actual file in the repo."""
    # For Python: convert module.name to module/name.py
    candidates = [
        imp.replace(".", "/") + ".py",
        imp.replace(".", "/") + "/__init__.py",
        imp + ".py",
        imp + ".ts",
        imp + ".tsx",
        imp + ".js",
        imp + "/index.ts",
        imp + "/index.js",
    ]

    # Also try relative to source file
    source_dir = source_file.parent
    for candidate in candidates:
        for f in all_files:
            if str(f).endswith(candidate) or f.name == candidate.split("/")[-1]:
                return f
            # Check relative path
            try:
                rel = source_dir / candidate
                if rel.resolve() in [p.resolve() for p in all_files]:
                    return rel
            except (OSError, ValueError):
                pass

    return None


class RepoMap:
    """Build and query a map of repository file relationships."""

    def __init__(self, repo_root: str | Path):
        self.repo_root = Path(repo_root).resolve()
        self.cache = get_cache(self.repo_root)
        self._graph: nx.DiGraph | None = None
        self._files: list[Path] = []

    def discover_files(
        self,
        extensions: list[str] | None = None,
        exclude_dirs: list[str] | None = None,
    ) -> list[Path]:
        """Discover source files in the repository."""
        if extensions is None:
            extensions = [".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs"]

        if exclude_dirs is None:
            exclude_dirs = [
                ".git",
                "node_modules",
                "__pycache__",
                ".venv",
                "venv",
                "dist",
                "build",
                ".next",
            ]

        files = []
        for ext in extensions:
            for path in self.repo_root.rglob(f"*{ext}"):
                # Skip excluded directories
                if any(excl in path.parts for excl in exclude_dirs):
                    continue
                files.append(path)

        self._files = files
        return files

    def build_graph(self, files: list[Path] | None = None) -> nx.DiGraph:
        """Build import graph from files."""
        if files is None:
            files = self._files or self.discover_files()

        G = nx.DiGraph()

        # Add all files as nodes
        for f in files:
            G.add_node(str(f))

        # Add edges for imports
        for source_file in files:
            imports = self.cache.get_file_cached(
                source_file,
                extract_imports,
            )

            for imp in imports:
                target = resolve_import_to_file(imp, source_file, files)
                if target and target != source_file:
                    # Weight by frequency
                    if G.has_edge(str(source_file), str(target)):
                        G[str(source_file)][str(target)]["weight"] += 1
                    else:
                        G.add_edge(str(source_file), str(target), weight=1)

        self._graph = G
        return G

    def rank_files(
        self,
        target_files: list[str] | None = None,
        top_n: int | None = None,
    ) -> list[tuple[str, float]]:
        """Rank files by importance using PageRank.

        Args:
            target_files: Files to personalize ranking around
            top_n: Return only top N files

        Returns:
            List of (filepath, score) tuples sorted by importance
        """
        if self._graph is None:
            self.build_graph()

        G = self._graph
        if not G or len(G) == 0:
            return []

        # Personalize around target files if provided
        personalization = None
        if target_files:
            personalization = {str(f): 0.0 for f in G.nodes()}
            for tf in target_files:
                if str(tf) in personalization:
                    personalization[str(tf)] = 1.0 / len(target_files)

        try:
            scores = nx.pagerank(
                G,
                weight="weight",
                personalization=personalization,
            )
        except nx.NetworkXError:
            # Graph might be empty or have issues
            return [(str(f), 1.0 / len(G)) for f in G.nodes()]

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        if top_n:
            ranked = ranked[:top_n]

        return ranked

    def get_context_files(
        self,
        target_file: str | Path,
        max_files: int = 10,
    ) -> list[str]:
        """Get most relevant context files for a target file.

        Args:
            target_file: The file being worked on
            max_files: Maximum number of context files to return

        Returns:
            List of file paths sorted by relevance
        """
        target = str(Path(target_file).resolve())
        ranked = self.rank_files(target_files=[target], top_n=max_files + 1)

        # Exclude the target file itself
        return [f for f, _ in ranked if f != target][:max_files]

    def get_file_outline(self, filepath: str | Path) -> str:
        """Get a brief outline of a file (function/class names only)."""

        def compute_outline(fp: str) -> str:
            path = Path(fp)
            if path.suffix != ".py":
                return ""

            try:
                with open(fp, encoding="utf-8") as f:
                    tree = ast.parse(f.read())

                lines = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                        lines.append(f"def {node.name}(...) @ line {node.lineno}")
                    elif isinstance(node, ast.ClassDef):
                        lines.append(f"class {node.name} @ line {node.lineno}")

                return "\n".join(lines)
            except (SyntaxError, OSError):
                return ""

        return self.cache.get_file_cached(filepath, compute_outline)


def rank_files_for_context(
    target_file: str | Path,
    repo_root: str | Path = ".",
    max_files: int = 10,
) -> list[str]:
    """Convenience function to get ranked context files.

    Args:
        target_file: The file being worked on
        repo_root: Repository root directory
        max_files: Maximum number of context files

    Returns:
        List of file paths sorted by relevance
    """
    repo = RepoMap(repo_root)
    repo.discover_files()
    return repo.get_context_files(target_file, max_files)


__all__ = [
    "RepoMap",
    "extract_imports",
    "rank_files_for_context",
]
