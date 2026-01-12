# Generate → Validate Flow Design

**Date:** 2026-01-12
**Status:** Draft

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

## Failure Handling

On validation failure:
- Do NOT apply changes to file
- Report failure with validator's reasoning
- Log full context for debugging
- Continue to next file (don't abort batch)

No retry - fail fast, let user see why.

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

## Implementation Tasks

1. Update `models.yaml` with validator config
2. Update `get_minion_config()` → `get_configs()` returning both
3. Add `validate_change()` function in new `llm_gc/validator.py`
4. Add failure logging to `~/.minions/failures.log`
5. Update `polish_file()` to call validator before write
6. Update `sweep` to use validation
7. Rewrite `setup` command with interactive flow
8. Add `--no-validate` and `--validator-model` flags
9. Update SKILL.md docs

## Trade-offs

| Aspect | With Validation | Without |
|--------|----------------|---------|
| Latency | 2x (two model calls) | 1x |
| Accuracy | Higher - catches errors | Lower |
| Safety | Proactive | Reactive (syntax check only) |
| Complexity | More code | Simpler |

Validation is worth it for auto-apply tasks (polish, sweep) where bad output = broken code.
