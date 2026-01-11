# Minions

**Local LLM minions for Claude Code** — summon a squad of small local models to discuss, review, and patch your code.

```
        Claude Code (Cloud)
           planning, strategy, final review
─────────────────────────────────────────────
        Minions (Local)
           discussion, patches, grunt work
           private, fast, token-free
```

## What is this?

Minions is a Claude Code plugin that lets you offload coding tasks to local LLMs running via [Ollama](https://ollama.ai). Instead of burning cloud tokens on routine discussions and small fixes, summon your minion squad:

- **Implementer** — proposes solutions and writes code
- **Reviewer** — critiques, finds bugs, asks hard questions

They debate until they reach a conclusion, then report back.

## Why?

| Cloud (Claude) | Local (Minions) |
|----------------|-----------------|
| Expensive tokens | Free (your hardware) |
| Best for strategy & synthesis | Best for grunt work |
| Knows the world | Knows your repo |
| Smart but costly | Cheap but focused |

Use Claude for the hard stuff. Send minions for the rest.

## Installation

### Step 1: Install the Plugin

**Claude Code** (recommended):
```
/plugin marketplace add felixmanojh/minions
```

**OpenSkills** (universal - works with Cursor, Windsurf, Cline, etc.):
```bash
npm i -g openskills
openskills install felixmanojh/minions
openskills sync
```

**Manual**:
```
/plugin add https://github.com/felixmanojh/minions
```

### Step 2: Setup Ollama + Models

After installing the plugin, run the setup skill:

```
/minion-setup
```

Or use the standalone installer (macOS/Linux):

```bash
curl -fsSL https://raw.githubusercontent.com/felixmanojh/minions/main/install.sh | bash
```

<details>
<summary>Windows users: manual Ollama setup</summary>

1. Download Ollama from https://ollama.ai/download/windows
2. Run the installer
3. Open PowerShell and run:
   ```powershell
   ollama serve
   ollama pull qwen2.5-coder:1.5b
   ollama pull deepseek-coder:1.3b
   ```

</details>

### Verify Installation

```bash
python scripts/verify_setup.py
```

Or just ask Claude: "Check my minions setup"

## Usage

Once installed, Claude Code automatically discovers the skills. Just ask:

> "Summon minions to review my auth implementation"

> "Have minions fix the pagination bug in src/paginator.py"

> "Queue up doc tasks for the utils module"

Or invoke directly:

```
/minion-huddle
/minion-fix
/minion-queue
```

### Example: Minion Huddle

```
$ python scripts/m1_chat.py "Review error handling in this function" \
    --read src/auth.py --rounds 2 --json
```

```json
{
  "task": "Review error handling in this function",
  "rounds": 2,
  "summary": "The function catches generic exceptions which masks the root cause.
              Recommend catching specific exceptions (ValueError, KeyError) and
              adding proper logging before re-raising.",
  "transcript_path": "sessions/20250111-143022-m1.json",
  "summary_path": "sessions/20250111-143022-m1-summary.txt"
}
```

### Example: Minion Fix

```
$ python scripts/m3_patch.py "Add type hints to the process function" \
    --target src/worker.py --rounds 3 --json
```

```json
{
  "task": "Add type hints to the process function",
  "patch_path": "sessions/20250111-143500-m3.patch",
  "metadata": {
    "patched_files": ["src/worker.py"]
  }
}
```

Apply the patch:
```bash
patch -p1 < sessions/20250111-143500-m3.patch
```

## Skills

### `/minion-huddle`

Multi-agent discussion. Minions debate a topic and report findings.

```bash
python scripts/m1_chat.py "Review the error handling strategy" \
  --repo-root . \
  --read src/errors.py \
  --rounds 3 \
  --json
```

### `/minion-fix`

Generate a patch. Minions write code, critique it, and produce a unified diff.

```bash
python scripts/m3_patch.py "Fix the race condition in worker.py" \
  --repo-root . \
  --target src/worker.py \
  --rounds 4 \
  --json
```

### `/minion-queue`

Batch tasks. Queue multiple jobs and process them.

```bash
python scripts/task_queue.py enqueue-patch "Add docstrings" --target src/utils.py
python scripts/task_queue.py run-next
```

## Architecture

```
minions/
├── .claude-plugin/          # Plugin metadata
│   └── plugin.json          # name, version, skills, requirements
├── skills/                  # Agent skills (works across platforms)
│   ├── minion-huddle/       # discussion skill
│   ├── minion-fix/          # patch generation skill
│   ├── minion-queue/        # task queue skill
│   └── minion-setup/        # bootstrap/diagnostic skill
├── llm_gc/                  # Python package
│   ├── orchestrator/        # multi-agent chat loops
│   ├── tools/               # file reader, diff generator, repo map
│   ├── parsers/             # extract code blocks from LLM output
│   └── config/              # model configuration
├── scripts/                 # CLI entry points
├── AGENTS.md                # Universal agent discovery
└── sessions/                # transcripts, patches, queue state
```

## Configuration

Edit `llm_gc/config/models.yaml` to change models or add roles:

```yaml
implementer:
  model: qwen2.5-coder:1.5b
  temperature: 0.2
  max_tokens: 512

reviewer:
  model: deepseek-coder:1.3b
  temperature: 0.15
  max_tokens: 400

# Add more roles as needed
bughunter:
  model: codellama:7b-code
  temperature: 0.3
  max_tokens: 600
```

## Requirements

- Python 3.10+
- Ollama running locally
- RAM based on preset:
  - nano: 1GB
  - small: 2GB (default)
  - medium: 8GB
  - large: 16GB+
- Claude Code (for skill integration)

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Ollama: command not found" | Install Ollama: `brew install ollama` or [ollama.ai](https://ollama.ai) |
| "Connection refused" | Start daemon: `ollama serve` |
| "Model not found" | Pull model: `ollama pull qwen2.5-coder:1.5b` |
| Empty or poor responses | Try a larger preset, or add more context with `--read` |
| Patch doesn't apply | File changed since minions saw it — re-run |

## License

MIT

## Contributing

PRs welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Acknowledgments

Inspired by [Aider](https://github.com/paul-gauthier/aider) for the repo mapping approach.
Built on [Ollama](https://ollama.ai) for local model inference.
