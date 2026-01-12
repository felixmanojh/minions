---
name: minion-polish
description: >
  Auto-apply docstrings, type hints, and cleanup to files (<500 lines).
  Invoke after completing implementation. Changes are applied directly.
allowed-tools: Bash, Read
---

# Minion Polish

Dispatch local model to add mechanical polish. Changes are auto-applied.

## When to Invoke

- After implementing a feature
- Files need docstrings, type hints, cleanup
- Mechanical changes only (no logic changes)

## Command

```bash
source .venv/bin/activate && python scripts/minions.py --json polish <files> --task <task>
```

## Tasks

| Task | Description |
|------|-------------|
| `all` | Docstrings + types + headers (default) |
| `docstrings` | Add function/class docstrings |
| `types` | Add type hints |
| `headers` | Add module-level docstrings |

## Examples

```bash
# Polish single file
python scripts/minions.py --json polish src/foo.py --task all

# Multiple files
python scripts/minions.py --json polish src/foo.py src/bar.py --task docstrings

# Dry run
python scripts/minions.py --json polish src/foo.py --task all --dry-run
```

## Output

```json
{
  "applied": true,
  "files_modified": ["src/foo.py"],
  "changes": ["src/foo.py: Added 3 docstring(s)"],
  "errors": [],
  "stats": {"total": 1, "applied": 1, "failed": 0}
}
```

## Claude Integration

After completing code:
- Small (1-2 files): Auto-invoke, report summary
- Medium (3+ files): Ask user "Want me to dispatch minions for polish?"
