---
name: minion-sweep
description: >
  Scan codebase for missing docstrings/types and batch-fix.
  User requests, Claude orchestrates. Two phases: discover then apply.
allowed-tools: Bash, Read, Glob
---

# Minion Sweep

Codebase-wide maintenance scan.

## When to Use

- User requests "add docstrings to all files"
- Periodic codebase cleanup
- Tech debt reduction

## Two-Phase Workflow

### Phase 1: Discover

```bash
source .venv/bin/activate && python scripts/m_sweep.py \
  <directory> --task <task> --json
```

Output shows what needs work:
```json
{
  "candidates": [
    {"file": "src/foo.py", "lines": 120, "missing": ["3 functions without docstrings"]},
    {"file": "src/bar.py", "lines": 85, "missing": ["module docstring", "2 functions without type hints"]}
  ],
  "skipped": [{"file": "src/big.py", "reason": ">500 lines"}],
  "total_candidates": 2,
  "total_skipped": 1
}
```

### Phase 2: Apply

```bash
source .venv/bin/activate && python scripts/m_sweep.py \
  <directory> --task <task> --apply --json
```

## Tasks

| Task | What it checks |
|------|----------------|
| `docstrings` | Missing function/class/module docstrings |
| `types` | Missing type hints on functions |
| `headers` | Missing module-level docstrings only |
| `all` | All of the above (default) |

## Examples

```bash
# Discover what needs docstrings in src/
python scripts/m_sweep.py src/ --task docstrings --json

# Apply docstrings to everything found
python scripts/m_sweep.py src/ --task docstrings --apply --json

# Full sweep with backups
python scripts/m_sweep.py . --task all --apply --backup --json

# Increase file size limit
python scripts/m_sweep.py src/ --task all --max-lines 1000 --json
```

## Options

| Flag | Description |
|------|-------------|
| `--discover` | Only show what needs work (default) |
| `--apply` | Fix all discovered files |
| `--max-lines N` | Skip files over N lines (default: 500) |
| `--backup` | Create .bak files before modifying |
| `--num-ctx N` | Override context window size |

## Claude Integration

When user requests codebase maintenance:

1. **Discover first:** Run sweep without `--apply` to show scope
2. **Confirm with user:** "Found 12 files needing docstrings. Apply?"
3. **Apply on approval:** Run sweep with `--apply`
4. **Report summary:** "Added docstrings to 10/12 files, 2 failed (>500 lines)"
