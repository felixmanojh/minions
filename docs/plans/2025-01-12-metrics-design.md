# Minion Metrics Design

## Overview

Comprehensive analytics for understanding minion performance, quality, usage patterns, and efficiency.

## Data Model

Every minion task logs a `MetricEvent`:

```python
{
    "id": "uuid",
    "timestamp": "2025-01-11T23:45:00",
    "session_id": "20250111-234500-m1",

    "task_type": "chat|patch|swarm|judge",
    "task_description": "fix the pagination bug",

    "duration_ms": 1250,
    "model": "qwen2.5-coder:7b",
    "role": "implementer",
    "tokens_estimated": 450,

    "success": true,
    "retries": 0,
    "fallback_used": false,
    "judge_score": 0.85,

    "patch_applied": true,
    "tests_passed": true,
    "error": null
}
```

Storage: `~/.minions/metrics.json` (array, capped at 1000 events)

## Collection Points

| Component | Captures |
|-----------|----------|
| orchestrator/base.py | Model calls: latency, tokens, model |
| swarm.py | Task start/end, retries, batch stats |
| judge.py | Scores, consensus, selected proposal |
| tools/test_runner.py | Pass/fail, duration |
| tools/patch_apply.py | Applied/failed, strategy |

## CLI Interface

```bash
python scripts/metrics.py              # Summary dashboard
python scripts/metrics.py --role X     # Filter by role
python scripts/metrics.py --today      # Today only
python scripts/metrics.py --failures   # Failed tasks
python scripts/metrics.py --export csv # Export
python scripts/metrics.py --help-metrics  # Metric reference
```

## Metric Reference

| Metric | What | Good | Okay | Bad | Fix |
|--------|------|------|------|-----|-----|
| Success Rate | % tasks completed | >90% | 70-90% | <70% | Check models, simplify prompts |
| Latency | Response time | <2s | 2-5s | >5s | Smaller models, check resources |
| Retry Rate | % needing retry | <10% | 10-25% | >25% | Better prompts, capable models |
| Judge Score | Quality 0-1 | >0.8 | 0.6-0.8 | <0.6 | More context, clearer tasks |
| Patch Success | % applied cleanly | >85% | 60-85% | <60% | More file context |
| Test Pass Rate | % tests passed | >90% | 70-90% | <70% | Review patches |

## Implementation

1. `llm_gc/metrics.py` - Core module
2. `scripts/metrics.py` - CLI
3. Integration into existing components
