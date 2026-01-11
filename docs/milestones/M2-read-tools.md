# Milestone M2 – Read-Only Tools & Repo Summaries

Goal: allow agents to pull repo context using safe read-only tools: file reader (scoped to repo), tree summarizer, and task-specific repo summary injection into prompts. Implementer/Reviewer continue to chat with guardrails; no write/diff yet.

## 1. New components

- `tools/file_reader.py`: sanitized file read helper with line range support, ensures only files under repo root are accessible.
- `tools/repo_summary.py`: generates a lightweight summary (e.g., root README + `tree -L 2` equivalent) once per session.
- `agents/context.py`: utilities to inject retrieved snippets into prompts while respecting token budgets.

## 2. Config additions

Extend `config/models.yaml` or add a new `config/settings.yaml` with:
```yaml
repo_root: /path/to/repo
max_read_bytes: 8192
summary_max_chars: 4000
```
These parameters keep reads bounded.

## 3. File read tool behavior

- Accepts `{ "path": "relative/path", "start": 1, "end": 80 }` (line indices optional).
- Validates the resolved path stays inside `repo_root`.
- Limits bytes read using `max_read_bytes`, truncates with a notice when exceeded.
- Returns fenced code block tagged with the file extension to help models parse content.

Implementation sketch (`tools/file_reader.py`):
```python
from pathlib import Path

class FileReader:
    def __init__(self, root: Path, max_bytes: int = 8192):
        self.root = root.resolve()
        self.max_bytes = max_bytes

    def read(self, relative_path: str, start: int | None = None, end: int | None = None) -> str:
        path = (self.root / relative_path).resolve()
        if not str(path).startswith(str(self.root)):
            raise ValueError("Path escapes repo root")
        text = path.read_text()
        lines = text.splitlines()
        segment = lines[(start or 1) - 1 : end]
        snippet = "\n".join(segment)
        snippet = snippet[: self.max_bytes]
        lang = path.suffix.removeprefix('.') or 'text'
        return f"```{lang}\n{snippet}\n```"
```

## 4. Repo summary helper

- Run once per chat session (cache results on disk to avoid repeated work).
- Combine:
  - README.md first ~400 words
  - `git status -sb` (without network; use `subprocess.run`)
  - Directory tree depth 2 (via Python walk)
- Store summary in `sessions/<session_id>-summary.txt` for transparency.

## 5. Prompt integration

Modify `ChatOrchestrator`:
- On initialization, compute repo summary text and pass it into each prompt (prepend after system message).
- Add ability for agents to request file reads mid conversation: interpret responses containing a structured command, or simpler: run a fixed list of reads before first round (M2-lite). For MVP: before chat starts, automatically read `PLAN.md` and `docs/*` summary and include in context.
- Keep conversation history truncated to avoid token bloat.

## 6. CLI updates

Add flags to `scripts/m1_chat.py` (or rename to `m2_chat.py`):
- `--repo-root PATH`
- `--read PATH:START-END` (repeatable) to pull specific files before chat.
- Print "Context sources:" header showing which files were added.

## 7. Acceptance criteria

- [ ] Running `scripts/m1_chat.py --repo-root . --read PLAN.md` shows the file snippet inside Implementer’s first prompt (inspect transcript JSON).
- [ ] Repo summary file saved per session under `sessions/`.
- [ ] File reader rejects `../` escapes with clear error.
- [ ] Entire system still read-only (no writes besides transcripts/summary).

With read tools in place, the agents can ground themselves for actual repo tasks, paving the way for M3 diff generation.
