---
name: minion-swarm
description: >
  Dispatch a swarm of minions to work on multiple tasks in parallel. Good for: batch operations
  like adding docstrings to many files, fixing typos across a codebase, bulk renaming, code checks.
  Features auto-retry with simplified prompts when minions fail. Use when you have many similar tasks.
allowed-tools: Bash, Read, Glob, Grep
---

# Minion Swarm

Dispatch many minions in parallel with auto-retry. Like Gru commanding his minion army!

## When to use

- Multiple similar tasks (docstrings on 10 files)
- Bulk operations (fix typos across codebase)
- Code verification sweeps (find issues, check patterns)
- Time-sensitive grunt work
- Tasks that can fail and retry

## Features

| Feature | Description |
|---------|-------------|
| Parallel execution | Multiple minions work simultaneously |
| Auto-retry | Failed tasks retry with simpler prompts |
| Minion-speak | Prompts get simplified on retry |
| 🍌 Banana counter | Track successful completions across sessions |
| Streaks | Daily streak tracking for productivity |

## Usage

### Patch: Same task on multiple files

```bash
source .venv/bin/activate && python scripts/swarm.py patch "Add docstrings to all functions" \
  src/utils.py src/parser.py src/config.py \
  --workers 5 \
  --json
```

### Analyze: Check files for issues

```bash
source .venv/bin/activate && python scripts/swarm.py analyze "Check for missing error handling" \
  src/api/*.py \
  --workers 5 \
  --json
```

### Batch from JSON

Create a tasks file:

```json
[
  {"kind": "patch", "description": "Add type hints", "target": "src/utils.py"},
  {"kind": "patch", "description": "Add type hints", "target": "src/parser.py"},
  {"kind": "task", "description": "Review error handling", "context_files": ["src/errors.py"]}
]
```

Run the swarm:

```bash
source .venv/bin/activate && python scripts/swarm.py batch tasks.json --workers 5 --json
```

### From Claude (programmatic)

```python
from llm_gc.swarm import Swarm
import asyncio

swarm = Swarm(workers=5, max_retries=2)

# Add patch tasks
swarm.add_patch("Add docstrings", target="src/a.py")
swarm.add_patch("Add docstrings", target="src/b.py")

# Add analyze tasks
swarm.add_task("Check for security issues", context_files=["src/auth.py"])

result = asyncio.run(swarm.run())
print(f"Completed: {result['stats']['completed']}")
```

### Process files with pattern

```python
from llm_gc.swarm import process_files
import asyncio

# Analyze all Python files
result = asyncio.run(process_files(
    pattern='src/**/*.py',
    task='Check {file} for security issues',
    action='analyze'
))

# Patch all Python files
result = asyncio.run(process_files(
    pattern='src/**/*.py',
    task='Add type hints to {file}',
    action='patch'
))
```

## Check/Analyze Examples

| Check | Example prompt |
|-------|----------------|
| Missing docs | "Find functions without docstrings" |
| Error handling | "Check for unhandled exceptions" |
| TODO/FIXME | "List all TODO comments" |
| Naming | "Find variables with unclear names" |
| Complexity | "Find functions over 50 lines" |
| Imports | "Check for unused imports" |
| Types | "Find functions missing type hints" |

## Auto-retry with Minion-speak

When a task fails, the swarm automatically retries with simpler prompts:

| Retry | Prompt Transformation |
|-------|----------------------|
| 0 | Original prompt |
| 1 | Remove verbose words + "SIMPLE TASK. ONE THING ONLY." |
| 2 | First 20 words only + "DO THIS:" |

This helps small models focus on the essential task.

## Output

```json
{
  "completed": [
    {"description": "Add docstrings...", "result": "sessions/xxx.patch"}
  ],
  "failed": [
    {"description": "Complex task...", "error": "Model output truncated"}
  ],
  "stats": {
    "total": 5,
    "completed": 4,
    "failed": 1,
    "retries": 2,
    "elapsed_seconds": 45.2,
    "bananas_earned": 4,
    "bananas_total": 127
  }
}
```

## Banana Stats 🍌

Track your minion productivity across sessions!

```bash
source .venv/bin/activate && python scripts/bananas.py

# Output:
# ========================================
# 🍌 BANANA STATS 🍌
# ========================================
# Total bananas: 127
# Today: 15
# Current streak: 3 days
# Best streak: 7 days
#
# 🍌🍌🍌🍌🍌 x20+
# ========================================
```

Banana milestones:
- 🍌 < 10: Getting started
- 🍌🍌🍌🍌🍌 x10: Regular user
- 🍌🍌🍌🍌🍌 x20+: Power user
- 🍌👑: BANANA KING! (500+)

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--workers` | 5 | Parallel workers |
| `--retries` | 2 | Max retries per task |
| `--json` | false | Output JSON |

## Best practices

1. **Keep tasks atomic** - One file, one change
2. **Use more workers for simple tasks** - `--workers 10` for typo fixes
3. **Use fewer workers for complex tasks** - `--workers 3` for code changes
4. **Review all patches** - Minions make mistakes!

## Example: Add docstrings to entire module

```bash
# Find all Python files
FILES=$(find src/ -name "*.py" | tr '\n' ' ')

# Dispatch swarm
source .venv/bin/activate && python scripts/swarm.py patch "Add docstrings to all public functions" $FILES \
  --workers 5 \
  --retries 2 \
  --json > results.json

# Review patches
cat sessions/*.patch | less
```

## Limitations

- Parallel tasks compete for Ollama resources
- Very large swarms may slow down
- Each task is independent (no shared state)
- Review patches carefully before applying
- Analyze tasks report issues, they don't fix them
