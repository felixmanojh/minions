# Minions

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ollama](https://img.shields.io/badge/Ollama-local%20LLMs-purple.svg)](https://ollama.ai)

Local LLM minions for mechanical code tasks — offload grunt work to your local Ollama models.

## The Idea

Think of it like Gru and his Minions: Gru (Claude Code) handles the master plan — architecture, complex logic, decisions. The Minions (local LLMs) handle the repetitive grunt work — adding docstrings to 50 files, type hints across a module.

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code (Cloud)                      │
│         Planning • Strategy • Complex reasoning             │
└─────────────────────────────┬───────────────────────────────┘
                              │ delegates mechanical tasks
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Minions (Local)                          │
│         Docstrings • Type hints • Repetitive fixes         │
│              Free • Private • On your hardware              │
└─────────────────────────────────────────────────────────────┘
```

**Why this split?**

| Cloud (Claude Code) | Local (Minions) |
|---------------------|-----------------|
| Expensive tokens | Free (your GPU) |
| Best for reasoning | Best for grunt work |
| Complex decisions | Mechanical repetition |
| Smart but costly | Cheap and focused |

Use Claude for the hard stuff. Send minions for the rest.

## What Minions Can Do

| Task | Works? |
|------|--------|
| Add docstrings | Yes |
| Add type hints | Yes |
| Add comments | Yes |
| Rename variable (simple cases) | Yes |
| Files up to ~500 lines | Yes (32K context) |
| Anything requiring understanding | No |

**Be honest:** 7b models are limited. Minions handle repetitive mechanical tasks. No reasoning, no logic.

## How It Works

Minions use a **Generate → Validate → Retry** pipeline:

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Generate │ ──▶ │ AST Lint │ ──▶ │ Validate │ ──▶ │  Apply   │
│ (minion) │     │ (syntax) │     │  (LLM)   │     │ (if ok)  │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                      │                │
                      └───── Retry ────┘
                        (with error)
```

1. **Generate**: Minion model creates code changes
2. **AST Lint**: Fast syntax check catches obvious errors
3. **Validate**: Second LLM checks task completion & preservation
4. **Retry**: On failure, error is sent back to minion to fix
5. **Apply**: Only after validation passes

Failures are logged to `~/.minions/` for debugging.

## Limits

| Constraint | Limit |
|------------|-------|
| File size | <500 lines (32K context, configurable) |
| Task type | Mechanical only (no logic, no reasoning) |

## Installation

### Prerequisites

1. Install Ollama: `brew install ollama` or [ollama.ai](https://ollama.ai)
2. Pull models:
   ```bash
   ollama pull qwen2.5-coder:7b
   ollama pull qwen2.5-coder:1.5b  # for validation
   ```

### Install Minions

```bash
git clone https://github.com/felixmanojh/minions.git
cd minions
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Interactive Setup

```bash
minions setup -i
```

Guides you through model selection and downloads.

### Add Skills to Claude Code (Optional)

```bash
cp -r skills/* ~/.claude/skills/
```

## Usage

### Unified CLI

```bash
minions <command> [options]
```

### Polish (Auto-Apply)

Add docstrings, types, comments — validated before applying:

```bash
# Add all polish (docstrings + types + headers)
minions polish src/foo.py --task all

# Just docstrings
minions polish src/foo.py --task docstrings

# Multiple files
minions polish src/foo.py src/bar.py --task types

# Dry run (preview without applying)
minions polish src/foo.py --task all --dry-run

# Skip validation (faster, less safe)
minions polish src/foo.py --task all --no-validate

# Use custom linter
minions polish src/foo.py --task all --lint-cmd "ruff check"

# More retries on failure
minions polish src/foo.py --task all --max-retries 3
```

### Sweep (Codebase Scan)

Find and fix files missing documentation:

```bash
# Discover what needs work
minions sweep src/ --task docstrings

# Apply fixes to all discovered files
minions sweep src/ --task docstrings --apply

# Full sweep with backups
minions sweep . --task all --apply --backup
```

### Patch (Manual Review)

Generate patches for review before applying:

```bash
minions patch "Add TODO comment at top" \
  --target src/file.py \
  --read src/file.py

# Review and apply
patch -p1 --dry-run < sessions/*.patch
patch -p1 < sessions/*.patch
```

### Swarm (Batch Patch)

Same patch on multiple files in parallel:

```bash
minions swarm "Add header comment" file1.py file2.py file3.py --workers 3
```

### Setup & Status

```bash
# Quick status check
minions setup

# Interactive model configuration
minions setup -i
```

## CLI Options

### Polish & Sweep

| Flag | Description |
|------|-------------|
| `--task` | docstrings, types, headers, comments, all |
| `--preset` | lite, standard, expert |
| `--dry-run` | Preview without applying |
| `--backup` | Create .bak files |
| `--no-lint` | Skip AST syntax check |
| `--no-validate` | Skip LLM validation |
| `--lint-cmd` | Custom linter (e.g., "ruff check") |
| `--max-retries` | Retry attempts on failure (default: 1) |
| `--no-retry` | Disable retry loop |
| `--num-ctx` | Context window size |

## Skills (Claude Code)

| Skill | Purpose |
|-------|---------|
| `/minion-polish` | Auto-apply docstrings, types, cleanup |
| `/minion-sweep` | Scan codebase and batch-fix missing docs |
| `/minion-patch` | Generate patch for single file |
| `/minion-swarm` | Batch patch multiple files in parallel |
| `/minion-setup` | Check Ollama, models, dependencies |
| `/minion-apply` | Review and apply patches safely |
| `/minion-models` | Pull/list Ollama models |
| `/minion-metrics` | View session stats |

## Configuration

Edit `llm_gc/config/models.yaml`:

```yaml
preset: standard

validation:
  max_retries: 1
  notify_on_fail: true

presets:
  lite:
    minion:
      model: qwen2.5-coder:7b
      temperature: 0.2
      max_tokens: 1024
      num_ctx: 32768
    validator: same  # use minion for validation

  standard:
    minion:
      model: qwen2.5-coder:7b
      temperature: 0.2
      max_tokens: 1024
      num_ctx: 32768
    validator:
      model: qwen2.5-coder:1.5b
      temperature: 0.1
      max_tokens: 400
      num_ctx: 16384

  expert:
    minion:
      model: qwen2.5-coder:14b
      temperature: 0.2
      max_tokens: 2048
      num_ctx: 65536
    validator:
      model: deepseek-coder:33b
      temperature: 0.1
      max_tokens: 400
      num_ctx: 32768
```

### Environment Overrides

```bash
MINIONS_MODEL=qwen2.5-coder:14b      # Override minion model
MINIONS_VALIDATOR=codellama:7b       # Override validator model
MINIONS_NUM_CTX=65536                # Override context window
MINIONS_PRESET=expert                # Override preset
```

### Context Window Size

Larger context = more file capacity, but slower:

| Size | Use Case | Speed |
|------|----------|-------|
| 32K (default) | Files <500 lines | Fast |
| 64K | Files <1000 lines | Medium |
| 128K (max) | Very large files | Slow |

### Custom Ollama Host

```bash
export OLLAMA_BASE_URL="http://ollama.my-lab:11434"
```

## Failure Logs

When validation fails after all retries, details are saved to:

```
~/.minions/
├── failures.log          # Quick reference (one line per failure)
└── sessions/
    └── 20260112_143022.json  # Full session data
```

Use for debugging: `tail ~/.minions/failures.log`

## When NOT to Use Minions

- Files >500 lines (increase `--num-ctx` for larger)
- Changes requiring understanding of code logic
- Security-sensitive code
- Complex refactoring

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Validation keeps failing | Check `~/.minions/failures.log` for details |
| Slow generation | Use `--no-validate` or `lite` preset |
| Syntax errors | AST lint should catch these; check logs |
| Empty patch | File unchanged or too big |
| Truncated output | Increase `--num-ctx` |

## License

MIT
