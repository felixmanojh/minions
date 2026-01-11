---
name: minion-metrics
description: >
  View analytics and performance data for your local minions. Shows success rates,
  latency, quality scores, and health indicators. Use to understand how your minions
  are performing and identify issues.
allowed-tools: Bash, Read
---

# Minion Metrics

View performance analytics for your local minion squad. See success rates, latency, quality scores, and identify what's working vs what needs attention.

## When to use

- Check how your minions are performing overall
- Investigate failures or slow response times
- Compare performance across different models
- Export data for deeper analysis

## Usage

### Dashboard (default)

Show the main metrics dashboard with health indicators:

```bash
source .venv/bin/activate && python scripts/metrics.py
```

This displays:
- Total tasks and success rate
- Today's activity
- Performance by role (implementer, reviewer, judge, etc.)
- Latency stats and fastest model
- Retry rate
- Quality metrics (judge scores, patch success, test pass rate)

### Filter by criteria

View only failed tasks:
```bash
source .venv/bin/activate && python scripts/metrics.py --failures
```

Filter by role:
```bash
source .venv/bin/activate && python scripts/metrics.py --role implementer
```

Today's events only:
```bash
source .venv/bin/activate && python scripts/metrics.py --today
```

Filter by task type:
```bash
source .venv/bin/activate && python scripts/metrics.py --type patch
```

### Understanding metrics

Show the metric reference guide with thresholds:
```bash
source .venv/bin/activate && python scripts/metrics.py --help-metrics
```

This explains what each metric means and what good/okay/bad looks like.

### Export data

Export to CSV for external analysis:
```bash
source .venv/bin/activate && python scripts/metrics.py --export csv
```

## Health Indicators

The dashboard shows colored dots for each metric:
- **Green (●)**: Good - metric is healthy
- **Yellow (●)**: Okay - metric needs attention
- **Red (●)**: Bad - metric needs investigation

| Metric | Good | Okay | Bad |
|--------|------|------|-----|
| Success Rate | >90% | 70-90% | <70% |
| Latency | <2s | 2-5s | >5s |
| Retry Rate | <10% | 10-25% | >25% |
| Judge Score | >0.8 | 0.6-0.8 | <0.6 |
| Patch Success | >85% | 60-85% | <60% |
| Test Pass Rate | >90% | 70-90% | <70% |

## Data Storage

Metrics are stored at `~/.minions/metrics.json` and collected automatically when minions run. The file is capped at 1000 events with automatic pruning.

## Troubleshooting

**No metrics recorded yet**: Run some minion tasks first (huddle, fix, swarm).

**Metrics file missing**: Check `~/.minions/` directory exists.

**High failure rate**: Check Ollama is running, models are available.

**High latency**: Use smaller models, check system resources.
