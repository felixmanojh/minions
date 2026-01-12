#!/usr/bin/env python3
"""Auto-apply polish (docstrings, types, etc.) to files using local minions.

Flow: Generate → AST Lint → LLM Validate → Retry → Apply
"""

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
from dataclasses import dataclass, field
from typing import Optional

from llm_gc.config import get_configs, get_validator_config, MinionConfigs
from llm_gc.orchestrator.base import OllamaClient
from llm_gc.parsers.code_blocks import parse_file_blocks
from llm_gc.linter import basic_lint, get_error_context, run_external_linter
from llm_gc.validator import CodeValidator, create_retry_prompt, ValidationResult
from llm_gc.logging import log_failure, log_success


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
    attempts: int = 1


@dataclass
class PolishConfig:
    """Configuration for polish operation."""
    backup: bool = False
    dry_run: bool = False
    no_lint: bool = False
    no_validate: bool = False
    lint_cmd: str | None = None
    max_retries: int = 1


async def generate_polish(
    client: OllamaClient,
    config,
    filepath: Path,
    content: str,
    task_prompt: str,
) -> tuple[str | None, str | None]:
    """Generate polished code.

    Returns:
        (generated_content, error_message)
    """
    prompt = f"""{POLISH_SYSTEM_PROMPT}

Task: {task_prompt}

File: {filepath.name}

```python
{content}
```

Output the complete modified file:"""

    try:
        response, _ = await client.prompt(prompt, config, role="polish")
    except Exception as e:
        return None, f"Minion failed: {e}"

    # Parse response for code block
    blocks = parse_file_blocks(response, fallback_path=filepath)
    if not blocks:
        # Check for truncation (has opening fence but no closing)
        if "```" in response[:50] and "```" not in response[-20:]:
            return None, "Response truncated (increase max_tokens or reduce file size)"
        return None, "No code block in response"

    return blocks[0].content, None


async def generate_with_retry(
    client: OllamaClient,
    config,
    filepath: Path,
    original: str,
    generated: str,
    error: str,
) -> tuple[str | None, str | None]:
    """Generate fixed code after error feedback.

    Returns:
        (generated_content, error_message)
    """
    prompt = create_retry_prompt(original, generated, error, lang="python")

    try:
        response, _ = await client.prompt(prompt, config, role="polish")
    except Exception as e:
        return None, f"Retry failed: {e}"

    # Parse response for code block
    blocks = parse_file_blocks(response, fallback_path=filepath)
    if not blocks:
        # Check for truncation (has opening fence but no closing)
        if "```" in response[:50] and "```" not in response[-20:]:
            return None, "Retry response truncated (increase max_tokens or reduce file size)"
        return None, "No code block in retry response"

    return blocks[0].content, None


