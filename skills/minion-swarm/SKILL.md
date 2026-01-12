---
name: minion-swarm
description: >
  Run same patch on multiple files in parallel.
  Use for batch operations across codebase.
allowed-tools: Bash, Read, Glob, Grep
---

# Minion Swarm

Parallel patches on multiple files.

## When to Invoke

- Same change needed on many files
- Adding headers/comments across codebase
- Batch mechanical operations

## Command

```bash
source .venv/bin/activate && python scripts/minions.py --json swarm "<task>" <files...>
```

## Examples

```bash
# Add header to multiple files
python scripts/minions.py --json swarm "Add # Minions header" src/a.py src/b.py src/c.py

# With more workers
python scripts/minions.py --json swarm "Add docstring" *.py --workers 5
```

## Output

```json
{
  "completed": [{"target": "src/a.py", "result": "success"}],
  "failed": [],
  "stats": {"completed": 3, "failed": 0, "total": 3}
}
```

## Limits

- Each file <500 lines
- Mechanical changes only
- Default 3 parallel workers
