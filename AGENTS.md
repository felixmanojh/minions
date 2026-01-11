# Minions - Agent Skills

> Local LLM minions for AI coding agents — offload grunt work to small local models.

This plugin works with Claude Code, Cursor, Windsurf, Cline, and any agent that reads AGENTS.md.

## Skills

### minion-huddle
Multi-agent discussion. Minions debate a topic and report findings.
- **Trigger**: "summon minions to discuss", "have minions review", "minion huddle"
- **Path**: `skills/minion-huddle/SKILL.md`

### minion-fix
Patch generation. Minions write code, critique it, and produce a unified diff.
- **Trigger**: "have minions fix", "minion patch", "minion fix"
- **Path**: `skills/minion-fix/SKILL.md`

### minion-queue
Task batching. Queue multiple jobs for async processing.
- **Trigger**: "queue for minions", "batch minion tasks", "minion queue"
- **Path**: `skills/minion-queue/SKILL.md`

### minion-setup
Bootstrap and diagnostics. Check/install Ollama, models, and dependencies.
- **Trigger**: "setup minions", "minion setup", "configure minions"
- **Path**: `skills/minion-setup/SKILL.md`

## Requirements

- [Ollama](https://ollama.ai) running locally
- Models based on your chosen preset:

| Preset | RAM | Models |
|--------|-----|--------|
| nano | ~1GB | qwen2.5-coder:0.5b |
| small | ~2GB | qwen2.5-coder:1.5b, deepseek-coder:1.3b |
| medium | ~8GB | qwen2.5-coder:7b, deepseek-coder:6.7b |
| large | ~25GB | qwen2.5-coder:14b, deepseek-coder:33b |

## Quick Setup

```bash
# Install Ollama
brew install ollama  # macOS
# or: curl -fsSL https://ollama.com/install.sh | sh  # Linux

# Start daemon
ollama serve &

# Pull models for your preset (example: small)
ollama pull qwen2.5-coder:1.5b
ollama pull deepseek-coder:1.3b
```

Then use any skill by asking naturally or invoking `/minion-huddle`, `/minion-fix`, etc.
