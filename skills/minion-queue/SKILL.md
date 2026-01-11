---
name: minion-queue
description: >
  Batch mechanical tasks for local minions. Good for: adding docstrings to multiple files,
  fixing formatting across a module, bulk renaming, repetitive boilerplate. NOT for: tasks
  requiring judgment or complex reasoning. Queue simple, independent tasks that minions
  can handle without deep understanding.
allowed-tools: Bash, Read
---

# Minion Queue

Dispatch multiple tasks to your minion squad. Queue them up, let minions work through them, and collect results later. Perfect for batching small fixes or reviews.

## Task Routing

Since queued tasks run independently, choose a preset that fits the **simplest task** in the batch:

| Batch Type | Preset | Examples |
|------------|--------|----------|
| Trivial batch | `nano` | Rename across files, fix formatting |
| Simple batch | `small` | Add docstrings to each file, type hints |
| Mixed batch | `small` | Default safe choice for varied tasks |

**Note:** Don't queue complex tasks. If any task in the batch needs reasoning, handle it directly with Claude instead.

## When to use

- Multiple small, independent tasks to delegate
- You want to queue work and check results later
- Batching doc fixes, lint cleanups, or minor refactors
- Running minions on a list of issues

## Prerequisites

Ensure Ollama is running:

```bash
ollama serve
```

## Commands

### Queue a discussion task

```bash
python scripts/task_queue.py enqueue-chat \
  "Review error handling in the auth module" \
  --repo-root . \
  --read src/auth.py \
  --rounds 3
```

### Queue a patch task

```bash
python scripts/task_queue.py enqueue-patch \
  "Add docstrings to all public functions" \
  --repo-root . \
  --read src/utils.py \
  --target src/utils.py \
  --rounds 4
```

### List queued tasks

```bash
python scripts/task_queue.py list
```

Output:

```json
[
  {
    "id": "abc-123",
    "kind": "chat",
    "description": "Review error handling...",
    "status": "pending",
    "created_at": "2025-01-11T12:00:00"
  },
  {
    "id": "def-456",
    "kind": "patch",
    "description": "Add docstrings...",
    "status": "completed",
    "result_path": "sessions/20250111-120500-m3.patch"
  }
]
```

### Run next pending task

```bash
python scripts/task_queue.py run-next
```

This blocks until the task completes, then returns the task JSON with results.

### Run all tasks in parallel

```bash
python scripts/task_queue.py run-parallel --workers 3
```

Runs all pending tasks concurrently (default: 3 workers). Great for batch operations.

### Clear completed tasks

```bash
python scripts/task_queue.py clear-completed
```

Removes completed and failed tasks from the queue.

## Task statuses

| Status | Meaning |
|--------|---------|
| `pending` | Queued, waiting to run |
| `running` | Currently executing |
| `completed` | Finished successfully |
| `failed` | Error occurred (see `error` field) |

## Integration pattern

1. Break a larger task into subtasks suitable for minions
2. Enqueue each subtask (chat or patch)
3. Run `run-next` repeatedly (or poll `list`)
4. Collect results from `result_path` fields
5. Synthesize minion outputs into final answer

### Example: batch documentation

```bash
# Queue doc tasks for each module
for file in src/*.py; do
  python scripts/task_queue.py enqueue-patch \
    "Add docstrings to $file" \
    --repo-root . \
    --read "$file" \
    --target "$file"
done

# Process queue
while python scripts/task_queue.py run-next; do
  echo "Task completed"
done
```

## Queue file location

Tasks are stored in `sessions/task_queue.json`. You can:

- Inspect it directly for debugging
- Back it up before experiments
- Clear it by deleting the file

Custom location:

```bash
python scripts/task_queue.py --queue-file my-queue.json list
```

## Limitations

- Each task is independent — no shared state between tasks
- Queue is file-based — not suitable for distributed systems
- No automatic retry on failure
- Parallel execution limited by Ollama's throughput

## Troubleshooting

**"No pending tasks"**: Queue is empty or all tasks completed. Check `list`.

**Task stuck in "running"**: Process crashed mid-task. Manually edit `task_queue.json` to reset status to `pending`.

**Want parallel execution**: Run multiple terminal sessions, each calling `run-next` (they'll grab different tasks due to file locking — but this is experimental).
