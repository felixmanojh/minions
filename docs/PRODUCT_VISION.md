# Minions: Product Vision

## One-Liner

**Delegate mechanical code work to local models. Save cloud intelligence for real reasoning.**

---

## The Real Problem

It's not about tokens. It's about **wasted intelligence**.

Claude Code is powerful. But developers burn that power on mechanical tasks:
- Adding docstrings to 50 files
- Adding type hints across a module
- Formatting, comments, headers

These tasks don't need Claude's intelligence. They need a worker who follows instructions.

**The cost isn't money. It's misallocated reasoning.**

---

## The Vision

### The Intelligence Pyramid

```
                              ▲
                              │ Intelligence
                              │ Cost
                        ┌─────┴─────┐
                        │ FRONTIER  │  ← Claude Code lives here
                        │  Opus/GPT-4│    (Reasoning, strategy)
                        ├───────────┤
                        │  MID-TIER │
                        │ Sonnet/4o │
                        ├───────────┤
                        │ EFFICIENT │
                        │Haiku/Mini │
                        ├───────────┤
                        │   SMALL   │  ← Minions live here
                        │  7b-14b   │    (Mechanical execution)
                        ├───────────┤
                        │   TINY    │
                        │  1.5b-3b  │
                        └─────┬─────┘
                              │
            ┌─────────────────┼─────────────────┐
            │                 │                 │
         LOCAL               │              CLOUD
       (Private)             │            (Cheap)
            │                 │                 │
      ┌─────┴─────┐          │          ┌─────┴─────┐
      │  Ollama   │          │          │OpenRouter │
      │ LM Studio │          │          │ 4o-mini   │
      │ llama.cpp │          │          │  Groq     │
      └───────────┘          │          └───────────┘
                              │
                    Both are valid.
                    Pick based on needs.
```

**The insight:** The pyramid has two halves — local and cloud. Minions operate at the bottom of the pyramid on either side. The top is reserved for reasoning.

Like Gru and his Minions: Gru handles the master plan, Minions handle the grunt work.

**Claude always classifies the task. Minions never self-select work.**

---

## A Concrete Example

**Before:**
```
42 Python files missing docstrings
Estimated Claude time: 15-20 minutes of back-and-forth
```

**Command:**
```bash
/minion-sweep src/ --task docstrings --apply
```

**Result:**
```
✓ 39 files: docstrings added and validated
✗ 3 files: rejected (logged for review)
Time: 4 minutes (local, parallel)
Claude time saved: ~18 minutes
```

---

## Target Users

1. **Claude Code power users** — developers who use Claude Code daily and want to preserve intelligence for hard problems
2. **Privacy-conscious teams** — want code processing to stay local (Ollama)
3. **Cost-conscious developers** — want cheap execution via OpenRouter/GPT-4o-mini
4. **High-velocity teams** — need to maintain large codebases without burning senior-engineer time on junior-engineer work

---

## Core Principles

### 1. Know Your Limits
Local models are for mechanical work, not reasoning — regardless of size.
- Mechanical tasks only (no reasoning, no logic changes)
- File size depends on model context window
- Simple, repetitive operations

**Model choice is yours:**
| Hardware | Recommended | Context |
|----------|-------------|---------|
| 8GB RAM | 7b | 32K |
| 16GB RAM | 14b | 64K |
| 32GB+ RAM | 32b/70b | 128K |

Bigger models = better accuracy, but the task type stays mechanical.

### 2. Validate Before Apply
Minions make mistakes. Every change goes through:
```
Generate → AST Lint → LLM Validate → Apply
```
If validation fails, retry with error feedback. If still fails, don't apply.

### 3. Cloud for Thinking, Local for Doing
- **Cloud (Claude):** Classification, analysis, decisions, complex reasoning
- **Local (Minions):** Execution of mechanical tasks

### 4. Transparent Failures
Log everything. When minions fail:
- Save the session (original, generated, error)
- Let Claude Code analyze patterns
- Surface insights to improve over time

