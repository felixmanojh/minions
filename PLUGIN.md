---
name: minions
version: 0.1.0
description: Summon local LLM minions to discuss, review, and patch your code. Offload grunt work to local models while Claude handles strategy.
author: felix
repository: https://github.com/felixmanojh/minions
license: MIT
requires:
  - ollama
tags:
  - local-llm
  - multi-agent
  - code-review
  - patch-generation
---

# Minions Plugin

Local LLM minions for Claude Code — a squad of small models that debate, review, and patch your code locally.

## Skills included

| Skill | Description |
|-------|-------------|
| `minion-huddle` | Multi-agent discussion — minions debate a topic and report findings |
| `minion-fix` | Patch generation — minions write code and produce a unified diff |
| `minion-queue` | Task batching — queue multiple jobs for minions to process |

## Setup

1. Install [Ollama](https://ollama.ai) and pull models:
   ```bash
   ollama pull qwen2.5-coder:1.5b
   ollama pull deepseek-coder:1.3b
   ```

2. Ensure Ollama is running:
   ```bash
   ollama serve
   ```

3. Install Python dependencies in the plugin directory:
   ```bash
   cd ~/.claude/plugins/minions
   python3 -m venv .venv
   source .venv/bin/activate
   pip install httpx pydantic pyyaml rich diff-match-patch
   ```

## Usage

Once installed, ask Claude naturally:

- "Summon minions to review my auth code"
- "Have minions fix the bug in paginator.py"
- "Queue doc tasks for the utils module"

Or use slash commands: `/minion-huddle`, `/minion-fix`, `/minion-queue`

## Configuration

Edit `llm_gc/config/models.yaml` to customize models and roles.

## Requirements

- Ollama running locally
- Python 3.10+
- 8GB+ RAM for small models
