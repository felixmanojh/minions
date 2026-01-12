# Minions: Product Strategy

## Strategic Context

### Where We Play

**Market:** Developer tools for AI-assisted coding
**Segment:** Claude Code users who want to optimize their AI usage
**Positioning:** The local workforce for Claude Code

**Key insight:** Cloud thinks. Local executes. Your code stays private, your wallet stays full.

### The Landscape

| Player | Philosophy | Strength | Gap We Fill |
|--------|------------|----------|-------------|
| **Claude Code** | "AI drives, you supervise" | Autonomous agent, terminal-first, MCP extensible | Burns intelligence on mechanical tasks |
| **Cursor** | "You drive, AI assists" | Familiar IDE, repo-wide context, multi-model | No delegation, cloud-only compute |
| **Copilot** | "AI pair programmer" | Inline completions, ubiquitous, low friction | No orchestration, no autonomy |
| **Ollama** | "Infrastructure for local LLMs" | 100% local, thinking mode, API for scripting | Raw capability, no workflow layer |
| **Aider** | "AI pair in terminal with git" | Git-native, multi-file edits, conversation flow | No validation, changes applied directly |

### Why We Win

| Against | Our Advantage |
|---------|---------------|
| Claude Code | We handle grunt work locally so Claude can focus on reasoning |
| Cursor/Copilot | We're free, private, and designed for mechanical bulk tasks |
| Ollama | We're the workflow layer that makes raw models useful for coding |
| Aider | We validate before applying — Generate → Validate → Retry |

**Our wedge:** None of these separate thinking from doing. We do.

### Research Validation

Our approach is independently validated by Stanford research:

