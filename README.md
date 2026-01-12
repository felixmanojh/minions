# Minions

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ollama](https://img.shields.io/badge/Ollama-local%20LLMs-purple.svg)](https://ollama.ai)

Local LLM minions for mechanical code tasks — offload grunt work to your local Ollama models.

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

## Limits

| Constraint | Limit |
|------------|-------|
| File size | <500 lines (32K context, configurable) |
| Task type | Mechanical only (no logic, no reasoning) |

## Installation

### Prerequisites

1. Install Ollama: `brew install ollama` or [ollama.ai](https://ollama.ai)
2. Pull model:
   ```bash
   ollama pull qwen2.5-coder:7b
   ```

### Install Minions

```bash
git clone https://github.com/felixmanojh/minions.git
cd minions
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Add Skills to Claude Code (Optional)

```bash
cp -r skills/* ~/.claude/skills/
```

## Usage

### Polish (Auto-Apply)

Add docstrings, types, comments — changes applied directly:

```bash
# Add all polish (docstrings + types + headers)
python scripts/m_polish.py src/foo.py --task all --json

# Just docstrings
python scripts/m_polish.py src/foo.py --task docstrings --json

# Multiple files
python scripts/m_polish.py src/foo.py src/bar.py --task types --json

# Dry run (preview without applying)
python scripts/m_polish.py src/foo.py --task all --dry-run
```

### Sweep (Codebase Scan)

Find and fix files missing documentation:

```bash
# Discover what needs work
python scripts/m_sweep.py src/ --task docstrings --json

# Apply fixes to all discovered files
python scripts/m_sweep.py src/ --task docstrings --apply --json

# Full sweep with backups
python scripts/m_sweep.py . --task all --apply --backup --json
```

### Patch (Manual Review)

Generate patches for review before applying:

```bash
python scripts/m3_patch.py "Add TODO comment at top" \
  --repo-root . \
  --read src/file.py \
  --target src/file.py \
  --json

# Review and apply
patch -p1 --dry-run < sessions/*.patch
patch -p1 < sessions/*.patch
```

### Swarm (Batch Patch)

Same patch on multiple files in parallel:

```bash
python scripts/swarm.py \
  --workers 2 \
  patch "Add header comment" \
  file1.py file2.py file3.py
```

## Skills

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
preset: medium

presets:
  medium:
    implementer:
      model: qwen2.5-coder:7b
      temperature: 0.2
      max_tokens: 1024
      num_ctx: 32768  # 32K context
```

### Context Window Size

Larger context = more file capacity, but slower:

```bash
# CLI flag (highest priority)
python scripts/m_polish.py file.py --task all --num-ctx 65536

# Environment variable
export MINIONS_NUM_CTX=65536
```

| Size | Use Case | Speed |
|------|----------|-------|
| 32K (default) | Files <500 lines | Fast |
| 64K | Files <1000 lines | Medium |
| 128K (max) | Very large files | Slow |

### Custom Ollama Host

```bash
export OLLAMA_BASE_URL="http://ollama.my-lab:11434"
```

## When NOT to Use Minions

- Files >500 lines (increase `--num-ctx` for larger)
- Changes requiring understanding of code logic
- Security-sensitive code
- Complex refactoring

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Syntax error after polish | Auto-reverted, minion made mistake |
| Empty patch | File unchanged or too big |
| Truncated output | Increase `--num-ctx` |

## License

MIT
