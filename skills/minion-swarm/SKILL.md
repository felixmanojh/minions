---
name: minion-swarm
description: >
  Run same mechanical patch on multiple SMALL files (<50 lines each) in parallel.
  7b models truncate longer files. Only for trivial changes. Review everything.
allowed-tools: Bash, Read, Glob, Grep
---

# Minion Swarm

Same patch task on multiple small files in parallel.

## Hard Limits

| Constraint | Limit |
|------------|-------|
| File size | <50 lines each (7b truncates longer) |
| Task type | Mechanical only |
| Review | MUST review every patch |

## What Actually Works

Tested with qwen2.5-coder:7b:

| Scenario | Result |
|----------|--------|
| Add comment to 22-line file | Success |
| Add comment to 130-line file | Failed (truncated) |
| Task on file without `--read` | Hallucinated |

## Usage

```bash
source .venv/bin/activate && python scripts/swarm.py \
  --workers 2 \
  --json \
  patch "Add comment '# Minions' at top" \
  small_file_1.py small_file_2.py small_file_3.py
```

The script automatically passes each file as `--read` context.

## Output

```json
{
  "completed": [{"target": "small_file_1.py", "result": "sessions/xxx.patch"}],
  "failed": [{"target": "big_file.py", "status": "empty"}],
  "stats": {"completed": 1, "failed": 1, "bananas_earned": 1}
}
```

## What "Failed" Means

| Status | Meaning |
|--------|---------|
| `empty` | No patch generated (file unchanged or truncated) |
| `error` | Exception during execution |

"Empty" usually means:
1. File already had the change (correct)
2. File too big, output truncated (limitation)
3. Model confused (re-run)

## Applying Patches

```bash
# Review first
cat sessions/*.patch

# Dry-run
patch -p1 --dry-run < sessions/*.patch

# Apply if clean
patch -p1 < sessions/*.patch
```

## When NOT to Use

- Any file >50 lines
- Changes requiring understanding
- Security-sensitive code
- When correctness matters more than speed

## Realistic Use Case

"I have 10 tiny config files and want to add a header comment to each"

That's it. That's what swarm is actually good for.
