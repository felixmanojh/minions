#!/usr/bin/env python3
"""CLI for banana stats 🍌 - Track your minion productivity!"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Auto-bootstrap venv and dependencies
from llm_gc.bootstrap import ensure_venv
ensure_venv()

import argparse
from llm_gc.bananas import format_stats, get_stats, add_bananas


def main() -> None:
    parser = argparse.ArgumentParser(
        description="🍌 Banana Stats - Track your minion productivity!"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output JSON"
    )
    parser.add_argument(
        "--add", type=int, help="Manually add bananas (for testing)"
    )
    args = parser.parse_args()

    if args.add:
        add_bananas(args.add, task_type="manual")
        print(f"🍌 Added {args.add} bananas!")

    if args.json:
        import json
        print(json.dumps(get_stats(), indent=2))
    else:
        print(format_stats())


if __name__ == "__main__":
    main()
