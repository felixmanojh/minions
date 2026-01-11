# Changelog

All notable changes to Minions will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Pydantic Minion types** (`llm_gc/types.py`) - Type-safe agent definitions with `Minion`, `MinionResult`, `CodeReview`, `PatchResult`
- **Disk cache** (`llm_gc/cache.py`) - Persistent caching with mtime invalidation for fast re-runs
- **PageRank file ranking** (`llm_gc/repomap.py`) - Import graph analysis to find most relevant context files
- **Fallback patch strategies** (`llm_gc/patcher.py`) - Robust patching: exact → fuzzy → unified diff → git apply
- **Agent handoff pattern** (`llm_gc/handoff.py`) - Automatic Reviewer → Patcher transitions
- **M4: Autonomous test runner and auto-apply**:
  - `MinionTestRunner` (`llm_gc/tools/test_runner.py`) - Auto-detect project type (Python, Node, Rust, Go) and run tests
  - `PatchApplier` (`llm_gc/tools/patch_apply.py`) - Auto-apply patches with backup and rollback
  - `SafetyGuard` (`llm_gc/safety.py`) - Denylist dangerous commands, path sandboxing, secret detection
- **Async refactor** - Swarm and orchestrators now use `asyncio` for parallel execution

### Changed
- Dependencies: added `diskcache`, `networkx`, `numpy`, `scipy`
- Swarm uses `asyncio.gather()` instead of ProcessPoolExecutor
- Test count: 120 tests

## [0.1.0] - 2025-01-11

### Added
- Initial release of Minions plugin for Claude Code
- **Multi-agent orchestration** with three specialized roles:
  - Implementer (Qwen2.5-Coder) - code generation
  - Reviewer (DeepSeek-Coder) - bug detection
  - Patcher (StarCoder2) - surgical edits with FIM
- **Skills**:
  - `/minion-huddle` - multi-agent discussion and debate
  - `/minion-fix` - patch generation with unified diffs
  - `/minion-swarm` - parallel task execution
  - `/minion-queue` - batch task queuing
  - `/minion-setup` - bootstrap and diagnostics
- **Smart routing** - keyword-based role inference with diff marker detection
- **Model presets** - lite (5GB), medium (13GB), large (35GB)
- **Swarm mode** with:
  - Parallel execution via ProcessPoolExecutor
  - Auto-retry with prompt simplification
  - tqdm progress bar
- **Banana counter** - gamification for task completion tracking
- **Ollama health checks** with exponential backoff retry
- **Environment overrides** for model selection (MINIONS_*_MODEL)
- Comprehensive test suite (67 tests)
- GitHub Actions CI with multi-Python testing
- Ruff linting configuration

### Infrastructure
- One-line install script for macOS/Linux
- Windows PowerShell instructions
- pyproject.toml with proper packaging
- MIT License

[Unreleased]: https://github.com/felixmanojh/minions/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/felixmanojh/minions/releases/tag/v0.1.0
