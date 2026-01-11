# Contributing to Minions

Thanks for your interest in contributing!

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/minions.git
   cd minions
   ```
3. Set up the development environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. Make sure Ollama is running with required models:
   ```bash
   ollama serve &
   ollama pull qwen2.5-coder:1.5b
   ollama pull deepseek-coder:1.3b
   ```

## Development Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes
3. Test locally:
   ```bash
   python scripts/verify_setup.py
   python scripts/m1_chat.py "Test task" --rounds 2
   ```
4. Commit with a clear message:
   ```bash
   git commit -m "Add feature: description"
   ```
5. Push and open a PR

## Code Style

- Python 3.10+ with type hints
- Use `ruff` for formatting (if available)
- Keep functions focused and small
- Add docstrings to public functions

## Project Structure

```
minions/
├── llm_gc/              # Core Python package
│   ├── orchestrator/    # Multi-agent chat loops
│   ├── tools/           # File reader, diff generator, etc.
│   ├── parsers/         # Extract code from LLM output
│   └── config/          # Model configuration
├── scripts/             # CLI entry points
├── skills/              # Agent skill definitions
└── sessions/            # Runtime artifacts (gitignored)
```

## Adding a New Skill

1. Create `skills/your-skill/SKILL.md`
2. Add frontmatter with name, description, allowed-tools
3. Write usage instructions in the body
4. Add the skill path to `.claude-plugin/plugin.json`
5. Update AGENTS.md with trigger phrases

## Questions?

Open an issue or start a discussion.
