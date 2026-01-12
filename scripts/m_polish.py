#!/usr/bin/env python3
"""Auto-apply polish (docstrings, types, etc.) to files using local minions."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Auto-bootstrap venv and dependencies
from llm_gc.bootstrap import ensure_venv
ensure_venv()

import argparse
import asyncio
import json
import subprocess
from dataclasses import dataclass, field

from llm_gc.config import load_models, get_num_ctx_override
from llm_gc.orchestrator.base import OllamaClient
from llm_gc.parsers.code_blocks import parse_file_blocks


# Task presets
TASK_PROMPTS = {
    "docstrings": "Add docstrings to all functions and classes that don't have them",
    "types": "Add type hints to all function parameters and return types",
    "headers": "Add a module-level docstring describing what this file does",
    "comments": "Add inline comments explaining complex or non-obvious logic",
    "all": "Add docstrings to functions/classes, type hints to parameters/returns, and a module docstring",
}

POLISH_SYSTEM_PROMPT = """You are a code polish minion. Your job is to add polish to code.

Rules:
- Output ONLY the complete modified file in a code block
- Do NOT explain what you did
- Do NOT add any text before or after the code block
- Preserve all existing functionality exactly
- Only add what was requested, don't change logic
"""


@dataclass
class PolishResult:
    """Result of polishing a single file."""
    file: str
    applied: bool
    changes: list[str] = field(default_factory=list)
    error: str | None = None


async def polish_file(
    filepath: Path,
    task: str,
    client: OllamaClient,
    config,
    backup: bool = False,
    dry_run: bool = False,
) -> PolishResult:
    """Polish a single file."""
    result = PolishResult(file=str(filepath), applied=False)

    # Check file exists and is readable
    if not filepath.exists():
        result.error = "File not found"
        return result

    # Check file size (line count)
    content = filepath.read_text()
    line_count = len(content.splitlines())
    if line_count > 500:
        result.error = f"File too large ({line_count} lines > 500)"
        return result

    # Resolve task prompt
    task_prompt = TASK_PROMPTS.get(task, task)

    # Build prompt
    prompt = f"""{POLISH_SYSTEM_PROMPT}

Task: {task_prompt}

File: {filepath.name}

```python
{content}
```

Output the complete modified file:"""

    # Call minion
    try:
        response, latency_ms = await client.prompt(prompt, config, role="polish")
    except Exception as e:
        result.error = f"Minion failed: {e}"
        return result

    # Parse response for code block
    blocks = parse_file_blocks(response, fallback_path=filepath)
    if not blocks:
        # Try to extract raw code if no fence found
        result.error = "No code block in response"
        return result

    new_content = blocks[0].content

    # Check if content actually changed
    if new_content.strip() == content.strip():
        result.changes.append("No changes needed")
        result.applied = True
        return result

    if dry_run:
        result.changes.append("Would apply changes (dry-run)")
        result.applied = True
        return result

    # Backup if requested
    if backup:
        backup_path = filepath.with_suffix(filepath.suffix + ".bak")
        backup_path.write_text(content)

    # Write new content
    filepath.write_text(new_content)

    # Syntax check for Python files
    if filepath.suffix == ".py":
        try:
            subprocess.run(
                [sys.executable, "-m", "py_compile", str(filepath)],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            # Revert on syntax error
            filepath.write_text(content)
            result.error = f"Syntax error, reverted: {e.stderr.decode()[:200]}"
            return result

    # Detect what changed (simple heuristic)
    old_lines = set(content.splitlines())
    new_lines = set(new_content.splitlines())
    added = new_lines - old_lines

    # Count docstrings added
    docstring_count = sum(1 for line in added if '"""' in line or "'''" in line)
    if docstring_count:
        result.changes.append(f"Added {docstring_count // 2 or 1} docstring(s)")

    # Count type hints added
    type_hint_count = sum(1 for line in added if "->" in line or ": " in line)
    if type_hint_count:
        result.changes.append(f"Added type hints")

    if not result.changes:
        result.changes.append("Applied polish")

    result.applied = True
    return result


async def run_polish(
    files: list[Path],
    task: str,
    preset: str | None = None,
    config_path: Path | None = None,
    num_ctx: int | None = None,
    backup: bool = False,
    dry_run: bool = False,
) -> dict:
    """Polish multiple files."""
    models = load_models(config_path, preset=preset)
    config = models.get("implementer")
    if not config:
        raise KeyError("No 'implementer' config found")

    # Apply num_ctx override
    ctx_override = num_ctx or get_num_ctx_override()
    if ctx_override:
        config = config.__class__(
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            num_ctx=ctx_override,
        )

    client = OllamaClient()
    results: list[PolishResult] = []

    for filepath in files:
        result = await polish_file(
            filepath=filepath,
            task=task,
            client=client,
            config=config,
            backup=backup,
            dry_run=dry_run,
        )
        results.append(result)

        # Print progress
        status = "✓" if result.applied else "✗"
        detail = ", ".join(result.changes) if result.changes else result.error or "failed"
        print(f"{status} {filepath}: {detail}")

    # Build summary
    applied = [r for r in results if r.applied]
    failed = [r for r in results if not r.applied]

    return {
        "applied": len(failed) == 0 and len(applied) > 0,
        "files_modified": [r.file for r in applied if r.changes and r.changes != ["No changes needed"]],
        "changes": [
            f"{r.file}: {', '.join(r.changes)}"
            for r in results if r.changes
        ],
        "errors": [
            {"file": r.file, "error": r.error}
            for r in failed
        ],
        "stats": {
            "total": len(results),
            "applied": len(applied),
            "failed": len(failed),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-apply polish (docstrings, types) to files"
    )
    parser.add_argument(
        "files",
        nargs="+",
        type=Path,
        help="Files to polish",
    )
    parser.add_argument(
        "--task",
        default="all",
        help="Task: docstrings, types, headers, comments, all, or custom prompt",
    )
    parser.add_argument(
        "--preset",
        choices=["lite", "medium", "large"],
        default=None,
        help="Model preset",
    )
    parser.add_argument(
        "--num-ctx",
        type=int,
        default=None,
        help="Context window size",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create .bak backup before modifying",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without applying",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON result",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    result = await run_polish(
        files=args.files,
        task=args.task,
        preset=args.preset,
        num_ctx=args.num_ctx,
        backup=args.backup,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\nPolish complete: {result['stats']['applied']}/{result['stats']['total']} files")


if __name__ == "__main__":
    asyncio.run(main())
