# Local Task Queue

To let a higher-level assistant (Claude/Codex) delegate multiple subtasks, the repo now includes a lightweight file-backed queue.

## Concepts

- **Task kinds**: `chat` (context discussion) and `patch` (diff generation).
- **Statuses**: pending → running → completed/failed.
- **Storage**: JSON file (default `sessions/task_queue.json`).

## CLI Usage

Queue a chat task:
```bash
python scripts/task_queue.py enqueue-chat \
  "Summarize docs" \
  --repo-root . \
  --read PLAN.md
```

Queue a patch task:
```bash
python scripts/task_queue.py enqueue-patch \
  "Fix logging bug" \
  --repo-root . \
  --read src/log.py:1-160 \
  --target src/log.py
```

List tasks:
```bash
python scripts/task_queue.py list
```

Run the next pending task (calls the orchestrator and updates status):
```bash
python scripts/task_queue.py run-next
```

The queue writes transcripts/diffs as usual and records `result_path` in the task entry so supervisors can pull artifacts.

## Integration Notes

- Claude/Codex can enqueue tasks (possibly multiple at once) and poll `list` or `run-next` depending on desired control.
- Current implementation runs tasks synchronously when `run-next` is called; a future daemon (or job runner) can call this periodically.
- Queue entries include `read_requests`/`targets` so supervisors know what context was used.
