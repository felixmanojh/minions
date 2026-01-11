# Milestone M1 – Minimal Multi-Agent Orchestrator (No Tools)

Goal: orchestrate a shared chat between at least two local coding models (Implementer & Reviewer) with deterministic turn scheduling and guardrails. Models must communicate only through the orchestrator; no repo/file tools yet.

## 1. Python environment & deps

1. Create a dedicated virtualenv (or use `uv`/`poetry`). Example with venv:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```
2. Install dependencies:
   ```bash
   pip install "pyautogen>=0.3" httpx pydantic[yaml] rich
   ```
   *AutoGen* provides the multi-agent framework, `httpx` will call the Ollama HTTP API, `pydantic[yaml]` loads config files, and `rich` helps display transcripts.

## 2. Repository scaffolding

```
llm_gc/
  __init__.py
  config/
    __init__.py
    models.yaml
  orchestrator/
    __init__.py
    base.py
    m1_chat.py
```

* `config/models.yaml` maps logical role names to Ollama models (from M0).
* `orchestrator/base.py` holds shared utilities (HTTP client wrapper, role metadata).
* `orchestrator/m1_chat.py` wires agents and runs the chat loop.

## 3. Model config schema

`config/models.yaml` example:
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

Parsing helper (pseudo-code for `llm_gc/config/__init__.py`):
```python
from pathlib import Path
from pydantic import BaseModel
import yaml

class ModelConfig(BaseModel):
    model: str
    temperature: float = 0.2
    max_tokens: int = 512

def load_models(path: Path) -> dict[str, ModelConfig]:
    data = yaml.safe_load(path.read_text())
    return {role: ModelConfig(**cfg) for role, cfg in data.items()}
```

## 4. Ollama client helper

`llm_gc/orchestrator/base.py` should expose a small callable for AutoGen:
```python
import httpx

class OllamaCompletion:
    def __init__(self, config):
        self.config = config
        self.client = httpx.Client(base_url="http://127.0.0.1:11434")

    def __call__(self, prompt: str) -> str:
        resp = self.client.post("/api/generate", json={
            "model": self.config.model,
            "prompt": prompt,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        })
        resp.raise_for_status()
        chunks = resp.json()
        return chunks.get("response", "")
```
Later milestones can add streaming, timeouts, retries, etc.

## 5. Minimal chat loop (Implementer ↔ Reviewer)

`llm_gc/orchestrator/m1_chat.py` responsibilities:

1. Load configs (`load_models`).
2. Create two AutoGen `AssistantAgent`s:
   ```python
   implementer = AssistantAgent(
       name="Implementer",
       system_message="Write a concise plan to solve the task.",
       llm_config={"seed": 42, "config_list": [{"custom_llm_provider": "ollama", "model_client_cls": OllamaCompletion, "config_name": "implementer"}]}
   )
   reviewer = AssistantAgent(
       name="Reviewer",
       system_message="Critique the implementer plan and highlight risks.",
       llm_config=...
   )
   ```
   Implement `OllamaCompletion` as `model_client_cls` per AutoGen’s custom LLM interface.
3. Use `UserProxyAgent` as conversation driver. Provide the user task and limit to ~3 rounds:
   ```python
   user = UserProxyAgent("User", human_input_mode="NEVER")
   user.initiate_chat(
       implementer,
       message=f"Task: {user_task}. Respond in <=200 tokens.",
       max_turns=5,
       summary_method="last_msg",
       select_speaker=lambda x: reviewer if x is implementer else implementer
   )
   ```
   After each implementer reply, forward it to reviewer, then back, until `max_turns` or stop token.
4. Capture transcript to `sessions/<timestamp>-m1.json` (store role, content, tokens, latency).

## 6. Guardrails for M1

* Enforce `max_turns` (e.g., 4 total messages after prompt).
* Limit per-message tokens (set via config).
* Deny tool usage entirely (agents just chat).
* Add `timeout` and fail-open logging if Ollama doesn’t respond within 30s.

## 7. CLI entry point (temporary)

Create `scripts/m1_chat.py`:
```python
#!/usr/bin/env python3
from llm_gc.orchestrator.m1_chat import run_chat
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("task", help="Natural language request")
parser.add_argument("--rounds", type=int, default=3)
args = parser.parse_args()

summary = run_chat(task=args.task, rounds=args.rounds)
print("\n=== Final Summary ===\n")
print(summary)
```

Usage:
```bash
source .venv/bin/activate
python scripts/m1_chat.py "Refactor the logging module" --rounds 3
```
Outputs transcript lines prefixed with role names and writes JSON transcript file.

## 8. Acceptance checklist

- [ ] `scripts/m1_chat.py "stub task"` prints both Implementer and Reviewer turns.
- [ ] JSON transcript stored under `sessions/` with timestamp.
- [ ] Each turn identifies model name + latency + tokens.
- [ ] Hard stop after configured rounds.
- [ ] No filesystem writes except transcript.

Complete these and M1 is done; next milestone (M2) will add read-only repo tools.
