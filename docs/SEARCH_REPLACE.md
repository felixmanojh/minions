# Optional Search/Replace Patch Format

Unified diffs work well in most cases, but small local models can sometimes produce diffs that fail to apply cleanly (line numbers drift, surrounding context shifts). As a fallback, we can support a SEARCH/REPLACE format:

```
SEARCH:
<original snippet>
===
REPLACE:
<new snippet>
END
```

Implementation sketch:

1. During final Implementer output, allow (or require) the model to emit SEARCH/REPLACE blocks in addition to full file dumps.
2. Parse blocks into structured objects (file path, search text, replace text).
3. When applying patches, attempt unified diff first; on failure, fall back to search/replace with fuzzy matching (diff-match-patch).
4. Log which method succeeded for visibility.

Status: not yet implemented. This doc tracks the design so we can add it if unified diffs prove brittle.
