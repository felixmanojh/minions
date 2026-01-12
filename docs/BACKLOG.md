# Minions: Product Backlog

*Last updated: 2026-01-12*

## Prioritization Framework

| Priority | Criteria |
|----------|----------|
| **P0** | Blocks core loop (validation broken, can't install) |
| **P1** | Research-validated improvements (Stanford findings) |
| **P2** | Expands capability (new tasks, languages) |
| **P3** | Nice to have (UI, dashboards) |

---

## P0: Trust Repairs

*These block the core value prop. Fix first.*

| Task | Why | Research Backing |
|------|-----|------------------|
| Fix missing code block output | Most common failure mode | — |
| Simplify prompts to single-step | Multi-step confuses local models | 56% improvement from decomposition |
| Chunk large files before processing | Long context degrades performance | 30% drop on long contexts |
| Enforce 7B minimum model size | Small models ineffective | "Models <3B not effective" |

---

## P1: Architecture Alignment

*Align with proven MinionS protocol from Stanford research.*

| Task | Why | Research Backing |
|------|-----|------------------|
| Formalize Decompose → Execute → Aggregate loop | Match proven architecture | Core of MinionS protocol |
| Claude decomposes, minions execute single tasks | Task decomposition is key | 56% improvement |
| Add structured output schemas to prompts | Cleaner parallel processing | MinionS uses Pydantic schemas |
| Make max_retries configurable per task type | Control iteration depth | `max_rounds` parameter |

### Decompose → Execute → Aggregate Explained

```
┌─────────────────────────────────────────────────────────────┐
│                      CLAUDE (Cloud)                         │
│  DECOMPOSE                              AGGREGATE           │
│  Break complex task ──────────────────► Combine results     │
│  into simple subtasks                   or request more     │
└──────────┬──────────────────────────────────▲───────────────┘
           │ subtasks                 results │
           ▼                                  │
┌─────────────────────────────────────────────────────────────┐
│                      MINIONS (Local)                        │
│  EXECUTE (parallel)                                         │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐              │
│  │Chunk 1 │ │Chunk 2 │ │Chunk 3 │ │Chunk 4 │              │
│  │Subtask │ │Subtask │ │Subtask │ │Subtask │              │
│  └────────┘ └────────┘ └────────┘ └────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## P2: Clarity and Learning

*Improve user understanding and feedback loops.*

| Task | Why |
|------|-----|
| Skill selection guide | "use polish for single file, sweep for directories, swarm for parallel" |
| Retry feedback loop | Surface actionable fixes, not just "failed" |
| Failure classification | Categorize errors to find patterns |
| Arena for model A/B testing | Help users pick right model for their code |
| TypeScript support | Second language, bigger audience |

---

## P3: Capability Expansion

*Nice to have after core is solid.*

| Task | Why |
|------|-----|
| `/minion-insights` skill | Claude analyzes failure logs |
| Export for fine-tuning | Training data generation |
| Multi-language support | Go, Rust, etc. |

---

## Kill Signal

> If validation failure rate does not drop below 70% after P0 fixes, reassess the validation approach entirely.

---

## Research Foundation

Backlog informed by [Stanford Minions research](https://arxiv.org/abs/2502.15964):

| Finding | Impact | Applied |
|---------|--------|---------|
| Task decomposition improves performance 56% | Critical | P0: Single-step prompts |
| Long context degrades performance 30% | Critical | P0: Chunk files |
| Models <3B not effective | Important | P0: 7B minimum |
| Decompose → Execute → Aggregate works | Important | P1: Formalize loop |
| Structured output improves quality | Medium | P1: Pydantic schemas |

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-12 | Initial backlog from SWOT + Stanford research |
