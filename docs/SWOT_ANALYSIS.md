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

| Weakness | Evidence | Root Cause Hypothesis |
|----------|----------|----------------------|
| **Validation failures common** | 6 failures today: "no code block", "validation failed" | Prompt ambiguity or model truncation at context limit |
| **Validator unreliable** | Same file (linter.py) failed multiple times | Non-deterministic output; AST edge cases in complex files |
| **No retry feedback loop** | Failures don't surface actionable fixes to user | Error messages designed for logs, not humans |
| **Skill overlap unclear** | polish vs sweep vs swarm - when to use which? | Skills evolved organically without clear decision tree |
| **File size limit** | <500 lines hard limit, no graceful degradation | Context window constraints; no chunking strategy |
| **Python only** | No TypeScript/Go/Rust support yet | Started with Python; AST tooling is Python-first |

### Opportunities

| Opportunity | Impact |
|-------------|--------|
| **Insights skill** | Claude analyzes failure patterns → improves presets |
| **Better error messages** | "No code block" should explain what went wrong |
| **TypeScript support** | Second most common language for web devs |
| **Chunking for large files** | Split >500 line files, process pieces |
| **Preset auto-upgrade** | Detect when 7b fails often, suggest 14b |

### Differentiator

| Opportunity | Why It's a Moat |
|-------------|-----------------|
| **Community presets** | Users share working model configs → network effects. Hard to replicate if we build the sharing infrastructure first. |

### Threats

| Threat | Likelihood | Mitigation |
|--------|------------|------------|
| **Small models too unreliable** | Medium | Validation catches; users upgrade models |
| **Claude Code skills change** | Low | CLI works standalone |
| **Users lose trust after failures** | Medium | Better error messages, transparent logging |
| **Ollama breaks API** | Low | Abstract client layer exists |
| **Faster competitor** | Medium | Move fast, ship insights |

---

## Key Insight

> **Minions is not failing because of model intelligence. It is failing at the seams between steps.**

Seams are fixable. Trust gaps are fixable. Workflow clarity is fixable.

If the core idea were wrong, the SWOT would look very different.

---

## Priority Backlog

*Informed by [Stanford Minions research](https://arxiv.org/abs/2502.15964)*

### P0: Trust Repairs (Research-Validated)

| Task | Why | Research Backing |
|------|-----|------------------|
| Fix missing code block output | Most common failure mode | — |
| Simplify prompts to single-step | Multi-step confuses local models | 56% improvement from decomposition |
| Chunk large files before processing | Long context degrades performance | 30% drop on long contexts |
| Enforce 7B minimum model size | Small models ineffective | "Models <3B not effective" |

### P1: Architecture Alignment

| Task | Why | Research Backing |
|------|-----|------------------|
| Formalize Decompose → Execute → Aggregate loop | Match proven architecture | Core of MinionS protocol |
| Claude decomposes, minions execute single tasks | Task decomposition is key | 56% improvement |
| Add structured output schemas to prompts | Cleaner parallel processing | MinionS uses Pydantic schemas |
| Make max_retries configurable per task type | Control iteration depth | `max_rounds` parameter |

### P2: Clarity and Learning

| Task | Why |
|------|-----|
| Skill selection guide | "use polish for single file, sweep for directories, swarm for parallel" |
| Retry feedback loop | Surface actionable fixes, not just "failed" |
| Failure classification | Categorize errors to find patterns |

### P3: Capability Expansion

| Task | Why |
|------|-----|
| `/minion-insights` skill | Claude analyzes failure logs |
| Arena for model selection | A/B test models on user's code |
| TypeScript support | Second language, bigger audience |

---

## Kill Signal

> If validation failure rate does not drop below 70% after P0 fixes, reassess the validation approach entirely.

---

*Analysis based on: 8 skills reviewed, 6 session logs, failure patterns from ~/.minions/*
