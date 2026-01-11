# Milestone M3 – Patch Generation with Unified Diff

Goal: extend the multi-agent chat to produce actual code patches. Agents discuss the approach, Implementer outputs full modified file contents, Reviewer critiques the code, then we compute and save a unified diff.

## 1. Workflow

```
1. User runs: python scripts/m3_patch.py "Fix bug in X" [--target file1.py file2.py]

2. Target resolution:
   - If --target provided: preload files via FileReader, tell Implementer "Modify these files"
   - If not: Implementer proposes files based on repo context

3. Rounds 1 to N-1: Discussion
   - Implementer proposes approach
   - Reviewer critiques, asks questions

4. Final round: Code generation
   - Implementer outputs full modified file contents in fenced blocks
   - Reviewer critiques actual code
   - Implementer revises if needed

5. Post-chat:
   - Parse modified files from Implementer's final response
   - Compute unified diff against originals
   - Write sessions/<id>.patch
```

## 2. New components

```
llm_gc/
├── parsers/
│   ├── __init__.py
│   └── code_blocks.py       # Parse ```path\n...\n``` blocks from responses
├── tools/
│   └── diff_generator.py    # Compute unified diff via difflib
└── orchestrator/
    └── m3_patch.py          # PatchOrchestrator with target handling

scripts/
└── m3_patch.py              # CLI entry point
```

### `parsers/code_blocks.py`

```python
@dataclass
class FileChange:
    path: str       # Normalized relative path
    content: str    # Full file content (trailing whitespace stripped)

def parse_file_blocks(response: str) -> list[FileChange]:
    """Extract fenced code blocks in ```path/to/file.py\n...\n``` format."""
```

### `tools/diff_generator.py`

```python
def generate_diff(original: str, modified: str, filepath: str) -> str:
    """Return unified diff for a single file."""

def generate_multi_diff(changes: list[tuple[str, str, str]]) -> str:
    """Combine diffs for multiple files into one patch."""
```

Uses `difflib.unified_diff` with proper `--- a/path` / `+++ b/path` headers.

### `orchestrator/m3_patch.py`

Extends `ChatOrchestrator`:
- Accepts `target_files: list[str]` parameter
- Modified agent specs with patch-oriented system messages
- Final-round prompt override instructing full file output
- Post-run: parse response → compute diff → write `.patch` file

## 3. Agent prompts

**Implementer (patch mode):**
```
Draft a concrete plan to solve the task.
When instructed to produce final code, output the COMPLETE modified file(s):
```path/to/file.py
<full file content>
```
```

**Reviewer (patch mode):**
```
Critique the implementer's approach. Check for:
- Correctness and edge cases
- Style consistency with existing code
- Missing error handling
When reviewing final code, focus on bugs that must be fixed.
```

**Final round injection:**
```
THIS IS THE FINAL ROUND. Output the complete modified file contents now.
Use this exact format for each file:
```path/to/file.py
<entire file content here>
```
```

## 4. CLI

```bash
# Explicit targets
python scripts/m3_patch.py "Fix off-by-one error" --target src/foo.py --rounds 3

# Auto-detect
python scripts/m3_patch.py "Add retry logic to OllamaClient"
```

Outputs:
- Transcript: `sessions/<id>.json`
- Summary: `sessions/<id>-summary.txt`
- Patch: `sessions/<id>.patch`

## 5. Acceptance criteria

- [ ] `scripts/m3_patch.py` accepts task + optional `--target` flags
- [ ] Target files echoed to console and logged in transcript metadata
- [ ] Final round prompts Implementer to output full file contents
- [ ] Reviewer critiques actual code before finalization
- [ ] `code_blocks.py` parses fenced blocks, normalizes paths, strips whitespace
- [ ] `diff_generator.py` produces valid unified diff (works with `patch -p1`)
- [ ] Patch written to `sessions/<id>.patch`
- [ ] Transcript JSON includes `patch_path` and `target_files` in metadata
- [ ] Graceful error if no valid code blocks found in final response
