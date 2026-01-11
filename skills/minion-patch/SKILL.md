---
name: minion-patch
description: >
  Generate patches for SMALL files (<50 lines) using local 7b models.
  Only for mechanical changes: add comment, add simple docstring, rename.
  ALWAYS review output - minions hallucinate and truncate.
allowed-tools: Bash, Read, Glob, Grep
---

# Minion Patch

Generate a patch for a small file. Single-shot, no reasoning.

## Hard Limits

| Constraint | Limit |
|------------|-------|
| File size | <50 lines (7b models truncate longer files) |
| Task complexity | Mechanical only (no logic, no reasoning) |
| Context | MUST pass `--read` or minion hallucinates |

## What Actually Works

| Task | Works? | Notes |
|------|--------|-------|
| Add comment to small file | Yes | Tested |
| Add docstring to small class | Yes | <30 line files |
| Rename variable | Maybe | Simple cases |
| Add type hint | Maybe | If file is tiny |
| Fix typo | Maybe | If obvious |
| Anything requiring thought | No | Will hallucinate |
| Files >50 lines | No | Output truncates |

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

- File >50 lines
- Need to understand code logic
- Security-sensitive changes
- Anything where "correct" matters
