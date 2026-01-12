# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Minions** - Local LLM helpers for mechanical code tasks. Offload grunt work (docstrings, type hints, comments) to local Ollama models with a Generate → Validate → Retry safety pipeline.

## Commands

### Quick Start
```bash
ollama serve                              # Start Ollama
minions setup                             # Check status
minions setup -i                          # Interactive config
```

### Common Tasks
```bash
# Polish files (auto-apply with validation)
minions polish src/file.py --task docstrings
minions polish src/*.py --task all --dry-run

# Sweep codebase
minions sweep src/ --task all --apply

# Generate patch for review
minions patch "Add header comment" --target src/file.py

# Batch patch
minions swarm "Add docstrings" file1.py file2.py --workers 3
```

### Testing
```bash
source .venv/bin/activate
pytest tests/ -v
```

## Architecture

```
llm_gc/
├── config/
│   ├── __init__.py     # get_configs(), MinionConfigs, ModelConfig
│   └── models.yaml     # Presets: lite/standard/expert
├── orchestrator/
│   ├── base.py         # OllamaClient, ChatTurn, persist_transcript()
│   ├── m1_chat.py      # Single-shot minion task executor
│   └── m3_patch.py     # Patch generator
├── linter.py           # AST syntax checking (tree-sitter + Python compile)
├── validator.py        # LLM-based validation (PASS/FAIL)
├── logging.py          # Failure logs to ~/.minions/
├── setup.py            # Interactive model configuration
└── tools/
    └── ...             # File reading, repo summary, diff generation

scripts/
├── minions.py          # Unified CLI entry point
├── m_polish.py         # Polish command (Generate → Validate → Apply)
├── m_sweep.py          # Codebase sweep + batch polish
└── swarm.py            # Parallel patch execution
```

## Validation Pipeline

```
Generate → AST Lint → LLM Validate → Retry → Apply
              ↑______________|
```

1. **Generate**: Minion model creates code changes
2. **AST Lint**: Fast syntax check (tree-sitter or Python compile)
3. **LLM Validate**: Second model checks task completion + code preservation
4. **Retry**: On failure, error sent back to minion to fix
5. **Apply**: Only after validation passes

## Configuration

`llm_gc/config/models.yaml`:
```yaml
preset: standard

validation:
  max_retries: 1
  notify_on_fail: true

presets:
  lite:
    minion: { model: qwen2.5-coder:7b, ... }
    validator: same  # use minion
  standard:
    minion: { model: qwen2.5-coder:7b, ... }
    validator: { model: codellama:7b-code, ... }
  expert:
    minion: { model: qwen2.5-coder:14b, ... }
    validator: { model: deepseek-coder:33b, ... }
```

Environment overrides:
```bash
MINIONS_MODEL=qwen2.5-coder:14b
MINIONS_VALIDATOR=codellama:7b
MINIONS_NUM_CTX=65536
MINIONS_PRESET=expert
```

## Key Files

| File | Purpose |
|------|---------|
| `scripts/minions.py` | Unified CLI (polish, sweep, patch, swarm, setup) |
| `scripts/m_polish.py` | Full validation pipeline implementation |
| `llm_gc/config/__init__.py` | Config loading, `get_configs()`, `MinionConfigs` |
| `llm_gc/linter.py` | AST syntax checking |
| `llm_gc/validator.py` | LLM validation (CodeValidator, ValidationResult) |
| `llm_gc/logging.py` | Failure logging to ~/.minions/ |

## Safety Constraints

- **AST Lint**: Catches syntax errors before LLM validation
- **LLM Validation**: Checks task completion and code preservation
- **Retry Loop**: Gives minion chance to fix errors
- **Failure Logging**: Full session data saved for debugging
- **File Sandbox**: Operations restricted to repo root
- **No Shell Exec**: Agents can't run arbitrary commands
