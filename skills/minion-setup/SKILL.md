---
name: minion-setup
description: Bootstrap the minions environment. Use when first installing minions, or to diagnose and fix setup issues. Detects missing components and installs only what's needed.
allowed-tools: Bash, Read, Write
---

# Minion Setup

Bootstrap your minion squad. This skill checks your environment and installs missing pieces.

## What it checks

1. **Ollama installed** → installs if missing
2. **Ollama running** → starts daemon if not
3. **Model preset** → asks user preference, pulls models
4. **Python venv** → creates if missing
5. **Dependencies** → installs if missing

## Run the setup

Execute step-by-step, checking each component:

### Step 1: Check Ollama installation

```bash
which ollama || echo "NOT_INSTALLED"
```

If `NOT_INSTALLED`:
- **macOS**: `brew install ollama`
- **Linux**: `curl -fsSL https://ollama.com/install.sh | sh`
- **Windows**: Direct user to https://ollama.ai/download/windows

### Step 2: Check Ollama daemon

```bash
curl -s http://127.0.0.1:11434/api/tags >/dev/null 2>&1 && echo "RUNNING" || echo "NOT_RUNNING"
```

If `NOT_RUNNING`:
```bash
ollama serve > /tmp/ollama.log 2>&1 &
sleep 3
```

### Step 3: Choose model preset

Ask the user which preset they want:

| Preset | Download Size | Best For |
|--------|---------------|----------|
| nano | ~1GB | Low RAM, quick tests |
| small | ~2GB | Most users (default) |
| medium | ~8GB | Better quality |
| large | ~25GB | Best quality |

Based on their choice, pull the appropriate models:

**nano:**
```bash
ollama pull qwen2.5-coder:0.5b
```

**small (default):**
```bash
ollama pull qwen2.5-coder:1.5b
ollama pull deepseek-coder:1.3b
```

**medium:**
```bash
ollama pull qwen2.5-coder:7b
ollama pull deepseek-coder:6.7b
```

**large:**
```bash
ollama pull qwen2.5-coder:14b
ollama pull deepseek-coder:33b
```

### Step 4: Update config with selected preset

Find the minions directory:
```bash
MINIONS_DIR=""
for dir in ~/.claude/plugins/minions ~/.local/share/minions ~/minions .; do
  if [ -f "$dir/llm_gc/__init__.py" ]; then
    MINIONS_DIR="$dir"
    break
  fi
done
echo "MINIONS_DIR: $MINIONS_DIR"
```

Update the preset in config (replace PRESET with user's choice):
```bash
sed -i.bak "s/^preset:.*/preset: small/" "$MINIONS_DIR/llm_gc/config/models.yaml"
```

### Step 5: Check Python venv

```bash
[ -d "$MINIONS_DIR/.venv" ] && echo "VENV_EXISTS" || echo "VENV_MISSING"
```

If missing:
```bash
cd "$MINIONS_DIR" && python3 -m venv .venv
```

### Step 6: Check Python dependencies

```bash
source "$MINIONS_DIR/.venv/bin/activate" && python -c "import httpx, pydantic, rich, yaml" 2>/dev/null && echo "DEPS_OK" || echo "DEPS_MISSING"
```

If missing:
```bash
source "$MINIONS_DIR/.venv/bin/activate" && pip install httpx pydantic pyyaml rich diff-match-patch
```

### Step 7: Verify everything works

```bash
source "$MINIONS_DIR/.venv/bin/activate" && python -c "
from llm_gc.config import load_models
models = load_models()
print(f'Loaded {len(models)} model configs')
for role, cfg in models.items():
    print(f'  {role}: {cfg.model}')

import httpx
resp = httpx.get('http://127.0.0.1:11434/api/tags')
print('SUCCESS: Ollama connected')
"
```

## Quick status check

Run this to see current status without fixing anything:

```bash
echo "=== Minions Status ==="
which ollama >/dev/null && echo "✓ Ollama installed" || echo "✗ Ollama missing"
curl -s http://127.0.0.1:11434/api/tags >/dev/null && echo "✓ Ollama running" || echo "✗ Ollama not running"
ollama list 2>/dev/null | head -5
echo "======================"
```

## Changing models later

Users can change their preset anytime:

1. Edit `llm_gc/config/models.yaml` and change `preset: small` to desired preset
2. Pull the new models: `ollama pull <model-name>`

Or use custom models by uncommenting the custom section in `models.yaml`.

## Troubleshooting

**"Ollama: command not found"**: Install Ollama first (Step 1).

**"Connection refused"**: Ollama daemon not running. Run `ollama serve &`.

**"Model not found"**: Pull the model: `ollama pull qwen2.5-coder:1.5b`

**Poor quality responses**: Try a larger preset (medium or large).

## After setup

Try your first minion command:

```bash
source .venv/bin/activate && python scripts/m1_chat.py "What files are in this project?"
```

Or run a batch operation:

```
/minion-swarm
```
