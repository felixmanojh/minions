# Generate → Validate Flow Design

**Date:** 2026-01-12
**Status:** Draft

## References

Best practices incorporated from:
- [Aider: Linting and testing](https://aider.chat/docs/usage/lint-test.html) - AST-based linting, error context
- [Aider: Linting with tree-sitter](https://aider.chat/2024/05/22/linting.html) - Language-agnostic parsing
- [Awesome-LLMs-as-Judges](https://github.com/CSHaitao/Awesome-LLMs-as-Judges) - LLM-as-judge patterns
- [Self-Verification LLM](https://github.com/WENGSYX/Self-Verification) - Structured validation

## Overview

Add a validation step to minion operations. After generation, a second model checks the output before applying changes. This catches errors proactively instead of reactively.

```
┌──────────┐     ┌───────────┐     ┌─────────┐
│ Generate │ ──▶ │ Validate  │ ──▶ │  Apply  │
│ (Model A)│     │ (Model B) │     │ or Fail │
└──────────┘     └───────────┘     └─────────┘
```

## Validation Checks

The validator checks three things:

1. **Syntax valid** - Does the code compile/parse?
2. **Task compliance** - Did it actually do what was requested (add docstrings, types, etc.)?
3. **Preservation** - Is the original logic intact (no accidental changes)?

Validator returns: `PASS` or `FAIL` with reason.

## Pre-Validation: AST Linting (from Aider)

Before LLM validation, run fast AST-based syntax check using tree-sitter:

```
┌──────────┐     ┌───────────┐     ┌───────────┐     ┌─────────┐
│ Generate │ ──▶ │ AST Lint  │ ──▶ │ Validate  │ ──▶ │  Apply  │
│ (Model A)│     │(tree-sitter)│   │ (Model B) │     │ or Fail │
└──────────┘     └───────────┘     └───────────┘     └─────────┘
                      │
                      ▼ (fail fast on syntax errors)
```

Benefits:
- **Fast** - No LLM call needed for obvious syntax errors
- **Language-agnostic** - tree-sitter supports 100+ languages
- **Precise** - Reports exact error location in AST

```python
# llm_gc/linter.py
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

def check_syntax(code: str, language: str = "python") -> tuple[bool, list[dict]]:
    """Check syntax using tree-sitter AST parsing.

    Returns (is_valid, errors) where errors contain line/column info.
    """
    parser = Parser(Language(tspython.language()))
    tree = parser.parse(bytes(code, "utf8"))

    errors = []
    def find_errors(node):
        if node.type == "ERROR":
            errors.append({
                "line": node.start_point[0] + 1,
                "column": node.start_point[1],
                "text": code.splitlines()[node.start_point[0]] if node.start_point[0] < len(code.splitlines()) else ""
            })
        for child in node.children:
            find_errors(child)

    find_errors(tree.root_node)
    return len(errors) == 0, errors
```

## Error Context (from Aider)

When reporting errors to the LLM validator, show surrounding function/class context, not just line numbers. LLMs are bad at line numbers but good with context.

```python
def get_error_context(code: str, error_line: int) -> str:
    """Get the function/class containing the error line."""
    # Use tree-sitter to find enclosing scope
    # Return: function name + signature + error line highlighted
```

Example error report to validator:
```
Syntax error in function `process_data`:

def process_data(items: list) -> dict:
    result = {}
    for item in items:
        result[item.id] = item.value  # <-- ERROR: unexpected indent
    return result
```

Not:
```
Syntax error on line 42
```

## Failure Handling with Retry Loop

On validation failure, attempt one retry with error feedback:

```
┌──────────┐     ┌───────────┐     ┌───────────┐
│ Generate │ ──▶ │ AST Lint  │ ──▶ │ Validate  │
│ (Model A)│     │(tree-sitter)│   │ (Model B) │
└──────────┘     └───────────┘     └───────────┘
      ▲                                  │
      │         ┌─────────────┐          │
      └─────────│ Retry with  │◀─────────┘ (on FAIL)
                │ error context│
                └─────────────┘
                       │
                       ▼ (still fails after retry)
                ┌─────────────┐
                │ Notify      │
                │ Claude Code │
                └─────────────┘
```

### Retry Flow

1. **First attempt fails** → Send error + original + generated to generator
2. **Retry prompt:**
   ```
   Your previous output had an error:
   {validator_reason}

   Original file:
   ```python
   {original}
   ```

   Your output (with error):
   ```python
   {generated}
   ```

   Fix the issue and output the corrected file:
   ```
3. **Retry succeeds** → Apply and continue
4. **Retry fails** → Log failure, notify Claude Code, continue to next file

### Notification to Claude Code

When retry fails, return structured error for Claude Code to handle:

```json
{
  "status": "failed",
  "file": "src/foo.py",
  "attempts": 2,
  "last_error": "Logic changed: removed error handling in try block",
  "suggestion": "Manual review required - minion unable to complete task"
}
```

Claude Code can then:
- Show the error to user
- Offer to do the task itself
- Skip and continue

### Config for Retry

```yaml
validation:
  max_retries: 1        # 0 = no retry, 1 = one retry (default)
  notify_on_fail: true  # return structured error for Claude Code
```

```bash
# Override via CLI
python scripts/minions.py polish src/foo.py --max-retries 2
python scripts/minions.py polish src/foo.py --no-retry  # same as --max-retries 0
```

## Logging

Dual logging for debugging:

### Session File (`sessions/<timestamp>.json`)
Full context for reproducibility:
```json
{
  "task": "add docstrings",
  "file": "src/foo.py",
  "original": "...",
  "generated": "...",
  "validation": {
    "result": "FAIL",
    "reason": "Logic changed: removed error handling on line 42",
    "model": "codellama:7b"
  }
}
```

### Failures Log (`~/.minions/failures.log`)
Quick reference, one line per failure:
```
2026-01-12 14:30:12 | src/foo.py | FAIL | Logic changed: removed error handling
2026-01-12 14:30:45 | src/bar.py | FAIL | Syntax error: unexpected indent
```

## Model Configuration

### Config Structure (`models.yaml`)

```yaml
preset: standard

presets:
  lite:
    minion:
      model: qwen2.5-coder:7b
      temperature: 0.2
      max_tokens: 1024
      num_ctx: 32768
    validator: same  # use minion model

  standard:
    minion:
      model: qwen2.5-coder:7b
      temperature: 0.2
      max_tokens: 1024
      num_ctx: 32768
    validator:
      model: codellama:7b-code
      temperature: 0.1
      max_tokens: 400
      num_ctx: 32768

  expert:
    minion:
      model: qwen2.5-coder:14b
      temperature: 0.2
      max_tokens: 2048
      num_ctx: 65536
    validator:
      model: deepseek-coder:33b
      temperature: 0.1
      max_tokens: 400
      num_ctx: 32768
```

### Environment Overrides

```bash
MINIONS_MODEL=qwen2.5-coder:14b
MINIONS_VALIDATOR=codellama:7b
MINIONS_NUM_CTX=65536
```

### CLI Override

```bash
python scripts/minions.py polish src/foo.py --validator-model codellama:7b
python scripts/minions.py polish src/foo.py --no-validate  # skip validation
```

## Interactive Setup

`python scripts/minions.py setup` handles complete onboarding:

### Flow for New Users (No Models)

```
$ python scripts/minions.py setup

✓ Ollama running

No models installed. Let's get you set up!

Choose setup:
  1. Lite - single model (generate + validate with same)
  2. Standard - two models (recommended)
  3. Expert - two models, larger sizes

[2]: 2

── Standard Setup ──

Available coding models:

  Small (1-4GB VRAM):
    1. qwen2.5-coder:3b      ~2GB
    2. starcoder2:3b         ~2GB
    3. codegemma:2b          ~1.5GB

  Medium (4-10GB VRAM):
    4. qwen2.5-coder:7b      ~4.5GB  ★ recommended generator
    5. codellama:7b          ~4GB    ★ recommended validator
    6. starcoder2:7b         ~4.5GB
    7. codegemma:7b          ~5GB
    8. codestral:22b         ~12GB

  Large (16GB+ VRAM):
    9. qwen2.5-coder:14b     ~9GB
   10. qwen2.5-coder:32b     ~20GB
   11. starcoder2:15b        ~10GB
   12. deepseek-coder:33b    ~20GB
   13. codellama:34b         ~20GB

Select generator [4]: 4
Select validator [5]: 5

Pulling qwen2.5-coder:7b... ████████████ 100% ✓
Pulling codellama:7b-code... ████████████ 100% ✓

✓ Setup complete:
  - minion: qwen2.5-coder:7b
  - validator: codellama:7b-code

Run 'minions polish <file>' to start!
```

### Flow for Existing Users (Has Models)

```
$ python scripts/minions.py setup

✓ Ollama running

Installed models:
  1. qwen2.5-coder:7b
  2. deepseek-coder:1.3b
  3. codellama:7b-code

Choose setup:
  1. Lite - single model
  2. Standard - two models (recommended)
  3. Expert - custom selection

[2]: 2

Select generator [1]: 1
Select validator (or 'same') [3]: 3

✓ Config saved:
  - minion: qwen2.5-coder:7b
  - validator: codellama:7b-code
```

### Recommendations per Setup

| Setup    | Generator Recommendation | Validator Recommendation |
|----------|-------------------------|-------------------------|
| Lite     | qwen2.5-coder:7b        | (same)                  |
| Standard | qwen2.5-coder:7b        | codellama:7b            |
| Expert   | qwen2.5-coder:14b+      | different architecture  |

## Validator Prompt

```
You are a code validator. Check if the modified code is correct.

Original file:
```python
{original_content}
```

Modified file:
```python
{modified_content}
```

Task requested: {task}

Check:
1. SYNTAX: Does the modified code have valid syntax?
2. TASK: Did it complete the requested task ({task})?
3. PRESERVATION: Is all original logic preserved exactly?

Respond with exactly one line:
PASS - if all checks pass
FAIL: <reason> - if any check fails

Examples:
PASS
FAIL: Syntax error on line 42
FAIL: Did not add docstrings to function bar()
FAIL: Logic changed - removed error handling in try block
```

## Validation Toggle

Validation is **on by default** for safety. User can opt-out:

```bash
# Default: validation enabled
python scripts/minions.py polish src/foo.py

# Skip validation (faster, riskier)
python scripts/minions.py polish src/foo.py --no-validate
```

## Custom Linting (from Aider)

Users can specify their own linter command for additional checks:

```bash
# Use ruff for Python
python scripts/minions.py polish src/foo.py --lint-cmd "ruff check"

# Use eslint for JavaScript
python scripts/minions.py polish src/app.js --lint-cmd "eslint"

# Disable all linting (AST + custom)
python scripts/minions.py polish src/foo.py --no-lint
```

Linting runs after generation, before LLM validation:
1. AST check (tree-sitter) - always runs unless `--no-lint`
2. Custom lint (if `--lint-cmd`) - runs user's linter
3. LLM validation - runs unless `--no-validate`

If any step fails, skip to next file with error logged.

## Implementation Tasks

### Phase 1: Core Validation
1. Update `models.yaml` with validator config
2. Update `get_minion_config()` → `get_configs()` returning both minion + validator
3. Add `llm_gc/linter.py` with tree-sitter AST checking
4. Add `llm_gc/validator.py` with LLM validation logic
5. Add `get_error_context()` for LLM-friendly error reporting
6. Add failure logging to `~/.minions/failures.log`
7. Add retry loop logic with error feedback to generator

### Phase 2: Integration
8. Update `polish_file()` flow: generate → AST lint → LLM validate → retry → apply
9. Update `sweep` to use validation
10. Add `--no-validate`, `--no-lint`, `--validator-model`, `--lint-cmd` flags
11. Add `--max-retries`, `--no-retry` flags
12. Return structured JSON for Claude Code on final failure

### Phase 3: Interactive Setup
13. Rewrite `setup` command with interactive model selection
14. Add model download flow with progress
15. Save user choices to `models.yaml`

### Phase 4: Documentation
16. Update SKILL.md docs with new flags
17. Update README with validation explanation

### Dependencies to Add
```toml
# pyproject.toml
[project]
dependencies = [
    "tree-sitter>=0.23.0",
    "tree-sitter-python>=0.23.0",
    "tree-sitter-javascript>=0.23.0",
    "grep-ast>=0.3.0",        # Aider's TreeContext for error context
    "rich>=13.0.0",           # Pretty CLI for interactive setup
    "pydantic>=2.0.0",        # Validation models
]
```

---

## Implementation Patterns (from Research)

### 1. AST Linting with Tree-Sitter (from Aider `linter.py`)

```python
# llm_gc/linter.py
from grep_ast import filename_to_lang
from grep_ast.tsl import get_parser
from dataclasses import dataclass
from typing import Optional

@dataclass
class LintResult:
    text: str
    lines: list[int]  # Line numbers with errors

def basic_lint(fname: str, code: str) -> Optional[LintResult]:
    """Use tree-sitter to find syntax errors."""
    lang = filename_to_lang(fname)
    if not lang:
        return None

    parser = get_parser(lang)
    tree = parser.parse(bytes(code, "utf-8"))
    errors = traverse_tree(tree.root_node)

    if not errors:
        return None
    return LintResult(text="", lines=errors)

def traverse_tree(node) -> list[int]:
    """Find ERROR nodes in AST."""
    errors = []
    if node.type == "ERROR" or node.is_missing:
        errors.append(node.start_point[0])
    for child in node.children:
        errors += traverse_tree(child)
    return errors
```

### 2. Error Context with TreeContext (from Aider)

```python
# llm_gc/linter.py (continued)
from grep_ast import TreeContext

def get_error_context(fname: str, code: str, line_nums: list[int]) -> str:
    """Get context around error lines, marked with █."""
    context = TreeContext(
        fname,
        code,
        color=False,
        line_number=True,
        child_context=False,
        last_line=False,
        margin=0,
        mark_lois=True,  # Mark lines of interest
        loi_pad=3,       # 3 lines of context
        show_top_of_file_parent_scope=False,
    )

    context.add_lines_of_interest(set(line_nums))
    context.add_context()

    s = "s" if len(line_nums) > 1 else ""
    output = f"## See relevant line{s} below marked with █.\n\n"
    output += fname + ":\n"
    output += context.format()
    return output
```

### 3. LLM Validator (from quotient-ai/judges)

```python
# llm_gc/validator.py
from dataclasses import dataclass
from typing import Optional, Literal
from pydantic import BaseModel

class ValidationResult(BaseModel):
    """Result of validation check."""
    passed: bool
    reason: Optional[str] = None
    check_type: Literal["syntax", "task", "preservation"] = "task"

@dataclass
class CodeValidator:
    """LLM-based code validator."""
    client: "OllamaClient"
    config: "ModelConfig"

    def validate(self, original: str, modified: str, task: str) -> ValidationResult:
        prompt = self._build_prompt(original, modified, task)
        response, _ = self.client.prompt(prompt, self.config, role="validator")
        return self._parse_response(response)

    def _parse_response(self, response: str) -> ValidationResult:
        response = response.strip()
        if response.startswith("PASS"):
            return ValidationResult(passed=True)
        elif response.startswith("FAIL:"):
            reason = response[5:].strip()
            return ValidationResult(passed=False, reason=reason)
        else:
            return ValidationResult(passed=False, reason=f"Invalid response: {response}")
```

### 4. Retry Loop (from LangGraph Reflection)

```python
# llm_gc/validator.py (continued)
@dataclass
class RetryConfig:
    max_retries: int = 1
    notify_on_fail: bool = True

class GenerateValidateLoop:
    def __init__(self, generator, validator, config: RetryConfig):
        self.generator = generator
        self.validator = validator
        self.config = config

    def run(self, original: str, task: str) -> dict:
        """Generate → Validate → Retry loop."""
        attempt = 0
        last_error = None
        generated = None

        while attempt <= self.config.max_retries:
            if attempt == 0:
                generated = self.generator.generate(original, task)
            else:
                # Retry with error feedback
                generated = self.generator.retry_with_error(
                    original, generated, last_error
                )

            result = self.validator.validate(original, generated, task)

            if result.passed:
                return {"status": "success", "output": generated, "attempts": attempt + 1}

            last_error = result.reason
            attempt += 1

        # All retries failed - notify Claude Code
        return {
            "status": "failed",
            "attempts": attempt,
            "last_error": last_error,
            "suggestion": "Manual review required - minion unable to complete task"
        }
```

### 5. Interactive CLI Setup (with Rich)

```python
# scripts/minions.py setup command
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, IntPrompt
from rich.progress import Progress

console = Console()

CODING_MODELS = [
    ("qwen2.5-coder:3b", 2, None),
    ("qwen2.5-coder:7b", 4.5, "generator"),
    ("codellama:7b", 4, "validator"),
    ("starcoder2:7b", 4.5, None),
    ("codegemma:7b", 5, None),
    ("codestral:22b", 12, None),
    ("qwen2.5-coder:14b", 9, None),
    ("qwen2.5-coder:32b", 20, None),
    ("starcoder2:15b", 10, None),
    ("deepseek-coder:33b", 20, None),
    ("codellama:34b", 20, None),
]

def setup_standard():
    console.print("\n[bold]── Standard Setup ──[/]\n")

    table = Table(title="Available Coding Models")
    table.add_column("#", style="cyan")
    table.add_column("Model", style="green")
    table.add_column("Size", justify="right")
    table.add_column("Rec", style="yellow")

    for i, (name, size, rec) in enumerate(CODING_MODELS, 1):
        rec_str = f"★ {rec}" if rec else ""
        table.add_row(str(i), name, f"~{size}GB", rec_str)

    console.print(table)

    gen_idx = IntPrompt.ask("\nSelect generator", default=2)
    val_idx = IntPrompt.ask("Select validator", default=3)

    gen_model = CODING_MODELS[gen_idx - 1][0]
    val_model = CODING_MODELS[val_idx - 1][0]

    pull_models_with_progress([gen_model, val_model])
    return {"minion": gen_model, "validator": val_model}

def pull_models_with_progress(models: list[str]):
    """Pull models with Rich progress bar."""
    import subprocess
    for model in models:
        console.print(f"[cyan]Pulling {model}...[/]")
        subprocess.run(["ollama", "pull", model], check=True)
        console.print(f"[green]✓[/] {model}")
```

### 6. Custom Linter Integration (from Aider)

```python
# llm_gc/linter.py (continued)
import subprocess
import re

def run_external_linter(cmd: str, filepath: str) -> Optional[LintResult]:
    """Run user's linter command (ruff, eslint, etc.)."""
    try:
        result = subprocess.run(
            f"{cmd} {filepath}",
            shell=True,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            return None

        errors = result.stdout + result.stderr
        linenums = find_line_numbers(errors, filepath)

        return LintResult(
            text=f"## Running: {cmd} {filepath}\n\n{errors}",
            lines=linenums
        )
    except OSError as err:
        return LintResult(text=f"Linter failed: {err}", lines=[])

def find_line_numbers(text: str, fname: str) -> list[int]:
    """Extract line numbers from linter output."""
    pattern = re.compile(rf"{re.escape(fname)}:(\d+)")
    return [int(m.group(1)) for m in pattern.finditer(text)]
```

### 7. Failure Logging

```python
# llm_gc/logging.py
from pathlib import Path
from datetime import datetime
import json

FAILURES_LOG = Path.home() / ".minions" / "failures.log"
SESSIONS_DIR = Path.home() / ".minions" / "sessions"

def log_failure(file: str, reason: str, session_data: dict = None):
    """Log failure to both quick log and full session."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Quick reference log
    FAILURES_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(FAILURES_LOG, "a") as f:
        f.write(f"{timestamp} | {file} | FAIL | {reason}\n")

    # Full session data
    if session_data:
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        session_file = SESSIONS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(session_file, "w") as f:
            json.dump(session_data, f, indent=2)
```

### 8. Complete Flow

```python
# llm_gc/polish.py - Putting it all together
def polish_file(filepath: str, task: str, config: dict) -> dict:
    """Generate → AST Lint → LLM Validate → Retry → Apply"""
    original = Path(filepath).read_text()

    # 1. Generate
    generated = generator.generate(original, task)

    # 2. AST Lint (fast fail)
    if not config.get("no_lint"):
        lint_result = basic_lint(filepath, generated)
        if lint_result:
            error_ctx = get_error_context(filepath, generated, lint_result.lines)
            generated = generator.retry_with_error(original, generated, error_ctx)
            lint_result = basic_lint(filepath, generated)
            if lint_result:
                log_failure(filepath, "Syntax errors persist", {...})
                return {"status": "failed", "error": "Syntax errors persist"}

    # 3. Custom Lint (if specified)
    if lint_cmd := config.get("lint_cmd"):
        ext_result = run_external_linter(lint_cmd, filepath)
        if ext_result:
            log_failure(filepath, ext_result.text, {...})
            return {"status": "failed", "error": ext_result.text}

    # 4. LLM Validate with retry loop
    if not config.get("no_validate"):
        loop = GenerateValidateLoop(generator, validator, RetryConfig())
        result = loop.run(original, task)
        if result["status"] == "failed":
            log_failure(filepath, result["last_error"], {...})
            return result
        generated = result["output"]

    # 5. Apply
    Path(filepath).write_text(generated)
    return {"status": "success", "file": filepath}
```

---

## Code Pattern Sources

| Component | Source Project | Key Feature |
|-----------|---------------|-------------|
| Tree-sitter lint | [Aider](https://github.com/Aider-AI/aider) | Fast AST-based syntax check |
| TreeContext | [grep-ast](https://github.com/paul-gauthier/grep-ast) | LLM-friendly error context |
| Validator class | [quotient-ai/judges](https://github.com/quotient-ai/judges) | Clean abstraction |
| Retry loop | [LangGraph](https://github.com/langchain-ai/langgraph) | Reflection pattern |
| Rich CLI | [Rich](https://github.com/Textualize/rich) | Professional UX |
| Code extraction | [OpenEvals](https://github.com/langchain-ai/openevals) | Parse LLM output |

## Trade-offs

| Aspect | Full Validation | AST Only | None |
|--------|----------------|----------|------|
| Latency | ~2x (AST + LLM) | ~1.1x | 1x |
| Accuracy | Highest | Medium | Low |
| Safety | Proactive | Catches syntax | Reactive |
| Complexity | Most code | Moderate | Simple |

### When to Use What

| Mode | Use Case |
|------|----------|
| Full validation | Auto-apply (polish, sweep) - bad output = broken code |
| AST only (`--no-validate`) | Quick iterations, trusted prompts |
| None (`--no-lint --no-validate`) | Debugging, testing minion output |

## Future Enhancements (Not in Scope for v1)

From research, interesting patterns we could add later:

1. **Self-consistency** (from LLM-as-judge research) - Run validation 3x, require consensus. Overkill for our use case.

2. **Fine-tuned judge** (from JudgeLM) - Train a specialized model for code validation. Too much effort for now.

3. **Multi-file awareness** - Validator checks cross-file dependencies. Complex but useful for refactors.
