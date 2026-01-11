---
name: minion-patch
description: >
  Generate code patches using local minions. Good for: adding docstrings, fixing typos,
  renaming variables, adding type hints, simple boilerplate. NOT for: complex bugs,
  multi-file refactors, business logic. Produces a diff for review - always verify.
allowed-tools: Bash, Read, Glob, Grep
---

# Minion Patch

Generate a code patch using a local minion. Single-shot execution produces a unified diff.

## Decision Guide

| Task | Use Minion? | Why |
|------|-------------|-----|
| Fix typo | Yes | Mechanical |
| Add docstrings | Yes | Templated |
| Add type hints | Yes | Mechanical |
| Rename variable | Yes | Find-replace |
| Logic bug | No | Needs reasoning |
| Multi-file refactor | No | Use /minion-swarm |
| Security fix | No | Needs expertise |

**Quick test:** Is it "find and change"? → Minion can try.

## Usage

Basic patch:

```bash
source .venv/bin/activate && python scripts/m3_patch.py "Add docstrings to public functions" \
  --repo-root . \
  --target src/utils.py \
  --json
```

With context (minion sees related code):

```bash
source .venv/bin/activate && python scripts/m3_patch.py "Add type hints matching base.py style" \
  --repo-root . \
  --read llm_gc/orchestrator/base.py \
  --target llm_gc/tools/file_reader.py \
  --json
```

## Output

```json
{
  "task": "Add docstrings",
  "patch_path": "sessions/20250112-patch.patch",
  "metadata": {
    "patched_files": ["src/utils.py"]
  }
}
```

## Applying Patches

Preview:
```bash
cat sessions/*.patch
```

Dry-run:
```bash
patch -p1 --dry-run < sessions/20250112-patch.patch
```

Apply:
```bash
patch -p1 < sessions/20250112-patch.patch
```

## When to Escalate

- **Empty patch** → Add more context with `--read`
- **Many files** → Use /minion-swarm instead
- **Complex logic** → Use cloud models

## Limitations

- Small models may truncate output
- Best for 1-2 file changes
- Always review before applying
