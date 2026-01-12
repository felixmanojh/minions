# Minions: SWOT Analysis

## 2026-01-12

### Strengths

| Strength | Evidence |
|----------|----------|
| **Clear skill coverage** | 8 skills covering full workflow: polish, sweep, patch, swarm, apply, models, setup, metrics |
| **Well-documented skills** | Each SKILL.md has clear triggers, examples, and output formats |
| **Validation pipeline exists** | Generate → Validate → Retry prevents bad code from applying |
| **Session logging** | All operations logged to `~/.minions/` for debugging |
| **Proactive triggers** | Skills marked "PROACTIVELY USE" guide Claude to delegate |
| **JSON output** | `--json` flag enables structured responses for Claude |

### Weaknesses

| Weakness | Evidence |
|----------|----------|
| **Validation failures common** | 6 failures today: "no code block", "validation failed" |
| **Validator unreliable** | Same file (linter.py) failed multiple times |
| **No retry feedback loop** | Failures don't surface actionable fixes to user |
| **Skill overlap unclear** | polish vs sweep vs swarm - when to use which? |
| **File size limit** | <500 lines hard limit, no graceful degradation |
| **Python only** | No TypeScript/Go/Rust support yet |

### Opportunities

| Opportunity | Impact |
|-------------|--------|
| **Insights skill** | Claude analyzes failure patterns → improves presets |
| **Better error messages** | "No code block" should explain what went wrong |
| **TypeScript support** | Second most common language for web devs |
| **Chunking for large files** | Split >500 line files, process pieces |
| **Preset auto-upgrade** | Detect when 7b fails often, suggest 14b |
| **Community presets** | Users share working model configs |

### Threats

| Threat | Likelihood | Mitigation |
|--------|------------|------------|
| **Small models too unreliable** | Medium | Validation catches; users upgrade models |
| **Claude Code skills change** | Low | CLI works standalone |
| **Users lose trust after failures** | Medium | Better error messages, transparent logging |
| **Ollama breaks API** | Low | Abstract client layer exists |
| **Faster competitor** | Medium | Move fast, ship insights |

### Priority Actions

1. **P0:** Fix "no code block" errors - investigate why minion output lacks code
2. **P1:** Better validation error messages - what specifically failed?
3. **P1:** Add skill selection guide - "use polish for single file, sweep for directories, swarm for parallel"
4. **P2:** `/minion-insights` skill - surface patterns from failure logs

---

*Analysis based on: 8 skills reviewed, 6 session logs, failure patterns from ~/.minions/*