**Paper:** [Minions: Cost-efficient Collaboration Between On-device and Cloud Language Models](https://arxiv.org/abs/2502.15964)
**Authors:** Narayan, Biderman, Eyuboglu, May, Linderman, Zou, Ré (Stanford)

| Finding | Implication for Us |
|---------|-------------------|
| Naive back-and-forth recovers only 87% performance | Simple delegation isn't enough |
| Task decomposition by cloud is key | Claude must classify/decompose, minions execute |
| 97.9% performance at 5.7x cost reduction | The approach works at scale |
| Local models struggle with multi-step instructions | Keep minion tasks simple and focused |

**Key insight from the paper:**
> "The remote model breaks down complex problems into simpler subtasks focused on shorter document segments, which the local model processes in parallel."

This is exactly our architecture: Claude thinks, Minions execute simple focused tasks.

---

## Strategic Bets

### Bet 1: Developers Will Delegate

**Hypothesis:** Power users will trust local models for mechanical work once validation proves reliable.

**Evidence needed:**
- 80%+ validation success rate
- Users apply changes without manual review
- Repeat usage after first week

**Risk:** Users don't trust local models at all, even with validation.

**Mitigation:** Model-agnostic design — users choose 7b/14b/32b/70b based on their hardware and trust level.

---

### Bet 2: Claude Code Is The Right Host

**Hypothesis:** Integrating as Claude Code skills is the fastest path to adoption.

**Evidence needed:**
- Skills get discovered and used
- Users prefer `/minion-sweep` over CLI
- Claude proactively suggests delegation

**Risk:** Claude Code ecosystem doesn't grow, or Anthropic changes skill system.

---

### Bet 3: Validation Is The Moat

**Hypothesis:** Generate → Validate → Retry creates trust that raw generation cannot.

**Evidence needed:**
- Users cite validation as reason for trust
- Competitors lack equivalent safety
- Failure logs enable continuous improvement

**Risk:** Validation overhead makes it slower than just using Claude.

---

### Bet 4: Insights Create Stickiness

**Hypothesis:** Claude analyzing minion performance creates a feedback loop users value.

**Evidence needed:**
- Users ask for insights regularly
- Insights lead to preset upgrades
- Pattern detection improves success rate

**Risk:** Users don't care about meta-analysis, just want it to work.

---

### Bet 5: Arena Becomes Model Discovery Platform

**Hypothesis:** Helping users find the right local model for their code creates unique value no one else provides.

**The problem:**
- 100+ models on Ollama, users don't know which to pick
- Generic benchmarks (MMLU, HumanEval) don't reflect real tasks
- No personalized "which model for MY code?" exists

**The solution:** Arena — A/B testing downloaded models on user's actual code.

```
Minions run battles → Generate data → Claude interprets → Recommends preset
```

**Two strategic paths:**

| Path | Description | Outcome |
|------|-------------|---------|
| **Tool** | Feature within metrics skill | Solves user's immediate "which model?" problem |
| **Platform** | Aggregate anonymous arena results | Community-driven model rankings for real coding tasks |

**Evidence needed:**
- Users run arena before choosing presets
- Arena results correlate with long-term success rate
- Community data reveals model strengths (e.g., "14b wins on complex files")

**Risk:** Users just pick a model and never benchmark.

**Opportunity:** If we aggregate arena data, we become the source of truth for "which local model actually works for coding" — a position no one holds today.

---

## Go-To-Market

### Phase 1: Seed (Now)

**Goal:** Prove the core loop works

| Action | Target |
|--------|--------|
| Ship to GitHub | Public repo, MIT license |
| Dogfood internally | Use on own codebase daily |
| Document honestly | README with real limits |

**Success:** 10 stars, 3 external users, 1 bug report we can fix

---

### Phase 2: Validate (Month 1-2)

**Goal:** Find early adopters who love it

| Action | Target |
|--------|--------|
| Post to r/ClaudeAI, HN | Show concrete example |
| Collect feedback | GitHub issues, Discord |
| Ship insights skill | `/minion-insights` live |

**Success:** 50 stars, 10 active users, clear patterns in feedback

---

### Phase 3: Grow (Month 3-6)

**Goal:** Expand use cases and reliability

| Action | Target |
|--------|--------|
| Multi-language support | TypeScript, Go |
| Fine-tuning export | Users can train custom minions |
| Team features | Shared model configs |

**Success:** 200 stars, users reporting real time savings

---

## Prioritization Framework

### What We Build Next

| Priority | Criteria |
|----------|----------|
| **P0** | Blocks core loop (validation broken, can't install) |
| **P1** | Improves trust (better error messages, logging) |
| **P2** | Expands capability (new tasks, languages) |
| **P3** | Nice to have (UI, dashboards) |

### Current P0/P1 Queue

1. **P1:** `/minion-insights` skill — surface patterns from logs
2. **P1:** Better truncation handling — detect and report clearly
3. **P1:** Timing metrics — show actual time saved
4. **P2:** TypeScript support — second language
5. **P2:** Export for fine-tuning — training data generation

---

## Competitive Lessons

What we can learn from each player's approach:

| From | Lesson | Apply To Minions |
|------|--------|------------------|
| **Claude Code** | Plan mode + permission prompts build trust | Our validation step serves same purpose |
| **Cursor** | Diff review before apply is essential UX | Always show what will change before applying |
| **Copilot** | Low friction drives adoption | Skills should "just work" without config |
| **Ollama** | Thinking mode (`<think>` sections) aids debugging | Surface minion reasoning in failure logs |
| **Aider** | Git commits per change enable rollback | Consider auto-commit option for each polish |

### Trust Mechanisms Comparison

| Tool | Trust Mechanism | Minions Equivalent |
|------|-----------------|-------------------|
| Claude Code | Plan mode, permission prompts | Validation step, `--dry-run` |
| Cursor | Diff review, line-by-line accept | Patch preview before apply |
| Aider | Git commit per change, easy revert | Session logs, `--backup` flag |
| Ollama Agent | Read-only mode, undo history | `--dry-run`, failure logs |

**Key insight:** Every successful tool has a trust/safety mechanism. Our Generate → Validate → Retry pipeline is our version.

---

## Competitive Positioning

### We Are Not

- A Claude Code replacement
- A general-purpose AI coding tool
- A way to avoid paying for cloud AI

### We Are

- Claude Code's local workforce
- A validation layer for local model output
- A way to preserve cloud intelligence for hard problems

### Positioning Statement

> For Claude Code power users who waste intelligence on mechanical tasks, Minions is a local delegation layer that handles grunt work with validation, unlike raw local models which lack safety or cloud-only tools which burn reasoning on repetition.

---

## Key Metrics Dashboard

| Metric | Current | Target (3mo) |
|--------|---------|--------------|
| Validation success rate | ~80% | 90% |
| Avg files per session | ? | 20+ |
| User trust (apply without review) | ? | 70% |
| GitHub stars | 0 | 100 |
| Active weekly users | 1 | 25 |

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Small models unreliable | Medium | High | Validation catches errors; users can upgrade to 14b/32b |
| Claude Code skills deprecated | Low | High | CLI works standalone |
| Users don't trust local models | Medium | Medium | Transparent logging, insights, model choice |
| Ollama changes API | Low | Medium | Abstract client layer |
| Better competitor emerges | Medium | Medium | Move fast, build community |

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-12 | Use 7b for validation (not 1.5b) | 1.5b inconsistent on large files |
| 2026-01-12 | Increase max_tokens to 8192 | Prevent truncation on real files |
| 2026-01-12 | Claude does insights, not minions | Fits intelligence separation |
| 2026-01-12 | Pure open source, no paid tier | Using open source models; better to build together |
| 2026-01-12 | Insights on-demand, not automatic | User controls when to analyze |
| 2026-01-12 | Non-Claude hosts later | Prove it works with Claude Code first |
| 2026-01-12 | Metric: tasks delegated, not time saved | Can't measure counterfactual "Claude minutes" |

---

*Last updated: 2026-01-12*
