# Minion Polish & Sweep Design

**Date:** 2026-01-12
**Status:** Approved

## Overview

Add two new minion capabilities for Claude Code integration:

1. **`minion:polish`** - Post-implementation cleanup that auto-applies changes
2. **`minion:sweep`** - Codebase-wide maintenance scans

**Core principle:** Minions apply changes directly and return summaries. Claude reviews summaries, minimizing token overhead.

## Motivation

Claude should delegate grunt work to local minions:

| Owner | Task Type | Examples |
|-------|-----------|----------|
| Claude | Intelligence | Planning, architecture, complex reasoning |
| Minion | Grunt work | Docstrings, type hints, formatting, comments |

With 32K context now available (configurable up to 128K), minions can handle files up to ~500-1000 lines.

## Design

### Trigger Behavior

| Scope | Trigger | Example |
|-------|---------|---------|
| Small (1-2 files) | Implicit - Claude auto-invokes | Added 1 function → auto-add docstring |
| Medium (3+ files) | Suggested - Claude asks first | "Want me to dispatch minions for polish?" |
| Large (codebase) | Explicit - user requests | "Sweep codebase for missing docstrings" |

### `minion:polish` Skill

**Purpose:** Post-implementation cleanup, auto-applied.

**Script:** `scripts/m_polish.py`

**Usage:**
```bash
python scripts/m_polish.py <files...> --task <task> [--json]
```

**Tasks:**
| Task | Description |
|------|-------------|
| `docstrings` | Add docstrings to functions/classes |
| `types` | Add type hints to parameters/returns |
| `headers` | Add module-level docstrings |
| `comments` | Add inline comments for complex logic |
| `all` | Combines all of the above |
| Custom | Any string, e.g. "add Google-style docstrings" |

**Output (JSON):**
```json
{
  "applied": true,
  "files_modified": ["src/foo.py", "src/bar.py"],
  "changes": [
    "Added docstring to foo.parse()",
    "Added type hints to bar.main()"
  ],
  "errors": []
}
```

**Internal flow:**
1. Read target file(s)
2. Build prompt: "Add {task} to this code: {content}"
3. Call minion (qwen2.5-coder:7b, 32K context)
4. Parse response - extract code block
5. Write directly to file (overwrite)
6. Return JSON summary

**Safety rails:**
| Guard | Action |
|-------|--------|
| Git dirty check | Warn if uncommitted changes |
| Backup | Optional `--backup` saves `.bak` files |
| Max file size | Skip files >500 lines with warning |
| Syntax check | `python -m py_compile` after write, revert if broken |

### `minion:sweep` Skill

**Purpose:** Codebase-wide maintenance, user-requested.

**Script:** `scripts/m_sweep.py`

**Usage:**
```bash
# Discover only
python scripts/m_sweep.py <directory> --task <task> --discover

# Discover + apply
python scripts/m_sweep.py <directory> --task <task> --apply
```

**Two-phase flow:**

**Phase 1: Discover**
- Scan directory for files missing docstrings/types
- Return list of candidates with details

**Phase 2: Apply**
- Run polish on each candidate
- Return aggregate summary

**Discovery output:**
```json
{
  "candidates": [
    {"file": "src/foo.py", "missing": ["docstrings"], "lines": 120},
    {"file": "src/bar.py", "missing": ["types", "docstrings"], "lines": 85}
  ],
  "total_files": 2,
  "skipped": ["src/big.py (>500 lines)"]
}
```

**Apply output:**
```json
{
  "applied": true,
  "files_modified": 2,
  "total_changes": 8,
  "changes_by_file": {
    "src/foo.py": ["Added 3 docstrings"],
    "src/bar.py": ["Added 2 docstrings", "Added 3 type hints"]
  },
  "errors": []
}
```

