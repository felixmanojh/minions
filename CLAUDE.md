# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Local Multi LLM Group Chat (`llm-gc`) is a local-first coding assistant where multiple open-source models collaborate in a group chat to solve programming tasks. Models are agents with roles (Implementer, Reviewer, Bug Hunter, etc.) that critique each other's proposals before producing a final patch.

## Commands

### Prerequisites
```bash
# Start Ollama service (required)
ollama serve

# Install dependencies (one time)
python3 -m venv .venv
source .venv/bin/activate
pip install "pyautogen>=0.3" httpx pydantic[yaml] rich diff-match-patch grep-ast tree-sitter
```

### Running the Chat
```bash
source .venv/bin/activate
python scripts/m1_chat.py "Your task description" --rounds 3

# With file context
python scripts/m1_chat.py "Refactor X" --repo-root . --read PLAN.md --read src/main.py:1-50
```

### Ollama Model Management
```bash
ollama list                          # List available models
ollama pull qwen2.5-coder:1.5b       # Pull a model
curl http://127.0.0.1:11434/api/tags # Health check
```

## Architecture

```
llm_gc/
├── config/
│   ├── __init__.py     # ModelConfig pydantic model, load_models() from YAML
│   └── models.yaml     # Role -> Ollama model mapping (implementer, reviewer)
├── orchestrator/
│   ├── base.py         # OllamaClient (HTTP wrapper), ChatTurn, persist_transcript()
│   └── m1_chat.py      # ChatOrchestrator: turn scheduling, prompt building, repo context
└── tools/
    ├── file_reader.py  # FileReader with path sandboxing (repo root only)
    └── repo_summary.py # build_repo_summary(): README + git status + directory tree
```

**Data flow:**
1. `scripts/m1_chat.py` parses CLI args → calls `run_chat()`
2. `ChatOrchestrator` loads model configs, builds repo context (summary + file snippets)
3. Agents take turns: prompt built with system message + task + repo context + history
4. `OllamaClient.generate()` calls Ollama HTTP API at `localhost:11434`
5. Transcript persisted to `sessions/<timestamp>.json`

## Configuration

Models are configured in `llm_gc/config/models.yaml`:
```yaml
implementer:
  model: qwen2.5-coder:1.5b
  temperature: 0.2
  max_tokens: 512
reviewer:
  model: deepseek-coder:1.3b
  temperature: 0.15
  max_tokens: 400
```

Add new roles by adding entries here and corresponding `AgentSpec` in `m1_chat.py`.

## Milestones

- **M0**: Ollama setup (complete)
- **M1**: Basic group chat with Implementer/Reviewer (complete)
- **M2**: Read-only tools and repo summarizer (in progress)
- **M3**: Patch generation with unified diff (pending)
- **M4**: Guarded test runner and apply flow (pending)
- **M5**: Judge scoring and stopping rules (pending)

## Safety Constraints

- File operations are sandboxed to repo root via `FileReader._resolve()`
- No shell execution or file writes by agents (transcripts only)
- Token/round limits enforced by orchestrator
