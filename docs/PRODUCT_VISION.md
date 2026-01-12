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

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code (Cloud)                      │
│              Planning • Strategy • Reasoning                │
│                 Powerful • Expensive • Remote               │
└─────────────────────────────┬───────────────────────────────┘
                              │ delegates mechanical tasks
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Minions (Local)                          │
│         Docstrings • Type hints • Repetitive fixes         │
│              Free • Private • On your hardware              │
└─────────────────────────────────────────────────────────────┘
```

Like Gru and his Minions: Gru handles the master plan, Minions handle the grunt work.

**Why local?**
- **Free** — No API costs, run as much as you want
- **Private** — Your code never leaves your machine
- **Fast** — No network latency, parallel execution

**Claude always classifies the task. Minions never self-select work.**

---

## A Concrete Example

**Task:**
```
42 Python files missing docstrings
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
Claude tasks avoided: 42 mechanical file edits
```

---

## Target Users

1. **Claude Code power users** — developers who use Claude Code daily and want to preserve intelligence for hard problems
2. **Privacy-conscious teams** — code never leaves your machine
3. **Cost-conscious developers** — local execution is free
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

| Preset | Minion | Validator | Hardware | Use Case |
|--------|--------|-----------|----------|----------|
| lite | 7b | same | 8GB RAM | Fast, minimal hardware |
| standard | 7b | 7b | 8GB RAM | Balanced safety |
| expert | 14b | 14b | 16GB RAM | Better accuracy |
| custom | any | any | varies | Your choice via config |

Users can override any model via `MINIONS_MODEL` env var or `models.yaml`.

---

## Success Metrics

| Metric | What It Measures |
|--------|------------------|
| **Tasks delegated per session** | Mechanical work offloaded from Claude |
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

### Phase 4: Expansion
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

## Research Foundation

This approach is validated by Stanford research:

**[Minions: Cost-efficient Collaboration Between On-device and Cloud Language Models](https://arxiv.org/abs/2502.15964)** (Narayan et al., Stanford, 2025)

Key findings:
- Cloud model decomposes tasks → local model executes in parallel
- Achieves **97.9% of frontier performance** at **5.7x cost reduction**
- Local models struggle with multi-step reasoning but excel at focused subtasks

We independently arrived at the same architecture. The research validates our core bet.

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
