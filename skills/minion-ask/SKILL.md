---
name: minion-ask
description: >
  Ask a quick question to a local minion. Good for: explaining code, summarizing files,
  answering simple questions about the codebase. Single-shot, no patches, no modifications.
  Use for lightweight queries that don't need the full swarm.
allowed-tools: Bash, Read, Glob, Grep
---

# Minion Ask

Ask a quick question and get an answer from a local minion. No patches, no multi-round debates - just a simple question and response.

## When to use

- Explain what a function does
- Summarize a file or module
- Answer questions about code structure
- Quick sanity checks

## When NOT to use

- Making code changes → /minion-patch
- Multiple file operations → /minion-swarm
- Complex reasoning → use cloud models

## Usage

### Basic question

```bash
source .venv/bin/activate && python scripts/m1_chat.py "What does this function do?" \
  --read src/utils.py \
  --rounds 1 \
  --json
```

### With specific lines

```bash
source .venv/bin/activate && python scripts/m1_chat.py "Explain this code" \
  --read "src/parser.py:50-100" \
  --rounds 1 \
  --json
```

### Multiple context files

```bash
source .venv/bin/activate && python scripts/m1_chat.py "How do these modules relate?" \
  --read src/api.py \
  --read src/models.py \
  --read src/db.py \
  --rounds 1 \
  --json
```

## Output

```json
{
  "task": "What does this function do?",
  "summary": "The `parse_config` function reads a YAML file...",
  "transcript_path": "sessions/20250112-chat.md",
  "metadata": {
    "model": "qwen2.5-coder:1.5b",
    "latency_ms": 1200
  }
}
```

## Good questions for minions

| Question Type | Example |
|---------------|---------|
| Explain | "What does this function do?" |
| Summarize | "Summarize this module in 3 sentences" |
| Compare | "What's the difference between A and B?" |
| List | "What are the public methods in this class?" |
| Describe | "What does this regex match?" |

## Bad questions for minions

| Don't Ask | Why | Instead |
|-----------|-----|---------|
| "Find bugs" | Needs reasoning | Use cloud models |
| "Is this secure?" | Needs expertise | Use security tools |
| "Optimize this" | Needs context | Use cloud models |
| "Refactor this" | Creates changes | Use /minion-patch |

## Tips

- Keep questions specific and focused
- Provide relevant context with `--read`
- Use `--rounds 1` for single-shot (faster)
- Use `--json` for machine-readable output
