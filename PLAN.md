

## Three GitHub repos to start with

1. **Ollama**: run open source coding models locally and expose a local chat API ([GitHub][1])
2. **Microsoft AutoGen**: multi agent conversation framework, good for agent group chat orchestration ([GitHub][2])
3. **Langroid**: lightweight multi agent framework with agents exchanging messages and tools, very clean mental model ([GitHub][3])

If you want a more software company style multi agent coding setup, also look at MetaGPT, but it can feel heavier ([GitHub][4])

---

## Initial doc: Local Multi LLM Coding Group Chat

### Goal

Build a local first coding assistant where multiple local open source coding models collaborate in a group chat to solve programming tasks, with an optional judge agent and strict safety controls.

### Non goals

* Not a training or finetuning pipeline
* Not a perfect replacement for IDEs on day 1
* Not user-interactive - minions work autonomously and report back to Claude

### User stories

* As a developer, I want 2 to 5 models to propose solutions and critique each other so I get a better final patch
* As a developer, I want to run everything locally so my codebase stays on my machine
* As a developer, I want a final answer that includes a patch plan, actual diffs, and a quick test plan
* As a developer, I want guardrails so no agent can run dangerous commands without my approval

### Core concept

* Each model is an agent with a role (Implementer, Reviewer, Bug Hunter, Perf, Security, Product)
* Agents talk in a shared group chat with a turn scheduler
* One optional Judge agent selects the best approach and merges feedback into a final patch

### Architecture

1. **Local Model Layer**

   * Use Ollama to run multiple models locally, each referenced by a model name
   * Examples: deepseek coder, qwen coder, codestral, llama based code models, etc
   * All requests go to local HTTP endpoints exposed by Ollama ([GitHub][1])

2. **Agent Orchestrator Layer**

   * Use AutoGen or Langroid to manage multi agent chat loops, tool use, and message routing ([Microsoft GitHub][5])
   * Responsibilities:

     * Create agents and roles
     * Define conversation policy (turn taking, stopping rules)
     * Enforce tool permissions
     * Store transcripts

3. **Tools Layer**

   * File read tool (repo scoped)
   * File write tool (repo scoped)
   * Diff tool
   * Test runner tool (runs autonomously, reports results)
   * Patch apply tool (applies diffs directly)
   * Optional: lint, typecheck, formatter

4. **Safety Layer** (autonomous, no human gates)

   * Denylist dangerous commands (rm -rf, sudo, curl pipe sh, etc)
   * Allowlist safe commands for tests (pytest, npm test, cargo test, etc)
   * Path sandboxing: tools can only touch files under the repo root
   * Fail safely and report errors back to Claude
   * No human approval gates - minions are autonomous workers

### Workflow (autonomous)

1. Claude delegates task to minions
2. Orchestrator creates a short shared context: repo summary, constraints, definition of done
3. Agents run in rounds:

   * Round 1: proposals
   * Round 2: critique and risk scan
   * Round 3: implementer produces patch plan and diff
4. Judge agent synthesizes:

   * final patch
   * risk notes
   * test plan
5. Minions apply patch, run tests, report results back to Claude
6. Claude reviews and decides next steps

### MVP scope

* Python package: `llm_gc` (minions for Claude Code)
* Config file: `models.yaml`
* Skills (Claude Code plugin):

  * `/minion-huddle` - multi-agent discussion
  * `/minion-fix` - patch generation and auto-apply
  * `/minion-swarm` - parallel task execution
  * `/minion-queue` - batch task queuing
* Local transcript storage in sessions folder
* Autonomous operation - no user prompts

### Suggested roles for v1

* Implementer: writes the diff
* Reviewer: checks correctness and style
* Bug Hunter: tries to break assumptions, edge cases
* Security: flags risky patterns and secrets
* Judge: selects final answer

### Stopping rules

* Max 3 to 5 rounds
* Hard token budget per agent per round
* Judge ends early if consensus is strong

### Quality rubric for Judge

* Correctness first
* Minimal diff
* Tests updated or added
* No new security risks
* Clear instructions to reproduce

### Metrics

* Time to first viable patch
* Number of iterations needed
* Tests pass rate after apply
* User accepted patch rate

### Milestones

* M0: Ollama models runnable locally and accessible ✅
* M1: basic group chat with 3 roles, no tools ✅
* M2: read only tools and repo summarizer ✅
* M3: patch generation with unified diff ✅
* M4: autonomous test runner and auto-apply ✅
  * Test runner tool (pytest, npm test, cargo test)
  * Auto-apply patches (no confirmation)
  * Safety constraints (denylist, path sandbox)
* M5: judge agent and quality scoring
  * Judge agent selects best approach
  * Quality rubric scoring
  * Early stopping on consensus
