---
name: minion-huddle
description: >
  Offload simple code discussions to local minions (1-3B models). Good for: checking code
  style, spotting obvious bugs, reviewing naming conventions, validating simple logic.
  NOT for: architecture decisions, security analysis, complex reasoning, or subtle bugs.
  Use when the task is mechanical and you want a quick sanity check without burning cloud tokens.
allowed-tools: Bash, Read, Glob, Grep
---

# Minion Huddle

Summon your local minion squad (Implementer + Reviewer) to discuss a task. They debate, critique each other, and produce a summary — all running locally via Ollama.

## Should I Use Minions? (Decision Guide)

Before delegating, assess if minions can handle it:

| Task Type | Use Minions? | Why |
|-----------|--------------|-----|
| Code style, naming | ✓ Yes | Pattern matching, no reasoning |
| Obvious bugs (typos, off-by-one) | ✓ Yes | Mechanical fixes |
| Simple logic review | ✓ Maybe | Depends on complexity |
| Multi-file refactor | ✗ No | Needs broader understanding |
| Security analysis | ✗ No | Needs real reasoning |
| Architecture decisions | ✗ No | Needs intelligence |
| Subtle bugs | ✗ No | Needs deep understanding |

**Quick test:** Can a junior dev do this with clear instructions? → Minions can try.

## When to use

- You want a second opinion before writing code
- The task is scoped and doesn't need cloud-level reasoning
- You want to save tokens by offloading discussion locally
- You need multiple perspectives on a refactor or bug fix

## Prerequisites

Ensure Ollama is running with models pulled:

```bash
ollama serve  # must be running
ollama list   # verify models exist
```

Required models (configured in `llm_gc/config/models.yaml`):
- `qwen2.5-coder:1.5b` (Implementer)
- `deepseek-coder:1.3b` (Reviewer)

## Usage

Basic huddle (uses user's configured preset):

```bash
python scripts/m1_chat.py "Check variable naming conventions" \
  --repo-root . \
  --rounds 3 \
  --json
```

With file context (minions see this code):

```bash
python scripts/m1_chat.py "Review this function for obvious issues" \
  --repo-root . \
  --read src/auth.py \
  --rounds 3 \
  --json
```

Multiple context files:

```bash
python scripts/m1_chat.py "Are these two modules consistent in style?" \
  --repo-root . \
  --read llm_gc/orchestrator/base.py \
  --read llm_gc/config/__init__.py \
  --rounds 3 \
  --json
```

## Output

The command returns JSON:

```json
{
  "task": "Review the authentication flow",
  "rounds": 3,
  "summary": "Reviewer's final assessment...",
  "transcript_path": "sessions/20250111-120000-m2.json",
  "summary_path": "sessions/20250111-120000-m2-summary.txt"
}
```

- **summary**: The final message from the conversation
- **transcript_path**: Full debate transcript (inspect for details)
- **summary_path**: Repo context that was fed to minions

## Integration pattern

1. Detect tasks suitable for local discussion (scoped, doesn't need latest knowledge)
2. Prepare context reads (relevant files the minions should see)
3. Invoke the huddle command with `--json`
4. Parse the summary and surface it to the user
5. Use the insights to inform your next action

## Limitations

- Small models (1-3B) have limited reasoning depth
- Best for focused tasks, not open-ended architecture discussions
- No internet access — minions only see repo context you provide
- Slower than cloud (10-30s per round depending on hardware)

## Troubleshooting

**"Connection refused"**: Ollama isn't running. Start it with `ollama serve`.

**"Model not found"**: Pull the model first: `ollama pull qwen2.5-coder:1.5b`

**Empty or poor responses**: Provide more context with `--read` flags.
