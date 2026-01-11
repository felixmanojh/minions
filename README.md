# Minions 🍌

**Local LLM minions for Claude Code** — summon a squad of specialized models to review, patch, and refactor your code.

```
        Claude Code (Cloud)
           planning, strategy, final review
─────────────────────────────────────────────
        Minions (Local)
           discussion, patches, grunt work
           private, fast, token-free
```

## What is this?

Minions is a Claude Code plugin that offloads coding tasks to local LLMs via [Ollama](https://ollama.ai). Instead of burning cloud tokens on routine work, summon your minion squad:

| Role | Model | Specialty |
|------|-------|-----------|
| **Implementer** | Qwen2.5-Coder | Code generation, 92+ languages |
| **Reviewer** | DeepSeek-Coder | Bug detection, 300+ languages |
| **Patcher** | StarCoder2 | FIM (fill-in-middle), surgical edits |

They debate, refine, and report back.

## Why?

| Cloud (Claude) | Local (Minions) |
|----------------|-----------------|
| Expensive tokens | Free (your hardware) |
| Best for strategy | Best for grunt work |
| Smart but costly | Specialized and fast |

Use Claude for the hard stuff. Send minions for the rest.

## Installation

### Quick Start (macOS/Linux)

```bash
curl -fsSL https://raw.githubusercontent.com/felixmanojh/minions/main/install.sh | bash
```

Then install the plugin:
```
/plugin marketplace add felixmanojh/minions
```

### Manual Setup

1. Install Ollama: `brew install ollama` or [ollama.ai](https://ollama.ai)
2. Pull models:
   ```bash
   ollama pull qwen2.5-coder:7b
   ollama pull deepseek-coder:6.7b
   ollama pull starcoder2:7b
   ```
3. Install plugin: `/plugin marketplace add felixmanojh/minions`

<details>
<summary>Windows users</summary>

1. Download Ollama from https://ollama.ai/download/windows
2. Open PowerShell:
   ```powershell
   ollama serve
   ollama pull qwen2.5-coder:7b
   ollama pull deepseek-coder:6.7b
   ollama pull starcoder2:7b
   ```
3. Install plugin in Claude Code

</details>

## Usage

Once installed, Claude Code discovers the skills automatically. Just ask:

> "Summon minions to review my auth implementation"

> "Have minions fix the pagination bug in src/paginator.py"

> "Swarm minions to add docstrings to all files in src/"

Or invoke directly:

```
/minion-huddle   # Multi-agent discussion
/minion-fix      # Generate a patch
/minion-swarm    # Parallel batch tasks
/minion-queue    # Queue tasks for later
```

## Skills

### `/minion-huddle`
Multi-agent discussion. Minions debate a topic and report findings.

### `/minion-fix`
Patch generation. Minions write code, critique it, and produce a unified diff.

### `/minion-swarm` 🍌
Parallel execution. Dispatch many minions simultaneously with auto-retry.

```bash
python scripts/swarm.py --workers 5 patch "Add docstrings" src/*.py
```

### `/minion-queue`
Batch tasks. Queue multiple jobs and process them asynchronously.

### `/minion-setup`
Bootstrap and diagnostics. Check/install Ollama, models, and dependencies.

## Presets

| Preset | Download | RAM | Description |
|--------|----------|-----|-------------|
| lite | ~5GB | 8GB | Single strong generalist model |
| **medium** | ~13GB | 16GB | Specialized model per role (recommended) |
| large | ~35GB | 32GB+ | Best for large repo refactoring |

> Note: download size varies slightly by quantization and platform.

Set via environment: `MINIONS_PRESET=medium`

## Configuration

Edit `llm_gc/config/models.yaml`:

```yaml
preset: medium

# Or override specific roles:
implementer:
  model: qwen2.5-coder:7b
  temperature: 0.2
  max_tokens: 1024

reviewer:
  model: deepseek-coder:6.7b
  temperature: 0.1
  max_tokens: 800

patcher:
  model: starcoder2:7b
  temperature: 0.1
  max_tokens: 1024
```

## Banana Counter 🍌

Track your minion productivity!

```bash
python scripts/bananas.py

# ========================================
# 🍌 BANANA STATS 🍌
# ========================================
# Total bananas: 127
# Today: 15
# Current streak: 3 days
```

Each completed task earns bananas. Milestones: 🍌 Newbie → 🍌🍌🍌🍌🍌 Regular → 🍌👑 BANANA KING!

## Architecture

```
minions/
├── .claude-plugin/          # Plugin metadata
├── skills/                  # Agent skills
│   ├── minion-huddle/       # Discussion
│   ├── minion-fix/          # Patch generation
│   ├── minion-swarm/        # Parallel execution
│   ├── minion-queue/        # Task queue
│   └── minion-setup/        # Bootstrap
├── llm_gc/                  # Python package
│   ├── orchestrator/        # Multi-agent loops
│   ├── config/              # Model configuration
│   ├── swarm.py             # Parallel execution
│   └── bananas.py           # 🍌 counter
├── scripts/                 # CLI entry points
└── sessions/                # Transcripts and patches
```

## Requirements

- Python 3.10+
- Ollama running locally
- 8-16GB RAM (depending on preset)
- Claude Code (for skill integration)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Ollama not found" | Install: `brew install ollama` |
| "Connection refused" | Start daemon: `ollama serve` |
| "Model not found" | Pull: `ollama pull qwen2.5-coder:7b` |
| Poor quality output | Use medium preset (7B models) |
| Patch doesn't apply | File changed — re-run |

## License

MIT

## Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## Acknowledgments

- [Aider](https://github.com/paul-gauthier/aider) for repo mapping inspiration
- [Ollama](https://ollama.ai) for local model inference
- The Minions movie for... inspiration 🍌
