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

### minion-swarm
Parallel execution. Dispatch many minions simultaneously with auto-retry.
- **Trigger**: "swarm minions", "minion swarm", "batch parallel"
- **Path**: `skills/minion-swarm/SKILL.md`

### minion-setup
Bootstrap and diagnostics. Check/install Ollama, models, and dependencies.
- **Trigger**: "setup minions", "minion setup", "configure minions"
- **Path**: `skills/minion-setup/SKILL.md`

## Model Roles

Each minion has a specialized role with an optimized model:

| Role | Model | Specialty |
|------|-------|-----------|
| **Implementer** | Qwen2.5-Coder | Code generation, 92+ languages |
| **Reviewer** | DeepSeek-Coder | Bug detection, 300+ languages |
| **Patcher** | StarCoder2 | FIM (fill-in-middle), surgical edits |

## Presets

Choose based on your hardware:

| Preset | Download | RAM | Models |
|--------|----------|-----|--------|
| lite | ~5GB | 8GB | Qwen2.5-Coder:7B (all roles) |
| **medium** | ~13GB | 16GB | Qwen + DeepSeek + StarCoder2 (7B each) |
| large | ~35GB | 32GB+ | 14B/33B/15B models |

> **Note:** We removed sub-7B presets. Small models (1.5B) produce unreliable output.

## Quick Setup

```bash
# One-liner install (recommended)
curl -fsSL https://raw.githubusercontent.com/felixmanojh/minions/main/install.sh | bash

# Or manual setup:
brew install ollama && ollama serve &
ollama pull qwen2.5-coder:7b
ollama pull deepseek-coder:6.7b
ollama pull starcoder2:7b
```

## Why These Models?

| Model | Why |
|-------|-----|
| **Qwen2.5-Coder** | Best overall under 10B, near GPT-4o on benchmarks |
| **DeepSeek-Coder** | Great debugging, "immediately usable" suggestions |
| **StarCoder2** | FIM-trained for surgical edits, 16K context |

## Banana Counter 🍌

Track your minion productivity! Each completed task earns bananas.

```bash
python scripts/bananas.py
```

Milestones: 🍌 Newbie → 🍌🍌🍌🍌🍌 Regular → 🍌👑 BANANA KING!
