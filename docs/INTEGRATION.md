# Integrating Local Multi LLM with External Assistants

This guide shows how to expose the local orchestrator as a reusable skill for agents such as Claude Code or Codex. The integration surface is intentionally small so tool-capable assistants can call into the repo without manual intervention.

## 1. Command-line Tool Contract

Use `scripts/m1_chat.py` as the primary entry point.

```bash
python scripts/m1_chat.py \
  "Refactor the HTTP client" \
  --repo-root /path/to/repo \
  --read PLAN.md \
  --read src/client.py:1-80 \
  --rounds 3 \
  --json
```

Key behaviors:

- Exits with non-zero status on failure (missing models, invalid paths, etc.).
- `--json` flag emits machine-readable output:
  ```json
  {
    "task": "Refactor the HTTP client",
    "rounds": 3,
    "repo_root": "/path/to/repo",
    "read_requests": ["PLAN.md", "src/client.py:1-80"],
    "summary": "Reviewer feedback...",
    "transcript_path": "sessions/20240214-120102-m2.json",
    "summary_path": "sessions/20240214-120102-m2-summary.txt",
    "metadata": {
      "session_id": "20240214-120102-m2",
      "context_files": [...],
      "repo_summary_sources": {...}
    }
  }
  ```
- `metadata.session_id` can be used to correlate transcript and summary artifacts.

Claude/Codex can treat this command as a tool invocation by providing the task text, repo root, and optional file snippets.

### Patch workflow (M3)

To request a diff:

```bash
python scripts/m3_patch.py \\
  "Fix the logging bug" \\
  --repo-root /path/to/repo \\
  --read src/log.py:1-160 \\
  --target src/log.py \\
  --json
```

Output JSON mirrors the chat command but adds `patch_path` and `metadata.patched_files`. The generated unified diff lives under `sessions/<id>.patch`.

## 2. Python Skill API

For assistants that can import Python modules directly, use `llm_gc.skill.run_chat_skill`:

```python
from pathlib import Path
from llm_gc.skill import ChatSkillRequest, run_chat_skill, parse_read_requests

request = ChatSkillRequest(
    task="Document the CLI layout",
    rounds=3,
    repo_root=Path("/path/to/repo"),
    read_requests=parse_read_requests(["PLAN.md", "docs/README.md:1-120"]),
)
result = run_chat_skill(request)
print(result.summary)
print(result.transcript_path)
```

The result object contains: `summary`, `transcript_path`, `summary_path`, and `metadata` (same as CLI JSON). This is ideal for tool APIs where Claude/Codex can call Python functions.

## 3. Suggested Tool Definition (Claude/Codex)

Describe the capability as:

> **LocalChatTool**
> - **Input**: `task` (string), optional `read_files` (array of `PATH[:start-end]`), optional `rounds`.
> - **Output**: structured JSON with `summary`, `transcript_path`, `summary_path`, and metadata.
> - **Behavior**: runs local Implementer/Reviewer chat with repo context. No code modifications are applied.

For the patch workflow, describe it as `LocalPatchTool` with additional outputs `patch_path` and `patched_files`.

Assistants should:

1. Detect small, repo-scoped questions suitable for local models.
2. Prepare context reads (e.g., `PLAN.md`, target files) and call the tool.
3. Parse JSON output, surface the summary/diff to the user, and reference the transcript if needed.
4. Fall back to native reasoning if the tool errors or lacks context.

## 4. Testing the Integration

- Use `--json` output in automated tests to verify the command returns valid JSON and creates transcripts.
- Add a sanity test script (future work) that mocks Ollama responses to confirm tool invocation without GPU requirements.
- Ensure `ollama serve` is running before invoking the tool.

## 5. Optional Enhancements for Better Context

- **RepoMap** (`llm_gc/tools/repomap.py`) leverages `grep-ast`/tree-sitter to extract class/function signatures. Consider generating this map once per session and feeding it into the context snippets so local models see available symbols.
- **Fuzzy patching** (`llm_gc/tools/fuzzy_patch.py`) uses `diff-match-patch` to tolerate minor drift when applying diffs. Integrate during M4 when implementing `llm-gc apply`.

## 6. Task Queue Delegation

Use `scripts/task_queue.py` (documented in `docs/TASK_QUEUE.md`) to queue multiple chat/patch tasks. Claude/Codex can enqueue subtasks, run them sequentially (`run-next`), and inspect queue JSON to retrieve summaries/diff paths.

## 7. Claude Tool Cards

Define the tools Claude Code should register when this repo is mounted as an extension.

| Tool name | Invocation | Inputs | Outputs | Failure handling |
| --- | --- | --- | --- | --- |
| `LocalChatTool` | `python scripts/m1_chat.py ... --json` | `task` (str), `repo_root` (path), `read_files` (array `PATH[:start-end]`), `rounds` (int) | JSON matching the sample in §1 (`summary`, `transcript_path`, `metadata`) | Non-zero exit → Claude reports failure and optionally retries with different context |
| `LocalPatchTool` | `python scripts/m3_patch.py ... --json` | `task`, `repo_root`, optional `read_files`, optional `target_files`, `rounds` | JSON including `summary`, `transcript_path`, `summary_path`, `patch_path`, `metadata.patched_files` | Same as above; if patch empty, Claude escalates to manual coding |
| `LocalTaskQueue` | `python scripts/task_queue.py enqueue-...` / `run-next` | enqueue: same args as tools above; run: none | Enqueue returns `{queued, kind}`; run returns task JSON with status/result paths | If `run-next` hits an error, status becomes `failed` and `error` field explains why |

Claude should invoke these tools only when tasks are scoped to the repo and safe for local execution, and it should surface the resulting artifacts (diffs/transcripts) back to the user or apply them after review.
