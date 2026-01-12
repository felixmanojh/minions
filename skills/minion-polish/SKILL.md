---
name: minion-polish
description: >
  Auto-apply docstrings, type hints, and cleanup to files (<500 lines).
  Claude invokes after completing implementation work. Changes are applied directly.
allowed-tools: Bash, Read
---

# Minion Polish

Dispatch local model to add mechanical polish. Changes are auto-applied.

## When to Use

- After implementing a feature
- Files need docstrings, type hints, cleanup
- Mechanical changes only (no logic changes)

## Usage

```bash
source .venv/bin/activate && python scripts/m_polish.py \
  <files...> \
  --task <task> \
  --json
```

## Tasks

| Task | Description |
|------|-------------|
| `docstrings` | Add function/class docstrings |
| `types` | Add type hints to parameters/returns |
| `headers` | Add module-level docstrings |
| `comments` | Add inline comments for complex logic |
| `all` | All of the above (default) |
| Custom | Any prompt, e.g. "add Google-style docstrings" |

## Examples

```bash
# Add docstrings to a single file
python scripts/m_polish.py src/foo.py --task docstrings --json

# Add all polish to multiple files
python scripts/m_polish.py src/foo.py src/bar.py --task all --json

# Dry run (see what would change)
python scripts/m_polish.py src/foo.py --task types --dry-run

# Create backups before modifying
python scripts/m_polish.py src/foo.py --task all --backup --json
```

## Output

```json
{
  "applied": true,
  "files_modified": ["src/foo.py"],
  "changes": ["src/foo.py: Added 3 docstring(s), Added type hints"],
  "errors": [],
  "stats": {"total": 1, "applied": 1, "failed": 0}
}
```

## Safety

- Files >500 lines are skipped
- Python files are syntax-checked after modification
- If syntax check fails, changes are reverted
- Use `--backup` to create .bak files
- Use `--dry-run` to preview without applying

## Claude Integration

After completing implementation:

1. **Small change (1-2 files):** Auto-invoke, report summary
2. **Medium change (3+ files):** Ask user first

Example flow:
```
Claude: "Want me to dispatch minions to add docstrings and types?"
User: "yes"
Claude: [runs polish, reports summary]
```
