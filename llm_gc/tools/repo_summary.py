"""Helpers to summarize repo state for prompts."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RepoSummary:
    text: str
    sources: dict[str, str]


def build_repo_summary(
    root: str | Path,
    *,
    max_chars: int = 4000,
    tree_depth: int = 2,
    max_tree_entries: int = 120,
) -> RepoSummary:
    root_path = Path(root).resolve()
    sections: list[str] = []
    sources: dict[str, str] = {}

    readme = root_path / "README.md"
    if readme.exists():
        snippet = readme.read_text(encoding="utf-8")
        snippet = snippet[: max_chars // 2]
        sections.append("# README snippet\n" + snippet)
        sources["README"] = str(readme.relative_to(root_path))

    status = _git_status(root_path)
    if status:
        sections.append("# git status -sb\n" + status)
        sources["git_status"] = "git status -sb"

    tree = _directory_tree(root_path, max_depth=tree_depth, max_entries=max_tree_entries)
    if tree:
        sections.append("# Directory tree\n" + tree)
        sources["tree"] = f"depth<= {tree_depth}"

    combined = "\n\n".join(sections)
    combined = combined[:max_chars]
    return RepoSummary(text=combined, sources=sources)


def _git_status(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "-sb"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return "git not available"
    if result.returncode != 0:
        return result.stderr.strip()
    return result.stdout.strip()


def _directory_tree(root: Path, *, max_depth: int, max_entries: int) -> str:
    lines: list[str] = []
    total = 0
    for current_root, dirs, files in os.walk(root):
        rel = Path(current_root).relative_to(root)
        depth = 0 if rel == Path(".") else len(rel.parts)
        if depth > max_depth:
            dirs[:] = []
            continue
        indent = "  " * depth
        directory_name = "." if rel == Path(".") else rel.name
        lines.append(f"{indent}{directory_name}/")
        total += 1
        if total >= max_entries:
            break
        for name in sorted(files):
            if total >= max_entries:
                break
            lines.append(f"{indent}  {name}")
            total += 1
        dirs.sort()
        if total >= max_entries:
            break
    if total >= max_entries:
        lines.append("... (truncated)")
    return "\n".join(lines)
