# Minions

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ollama](https://img.shields.io/badge/Ollama-local%20LLMs-purple.svg)](https://ollama.ai)

Local LLM minions for mechanical code tasks — offload trivial patches to your local Ollama models.

## What Minions Can Do

| Task | Works? |
|------|--------|
| Add comment to small file (<50 lines) | Yes |
| Add simple docstring | Yes |
| Rename variable (simple cases) | Maybe |
| Anything requiring understanding | No |
| Files >50 lines | No (7b models truncate) |

**Be honest:** 7b models are limited. Minions are good for repetitive mechanical tasks on small files. That's it.

## Hard Limits

| Constraint | Limit |
|------------|-------|
| File size | <50 lines (models truncate longer) |
| Task type | Mechanical only (no logic, no reasoning) |
| Context | MUST pass `--read` or model hallucinates |
| Review | ALWAYS review patches before applying |

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

### Single File Patch

```bash
source .venv/bin/activate && python scripts/m3_patch.py \
  "Add comment '# TODO: refactor' at top" \
  --repo-root . \
  --read src/small_file.py \
  --target src/small_file.py \
  --json
```

**IMPORTANT:** Always pass `--read` with the target file. Without it, the model hallucinates.

### Multiple Files (Swarm)

```bash
source .venv/bin/activate && python scripts/swarm.py \
  --workers 2 \
  --json \
  patch "Add comment '# Minions' at top" \
  small_file_1.py small_file_2.py small_file_3.py
```

### Applying Patches

Always review and dry-run first:

```bash
# Review
cat sessions/*.patch

# Dry-run
patch -p1 --dry-run < sessions/*.patch

# Apply if clean
patch -p1 < sessions/*.patch
```

## Skills

| Skill | Purpose |
|-------|---------|
| `/minion-setup` | Check Ollama, models, dependencies |
| `/minion-patch` | Generate patch for single small file |
| `/minion-swarm` | Batch patch multiple small files |
| `/minion-apply` | Review and apply patches safely |
| `/minion-models` | Pull/list Ollama models |
| `/minion-metrics` | View session stats |

## Configuration

Edit `llm_gc/config/models.yaml`:

```yaml
preset: medium

patcher:
  model: qwen2.5-coder:7b
  temperature: 0.1
  max_tokens: 1024
```

Custom Ollama host:

```bash
export OLLAMA_BASE_URL="http://ollama.my-lab:11434"
```

## When NOT to Use Minions

- Files >50 lines
- Changes requiring understanding of code logic
- Security-sensitive code
- When correctness matters more than speed
- Complex refactoring

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Empty patch | File too big or already has change |
| Wrong file contents | Missing `--read` flag |
| Truncated output | File >50 lines |
| Patch doesn't apply | File changed - re-run |

## License

MIT
