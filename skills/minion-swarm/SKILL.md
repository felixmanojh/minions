---
name: minion-swarm
description: >
  Dispatch a swarm of minions to work on multiple tasks in parallel. Good for: batch operations
  like adding docstrings to many files, fixing typos across a codebase, bulk renaming. Features
  auto-retry with simplified prompts when minions fail. Use when you have many similar grunt tasks.
allowed-tools: Bash, Read, Glob, Grep
---

# Minion Swarm

Dispatch many minions in parallel with auto-retry. Like Gru commanding his minion army!

## When to use

- Multiple similar tasks (docstrings on 10 files)
- Bulk operations (fix typos across codebase)
- Time-sensitive grunt work
- Tasks that can fail and retry

## Features

| Feature | Description |
|---------|-------------|
| Parallel execution | Multiple minions work simultaneously |
| Auto-retry | Failed tasks retry with simpler prompts |
| Minion-speak | Prompts get simplified on retry |
| Progress feedback | 🍌 bananas for completed tasks |

## Usage

### Same task on multiple files

```bash
python scripts/swarm.py patch "Add docstrings to all functions" \
  src/utils.py src/parser.py src/config.py \
  --workers 5 \
  --json
```

### Batch from JSON

Create a tasks file:

```json
[
  {"kind": "patch", "description": "Add type hints", "target": "src/utils.py"},
  {"kind": "patch", "description": "Add type hints", "target": "src/parser.py"},
  {"kind": "chat", "description": "Review error handling", "context_files": ["src/errors.py"]}
]
```

Run the swarm:

```bash
python scripts/swarm.py batch tasks.json --workers 5 --json
```

### From Claude (programmatic)

```python
from llm_gc.swarm import swarm_dispatch

results = swarm_dispatch(
    tasks=[
        {"kind": "patch", "description": "Add docstrings", "target": "src/a.py"},
        {"kind": "patch", "description": "Add docstrings", "target": "src/b.py"},
        {"kind": "patch", "description": "Add docstrings", "target": "src/c.py"},
    ],
    workers=5,
    max_retries=2,
    repo_root=".",
)

print(f"Completed: {results['stats']['completed']}")
print(f"Failed: {results['stats']['failed']}")
```

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
    "elapsed_seconds": 45.2
  }
}
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--workers` | 5 | Parallel workers |
| `--retries` | 2 | Max retries per task |
| `--rounds` | 2 | Chat rounds per task |
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
python scripts/swarm.py patch "Add docstrings to all public functions" $FILES \
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