async def polish_file(
    filepath: Path,
    task: str,
    client: OllamaClient,
    configs: MinionConfigs,
    polish_config: PolishConfig,
) -> PolishResult:
    """Polish a single file with full validation pipeline.

    Flow: Generate → AST Lint → LLM Validate → Retry → Apply
    """
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

    # === GENERATE ===
    generated, gen_error = await generate_polish(
        client, configs.minion, filepath, content, task_prompt
    )
    if gen_error:
        result.error = gen_error
        log_failure(str(filepath), gen_error, task=task, original=content)
        return result

    attempt = 1
    max_attempts = 1 + configs.validation.max_retries

    while attempt <= max_attempts:
        result.attempts = attempt

        # Check if content actually changed
        if generated.strip() == content.strip():
            result.changes.append("No changes needed")
            result.applied = True
            return result

        # === AST LINT ===
        if not polish_config.no_lint:
            lint_result = basic_lint(str(filepath), generated)
            if lint_result and lint_result.has_errors:
                error_ctx = get_error_context(str(filepath), generated, lint_result.lines)

                if attempt < max_attempts:
                    # Retry with error context
                    generated, retry_error = await generate_with_retry(
                        client, configs.minion, filepath, content, generated, error_ctx
                    )
                    if retry_error:
                        result.error = retry_error
                        log_failure(str(filepath), retry_error, task=task, original=content, generated=generated, attempts=attempt)
                        return result
                    attempt += 1
                    continue
                else:
                    result.error = f"Syntax errors persist after {attempt} attempts"
                    log_failure(str(filepath), result.error, task=task, original=content, generated=generated, attempts=attempt)
                    return result

        # === CUSTOM LINT ===
        if polish_config.lint_cmd:
            # Write temp file for external linter
            temp_path = filepath.with_suffix(filepath.suffix + ".tmp")
            temp_path.write_text(generated)
            try:
                ext_result = run_external_linter(polish_config.lint_cmd, str(temp_path))
                if ext_result and ext_result.has_errors:
                    result.error = ext_result.text[:200]
                    log_failure(str(filepath), result.error, task=task, original=content, generated=generated, attempts=attempt)
                    return result
            finally:
                temp_path.unlink(missing_ok=True)

        # === LLM VALIDATE ===
        if not polish_config.no_validate:
            validator_config = get_validator_config(configs)
            validator = CodeValidator(client=client, config=validator_config)

            val_result = await validator.validate(content, generated, task_prompt)

            if not val_result.passed:
                if attempt < max_attempts:
                    # Retry with validation error
                    generated, retry_error = await generate_with_retry(
                        client, configs.minion, filepath, content, generated, val_result.reason or "Validation failed"
                    )
                    if retry_error:
                        result.error = retry_error
                        log_failure(str(filepath), retry_error, task=task, original=content, generated=generated, attempts=attempt)
                        return result
                    attempt += 1
                    continue
                else:
                    result.error = f"Validation failed: {val_result.reason}"
                    log_failure(str(filepath), result.error, task=task, original=content, generated=generated, attempts=attempt)
                    return result

        # All checks passed, exit retry loop
        break

    # === DRY RUN ===
    if polish_config.dry_run:
        result.changes.append("Would apply changes (dry-run)")
        result.applied = True
        return result

    # === BACKUP ===
    if polish_config.backup:
        backup_path = filepath.with_suffix(filepath.suffix + ".bak")
        backup_path.write_text(content)

    # === APPLY ===
    filepath.write_text(generated)

    # Detect what changed (simple heuristic)
    old_lines = set(content.splitlines())
    new_lines = set(generated.splitlines())
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
    log_success(str(filepath), task=task, original=content, generated=generated, attempts=result.attempts)
    return result


async def run_polish(
    files: list[Path],
    task: str,
    preset: str | None = None,
    num_ctx: int | None = None,
    backup: bool = False,
    dry_run: bool = False,
    no_lint: bool = False,
    no_validate: bool = False,
    lint_cmd: str | None = None,
    max_retries: int | None = None,
) -> dict:
    """Polish multiple files."""
    configs = get_configs(preset=preset)

    # Apply num_ctx override
    if num_ctx:
        from llm_gc.config import ModelConfig
        configs.minion = ModelConfig(
            model=configs.minion.model,
            temperature=configs.minion.temperature,
            max_tokens=configs.minion.max_tokens,
            num_ctx=num_ctx,
        )

    # Override max_retries if specified
    if max_retries is not None:
        configs.validation.max_retries = max_retries

    polish_config = PolishConfig(
        backup=backup,
        dry_run=dry_run,
        no_lint=no_lint,
        no_validate=no_validate,
        lint_cmd=lint_cmd,
        max_retries=configs.validation.max_retries,
    )

    client = OllamaClient()
    results: list[PolishResult] = []

    for filepath in files:
        result = await polish_file(
            filepath=filepath,
            task=task,
            client=client,
            configs=configs,
            polish_config=polish_config,
        )
        results.append(result)

        # Print progress
        status = "✓" if result.applied else "✗"
        detail = ", ".join(result.changes) if result.changes else result.error or "failed"
        attempts_info = f" ({result.attempts} attempts)" if result.attempts > 1 else ""
        print(f"{status} {filepath}: {detail}{attempts_info}")

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
            {"file": r.file, "error": r.error, "attempts": r.attempts}
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
        choices=["lite", "standard", "expert"],
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
        "--no-lint",
        action="store_true",
        help="Skip AST syntax checking",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip LLM validation",
    )
    parser.add_argument(
        "--lint-cmd",
        type=str,
        default=None,
        help="Custom linter command (e.g., 'ruff check')",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=None,
        help="Max retry attempts on failure (default: from config)",
    )
    parser.add_argument(
        "--no-retry",
        action="store_true",
        help="Disable retry on failure",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON result",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    max_retries = 0 if args.no_retry else args.max_retries

    result = await run_polish(
        files=args.files,
        task=args.task,
        preset=args.preset,
        num_ctx=args.num_ctx,
        backup=args.backup,
        dry_run=args.dry_run,
        no_lint=args.no_lint,
        no_validate=args.no_validate,
        lint_cmd=args.lint_cmd,
        max_retries=max_retries,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\nPolish complete: {result['stats']['applied']}/{result['stats']['total']} files")


if __name__ == "__main__":
    asyncio.run(main())
