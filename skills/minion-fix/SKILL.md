---
name: minion-fix
description: >
  Delegate mechanical code changes to local minions (1-3B models). Good for: adding docstrings,
  fixing typos, renaming variables, adding type hints, simple format changes, boilerplate code.
  NOT for: complex bug fixes, multi-file refactors, anything requiring understanding of business
  logic. Minions produce a diff for review - always verify before applying. Use for grunt work only.
allowed-tools: Bash, Read, Glob, Grep
---

# Minion Fix

Command a minion to produce a code patch. A single-shot task produces a unified diff ready to apply.

## Should I Use Minions? (Decision Guide)

Before delegating a fix, assess if minions can handle it:

| Fix Type | Use Minions? | Why |
|----------|--------------|-----|
| Fix typo, rename variable | ✓ Yes | Mechanical, no reasoning |
| Add docstrings | ✓ Yes | Templated, pattern-based |
| Add type hints | ✓ Yes | Mechanical annotation |
| Simple boilerplate | ✓ Yes | Copy-paste style work |
| Logic bug fix | ✗ No | Needs understanding |
| Multi-file refactor | ✗ No | Needs broader context |
| Performance fix | ✗ No | Needs analysis |
| Security fix | ✗ No | Needs real reasoning |

**Quick test:** Is this a "find and change" task? → Minions can try.

## When to use

- Clear, scoped bug fixes or small features
- You want a draft patch to review (not auto-apply)
- Saving cloud tokens on routine fixes
- The change is localized to a few files

## Prerequisites

Ensure Ollama is running:

```bash
ollama serve
ollama list   # verify qwen2.5-coder:1.5b and deepseek-coder:1.3b exist
```

## Usage

Basic fix with explicit target (uses user's configured preset):

```bash
python scripts/m3_patch.py "Add docstrings to all public functions" \
  --repo-root . \
  --target src/utils.py \
  --rounds 4 \
  --json
```

With context files (minions see related code):

```bash
python scripts/m3_patch.py "Add type hints matching the style in base.py" \
  --repo-root . \
  --read llm_gc/orchestrator/base.py \
  --target llm_gc/tools/file_reader.py \
  --rounds 4 \
  --json
```

Let minions decide which files to change:

```bash
python scripts/m3_patch.py "Fix all TODO comments in the tools module" \
  --repo-root . \
  --read llm_gc/tools/__init__.py \
  --rounds 4 \
  --json
```

## Output

```json
{
  "task": "Fix the off-by-one error",
  "summary": "Final reviewer assessment...",
  "transcript_path": "sessions/20250111-120000-m3.json",
  "patch_path": "sessions/20250111-120000-m3.patch",
  "metadata": {
    "patched_files": ["src/pagination.py"]
  }
}
```

## Reviewing the patch

Preview the generated diff:

```bash
cat sessions/20250111-120000-m3.patch
```

Apply if it looks good:

```bash
patch -p1 < sessions/20250111-120000-m3.patch
```

Dry-run first:

```bash
patch -p1 --dry-run < sessions/20250111-120000-m3.patch
```

## Integration pattern

1. Identify a scoped fix suitable for minions
2. Determine target files and context files
3. Invoke minion-fix with `--json`
4. Read the patch file and present to user for review
5. Apply patch after user approval (or suggest manual edits if patch is incomplete)

## Limitations

- Small models may produce incomplete patches (truncated output)
- Best for single-file or 2-3 file changes
- Review carefully — minions can introduce bugs
- No test execution — you must verify the fix works

## When to escalate

If the patch is:
- Empty or malformed → ask minions with more context, or handle manually
- Touches many files → break into smaller tasks or use /minion-swarm
- Requires complex reasoning → use cloud models instead

## Troubleshooting

**Empty patch file**: Model output was truncated or didn't follow format. Try:
- Providing more context with `--read`
- Using fewer target files
- Increasing rounds to 5

**Patch doesn't apply cleanly**: File changed since minions saw it. Re-run with fresh context.

**"No valid file blocks found"**: Model didn't output code in expected format. Check transcript for what it actually said.
