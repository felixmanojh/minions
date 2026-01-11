---
name: minion-swarm
description: >
  Dispatch minions to apply the same mechanical transformation to many files in parallel.
  Good for: adding docstrings, type hints, renaming variables, fixing typos across a codebase.
  NOT for: finding bugs, code review, or anything requiring judgment.
allowed-tools: Bash, Read, Glob, Grep
---

# Minion Swarm

Apply the same mechanical transformation to many files in parallel.

## What swarm is for

**The pattern:** "Do {mechanical task} to {N files}"

```
"Add docstrings" × 20 files
"Add type hints" × 30 files
"Rename oldName to newName" × 15 files
"Fix trailing whitespace" × 50 files
```

## What swarm is NOT for

- Finding bugs (minions miss them)
- Code review (minions lack judgment)
- Security checks (use real tools)
- Anything requiring "understanding"

## Usage

### Basic: Same task, multiple files

```bash
source .venv/bin/activate && python scripts/swarm.py patch "Add docstrings to all functions" \
  src/utils.py src/parser.py src/config.py \
  --workers 5 \
  --json
```

### Glob pattern

```bash
source .venv/bin/activate && python scripts/swarm.py patch "Add type hints" \
  src/**/*.py \
  --workers 5 \
  --json
```

### Programmatic

```python
from llm_gc.swarm import Swarm
import asyncio

swarm = Swarm(workers=5, max_retries=2)
swarm.add_patch("Add docstrings", target="src/a.py")
swarm.add_patch("Add docstrings", target="src/b.py")
swarm.add_patch("Add docstrings", target="src/c.py")

result = asyncio.run(swarm.run())
print(f"Completed: {result['stats']['completed']}")
```

## Good swarm tasks

| Task | Why it works |
|------|--------------|
| Add docstrings | Templated, mechanical |
| Add type hints | Pattern matching |
| Rename variable | Find-replace |
| Fix import order | Mechanical |
| Add license header | Boilerplate |
| Remove trailing whitespace | Trivial |

## Bad swarm tasks

| Task | Why it fails |
|------|--------------|
| Find bugs | Requires reasoning |
| Check for issues | Vague, unreliable |
| Review code | Needs judgment |
| Fix logic errors | Needs understanding |

## Auto-retry

When a minion fails, swarm retries with simpler prompts:

| Retry | Transformation |
|-------|---------------|
| 0 | Original prompt |
| 1 | Strip fluff + "SIMPLE TASK. ONE THING ONLY." |
| 2 | First 20 words + "DO THIS:" |

## Output

```json
{
  "completed": [
    {"description": "Add docstrings to src/a.py", "result": "sessions/xxx.patch"}
  ],
  "failed": [
    {"description": "Add docstrings to src/b.py", "error": "Output truncated"}
  ],
  "stats": {
    "total": 3,
    "completed": 2,
    "failed": 1,
    "bananas_earned": 2
  }
}
```

## Banana Stats 🍌

Track completed tasks across sessions:

```bash
source .venv/bin/activate && python scripts/bananas.py
```

Milestones: 🍌 (starting) → 🍌🍌🍌🍌🍌 x10 (regular) → 🍌👑 (500+ BANANA KING)

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--workers` | 5 | Parallel minions |
| `--retries` | 2 | Max retries per task |
| `--json` | false | Machine-readable output |

## Tips

1. **Keep tasks specific** - "Add docstrings" not "improve code"
2. **One transformation** - Don't combine tasks
3. **Review all patches** - Minions make mistakes
4. **More workers for trivial tasks** - `--workers 10` for whitespace fixes
