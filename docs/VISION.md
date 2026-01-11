# Vision: Claude Code + Local Nanites

This project builds a layered assistant stack where Claude Code orchestrates from the cloud and local LLM “nanites” execute concrete repo tasks. The pyramid has three tiers:

```
        Cloud (Claude Code: Opus/Sonnet)
           - planning, decomposition, final review
           - expensive tokens, highest IQ
----------------------------------------------
  Local Mid-tier (7–13B models)
           - Reviewer, Bug Hunter roles
           - richer reasoning with more RAM/VRAM
  Local Nanites (1–3B models)
           - file summaries, lint/doc fixes, quick diffs
           - super cheap, always-on helpers
```

The red boundary separates cloud vs. local compute and high vs. lower capability. Claude stays above the line directing strategy; the local tiers work below it, keeping code private and saving tokens.

## Path to a Claude Code Skill/Plugin

| Step | Milestone link | Deliverable |
| --- | --- | --- |
| 1. Foundations | M0–M3 | Local models via Ollama, multi-agent chat, repo context, patch diffing |
| 2. Tool contract | M2–M3 | CLI/API with JSON outputs (`scripts/m1_chat.py`, `scripts/m3_patch.py`, `llm_gc.skill`) → see `docs/INTEGRATION.md` |
| 3. Task queue | M3+ | File-backed scheduler (`scripts/task_queue.py`, `docs/TASK_QUEUE.md`) so Claude can enqueue multiple nanite tasks |
| 4. Claude skill definition | upcoming | Register tools (`LocalChatTool`, `LocalPatchTool`, `LocalTaskQueue`) inside Claude Code with clear inputs/outputs/failure modes |
| 5. Future robustness | M4–M5 | Guarded apply/test hooks, fuzzy patching, SEARCH/REPLACE fallback (`docs/SEARCH_REPLACE.md`) |

## Token-Savings Rationale

- Routine subtasks (summaries, doc fixes) cost ~1k Claude tokens each. Offloading 20/day to nanites saves ~20k tokens.
- Multi-step refactors: instead of Claude spending 5–10k tokens implementing, nanites produce diffs while Claude only reviews (~500 tokens).
- Local verification: targeted reviews/tests run offline, so Claude only consumes tokens to interpret results, not to perform the work.

## Next Steps Checklist

1. Write Claude tool cards referencing the CLI/API contracts (inputs: task, repo_root, read files; outputs: summary, transcript/diff paths, metadata).
2. Integrate the task queue into Claude’s workflow (enqueue multiple subtasks, poll `run-next`).
3. Add RepoMap text or key snippets into prompts (already available) and evaluate benefit; iterate on prompt limits.
4. Plan M4 work: apply commands using `fuzzy_patch`, guarded test runner approvals, and SEARCH/REPLACE fallback.

Outcome: Claude remains the strategic brain in the cloud, while the local multi-LLM stack serves as an always-available skill/plugin for fast, private, and cheap execution of small coding tasks.
