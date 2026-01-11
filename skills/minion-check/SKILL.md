---
name: minion-check
description: >
  Run verification tasks using local minions. Good for: checking code quality,
  running test analysis, validating patterns, reviewing changes before commit.
  Minions scan files and report issues - they don't auto-fix. Use for quick
  verification sweeps on mechanical checks.
allowed-tools: Bash, Read, Glob, Grep
---

# Minion Check

Run verification tasks in parallel across your codebase. Minions scan files and report findings - perfect for pre-commit checks, quality sweeps, or pattern validation.

## When to use

- Pre-commit verification sweep
- Check code quality across files
- Find patterns, anti-patterns, or issues
- Analyze test coverage or missing tests
- Validate naming conventions

## Prerequisites

Ensure Ollama is running:

```bash
ollama serve
ollama list   # verify qwen2.5-coder is available
```

## Usage

### Check specific files

```bash
source .venv/bin/activate && python scripts/check.py "Check for missing error handling" \
  --files "src/api/*.py" \
  --json
```

### Check all files matching pattern

```bash
source .venv/bin/activate && python scripts/check.py "Find functions missing docstrings" \
  --files "**/*.py" \
  --json
```

### Pre-commit sweep

```bash
source .venv/bin/activate && python scripts/check.py "Review for bugs and issues" \
  --files "$(git diff --name-only --cached)" \
  --json
```

### Quality checks

```bash
source .venv/bin/activate && python scripts/check.py "Check for TODO comments" \
  --files "src/**/*.py" \
  --json
```

## Output

```json
{
  "task": "Check for missing error handling",
  "files_checked": 12,
  "findings": [
    {
      "file": "src/api/users.py",
      "issues": ["Missing try/except around database call on line 45"]
    }
  ],
  "stats": {
    "completed": 12,
    "failed": 0,
    "elapsed_seconds": 8.2
  }
}
```

## Swarm Mode (parallel)

For large sweeps, use swarm directly:

```bash
source .venv/bin/activate && python -c "
import asyncio
from llm_gc.swarm import process_files

result = asyncio.run(process_files(
    pattern='src/**/*.py',
    task='Check {file} for security issues',
    action='analyze'
))
print(f'Checked {result[\"stats\"][\"completed\"]} files')
"
```

## Good check tasks

| Check | Example prompt |
|-------|----------------|
| Missing docs | "Find functions without docstrings" |
| Error handling | "Check for unhandled exceptions" |
| TODO/FIXME | "List all TODO comments" |
| Naming | "Find variables with unclear names" |
| Complexity | "Find functions over 50 lines" |
| Imports | "Check for unused imports" |
| Types | "Find functions missing type hints" |

## Limitations

- Minions report issues, don't fix them
- Best for pattern-based mechanical checks
- May miss subtle bugs requiring deep reasoning
- Large files may be truncated in context

## When to escalate

If check requires:
- Understanding business logic -> use cloud reasoning
- Complex static analysis -> use dedicated tools (ruff, mypy)
- Security audit -> use proper security tools
