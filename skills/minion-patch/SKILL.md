---
name: minion-patch
description: >
  Generate patches for files up to ~500 lines using local 7b models (32K context).
  Only for mechanical changes: add comment, add docstring, rename, type hints.
  ALWAYS review output - minions can still hallucinate.
allowed-tools: Bash, Read, Glob, Grep
---

# Minion Patch

Generate a patch for a file. Single-shot, no reasoning.

## Limits

| Constraint | Limit |
|------------|-------|
| File size | <500 lines (32K context window) |
| Task complexity | Mechanical only (no logic, no reasoning) |
| Context | MUST pass `--read` or minion hallucinates |

## What Actually Works

| Task | Works? | Notes |
|------|--------|-------|
| Add comment | Yes | Tested |
| Add docstring | Yes | Functions, classes, modules |
| Add type hints | Yes | Parameters and returns |
| Rename variable | Yes | Simple cases |
| Fix typo | Yes | If obvious |
| Anything requiring thought | No | Will hallucinate |
| Files >500 lines | No | May truncate |

## Usage

**ALWAYS include `--read` with the target file:**

```bash
source .venv/bin/activate && python scripts/m3_patch.py "Add comment '# TODO' at top" \
  --repo-root . \
  --read src/small_file.py \
  --target src/small_file.py \
  --json
```

Without `--read`, the minion will hallucinate file contents.

## Applying Patches

**Always dry-run first:**

```bash
patch -p1 --dry-run < sessions/*.patch
```

If clean, apply:

```bash
patch -p1 < sessions/*.patch
```

## Failure Modes

| Symptom | Cause | Fix |
|---------|-------|-----|
| Wrong file contents | No `--read` | Add `--read` flag |
| Truncated output | File too big | Use smaller file or cloud model |
| Empty patch | No changes needed | Task already done |
| Diff format in output | Model confused | Re-run, check prompt |
| Wrong path in patch | Model said `python` | Fallback should handle |

## When NOT to Use

- File >500 lines
- Need to understand code logic
- Security-sensitive changes
- Anything where "correct" matters