---

## The Product

### Skills (Claude Code Integration)

**Current:**

| Skill | Purpose |
|-------|---------|
| `/minion-polish` | Auto-apply docstrings, types to files |
| `/minion-sweep` | Scan codebase, batch-fix missing docs |
| `/minion-swarm` | Same change across multiple files |
| `/minion-patch` | Generate patch for manual review |
| `/minion-setup` | Verify Ollama and models |
| `/minion-metrics` | View session stats |

**Planned (Phase 2):**

| Skill | Purpose |
|-------|---------|
| `/minion-insights` | Claude analyzes minion performance |

### CLI (Standalone)

```bash
minions polish src/foo.py --task docstrings   # Auto-apply polish
minions sweep src/ --task all --apply          # Batch fix codebase
minions patch "Add header" --target src/foo.py # Generate patch
minions swarm "Add header" src/*.py            # Parallel patches
minions setup                                   # Verify Ollama/models
minions metrics                                 # View session stats
```

### Presets

**Local (Ollama):**

| Preset | Minion | Validator | Hardware | Use Case |
|--------|--------|-----------|----------|----------|
| lite | 7b | same | 8GB RAM | Fast, minimal hardware |
| standard | 7b | 7b | 8GB RAM | Balanced safety |
| expert | 14b | 14b | 16GB RAM | Better accuracy |

**Cloud (Planned):**

| Preset | Minion | Validator | Cost | Use Case |
|--------|--------|-----------|------|----------|
| openrouter | free tier | same | $0 | Zero cost, variable availability |
| gpt-mini | gpt-4o-mini | same | ~$0.15/1M | No GPU required |
| haiku | claude-3-haiku | same | ~$0.25/1M | Anthropic ecosystem |

Users can override any model via `MINIONS_MODEL` env var or `models.yaml`.

---

## Success Metrics

| Metric | What It Measures |
|--------|------------------|
| **Claude minutes saved per session** | Time not spent on mechanical work |
| **Files safely modified per session** | Throughput of validated changes |
| **Validation success rate** | % of minion output that passes |
| **User trust score** | % of changes applied without manual review |

---

## Roadmap

### Phase 1: Foundation (Done)
- [x] Generate → Validate → Retry pipeline
- [x] Polish, Sweep, Patch, Swarm commands (CLI)
- [x] Session logging to `~/.minions/`
- [x] Claude Code skills (polish, sweep, swarm, patch, setup, metrics)

### Phase 2: Insights
- [ ] `/minion-insights` skill — Claude analyzes logs
- [ ] Success/failure pattern detection
- [ ] Preset upgrade suggestions

### Phase 3: Learning Loop
- [ ] Export successful pairs for fine-tuning
- [ ] Custom model creation (`ollama create minion-tuned`)
- [ ] Per-codebase adaptation

### Phase 4: Cloud Backends
- [ ] OpenRouter integration (free tiers)
- [ ] OpenAI API (GPT-4o-mini)
- [ ] Anthropic API (Haiku)
- [ ] Backend abstraction layer

### Phase 5: Expansion
- [ ] More task types (tests, refactoring patterns)
- [ ] Multi-language support
- [ ] Team sharing of tuned models

---

## What Minions Will Never Do

- **Classify work as mechanical** — Claude decides what to delegate
- **Reason about code logic** — that's Claude's job
- **Make architectural decisions** — that's Claude's job
- **Handle security-sensitive code** — local models shouldn't touch auth, crypto, etc.
- **Replace Claude Code** — they're the workforce, not the brain

---

## The Strategic Insight

This product is not about saving tokens.

**It's about preserving intelligence for leverage.**

We're proposing a future where:
- Cloud models act like senior engineers
- Local models act like reliable juniors
- The human stays in control

The division of labor mirrors how effective teams already work.

---

## The Pitch

> "Stop wasting Claude's intelligence on docstrings. Delegate grunt work to local minions. Keep the reasoning for what matters."

---

*Last updated: 2026-01-12*