### Claude Integration Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Claude finishes implementing a feature                   │
│                                                             │
│ 2. Claude assesses: "This needs docstrings/types"           │
│                                                             │
│ 3. Small change (1-2 files):                                │
│    → Auto-invoke polish, apply silently                     │
│    → Mention in response: "Added docstrings via minion"     │
│                                                             │
│ 4. Medium change (3+ files):                                │
│    → Ask: "Want me to dispatch minions for polish?"         │
│    → User approves → invoke skill                           │
│                                                             │
│ 5. Claude runs:                                             │
│    python scripts/m_polish.py src/foo.py --task all --json  │
│                                                             │
│ 6. Claude reads JSON summary                                │
│                                                             │
│ 7. Claude reports to user:                                  │
│    "Minion added docstrings to 3 functions in foo.py"       │
└─────────────────────────────────────────────────────────────┘
```

### Skill Files

**`skills/minion-polish/SKILL.md`:**
```markdown
---
name: minion-polish
description: >
  Auto-apply docstrings, type hints, and cleanup to files (<500 lines).
  Claude invokes after completing implementation work.
allowed-tools: Bash, Read
---

# Minion Polish

Dispatch local model to add mechanical polish, auto-applied.

## When to Use

- After implementing a feature
- Files need docstrings, type hints, cleanup
- Mechanical changes only (no logic)

## Usage

\`\`\`bash
source .venv/bin/activate && python scripts/m_polish.py \
  <files...> \
  --task "docstrings" \
  --json
\`\`\`

## Tasks

- `docstrings` - Add function/class docstrings
- `types` - Add type hints
- `headers` - Add module docstrings
- `all` - All of the above

## Output

Returns JSON with applied changes. Report summary to user.
```

**`skills/minion-sweep/SKILL.md`:**
```markdown
---
name: minion-sweep
description: >
  Scan codebase for missing docstrings/types and batch-fix.
  User requests, Claude orchestrates.
allowed-tools: Bash, Read, Glob
---

# Minion Sweep

Codebase-wide maintenance scan.

## When to Use

- User requests "add docstrings to all files"
- Periodic codebase cleanup
- Tech debt reduction

## Usage

\`\`\`bash
# Discover what needs work
source .venv/bin/activate && python scripts/m_sweep.py \
  src/ --task docstrings --discover --json

# Apply fixes
source .venv/bin/activate && python scripts/m_sweep.py \
  src/ --task docstrings --apply --json
\`\`\`

## Output

Returns JSON with candidates (discover) or changes (apply).
```

## Implementation Plan

### Phase 1: Polish Script
1. Create `scripts/m_polish.py`
2. Implement file reading and prompt building
3. Implement direct file write with syntax check
4. Add JSON output
5. Create `skills/minion-polish/SKILL.md`

### Phase 2: Sweep Script
1. Create `scripts/m_sweep.py`
2. Implement discovery (scan for missing docs/types)
3. Implement batch apply using polish
4. Add JSON output
5. Create `skills/minion-sweep/SKILL.md`

### Phase 3: Testing
1. Test polish on single file
2. Test polish on multiple files
3. Test sweep discover mode
4. Test sweep apply mode
5. Test safety rails (backup, syntax check)

## Files to Create/Modify

| File | Action |
|------|--------|
| `scripts/m_polish.py` | Create |
| `scripts/m_sweep.py` | Create |
| `skills/minion-polish/SKILL.md` | Create |
| `skills/minion-sweep/SKILL.md` | Create |

## Already Completed

| File | Change |
|------|--------|
| `models.yaml` | Added `num_ctx: 32768` |
| `config/__init__.py` | Added `num_ctx` field + env override |
| `orchestrator/base.py` | Pass `num_ctx` to Ollama |
| `orchestrator/m1_chat.py` | Accept `num_ctx` override |
| `scripts/m1_chat.py` | Added `--num-ctx` CLI flag |
| `skills/minion-patch/SKILL.md` | Updated limits 50→500 |
| `skills/minion-swarm/SKILL.md` | Updated limits 50→500 |
| `README.md` | Updated limits + context docs |

## Success Criteria

1. `m_polish.py` can add docstrings to a file and auto-apply
2. `m_sweep.py` can discover files missing docstrings
3. `m_sweep.py --apply` can batch-fix discovered files
4. Claude can invoke skills and report results with minimal tokens
5. Safety rails prevent broken code from being written
