#!/usr/bin/env python3
"""Unified minions CLI - single entry point for all minion commands.

Usage:
    minions polish <files> --task <task>    # Auto-apply docstrings/types
    minions sweep <dir> --task <task>       # Discover + batch fix
    minions patch <task> --target <file>    # Generate patch for review
    minions chat <task>                     # Single-shot minion task
    minions swarm <task> <files>            # Parallel patches
    minions setup                           # Verify Ollama and models
    minions metrics                         # View session stats
"""

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
import asyncio
import json


def cmd_polish(args):
    """Auto-apply docstrings, types, comments."""
    from scripts.m_polish import run_polish

    result = asyncio.run(run_polish(
        files=[Path(f) for f in args.files],
        task=args.task,
        preset=args.preset,
        num_ctx=args.num_ctx,
        backup=args.backup,
        dry_run=args.dry_run,
    ))

    if args.json:
        print(json.dumps(result, indent=2))
    return 0 if result.get("applied") else 1


def cmd_sweep(args):
    """Scan codebase and batch-fix."""
    from scripts.m_sweep import run_sweep

    result = asyncio.run(run_sweep(
        directory=Path(args.directory),
        task=args.task,
        apply=args.apply,
        max_lines=args.max_lines,
        preset=args.preset,
        num_ctx=args.num_ctx,
        backup=args.backup,
    ))

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\nCandidates: {result['total_candidates']}")
        if args.apply and "stats" in result:
            print(f"Applied: {result['stats']['applied']}/{result['stats']['total']}")
    return 0


def cmd_patch(args):
    """Generate patch for manual review."""
    from llm_gc.orchestrator.m3_patch import run_patch
    from llm_gc.skill import parse_read_requests

    read_requests = parse_read_requests(args.read or [])
    result = asyncio.run(run_patch(
        task=args.task,
        preset=args.preset,
        config_path=args.config,
        session_dir=Path(args.sessions),
        repo_root=Path(args.repo_root),
        read_requests=read_requests,
        target_files=args.target or [],
    ))

    if args.json:
        print(json.dumps({
            "task": args.task,
            "patch_path": str(result.get("patch_path")) if result.get("patch_path") else None,
            "summary": result.get("summary", ""),
        }, indent=2))
    else:
        if result.get("patch_path"):
            print(f"Patch saved: {result['patch_path']}")
        else:
            print("No patch generated")
    return 0 if result.get("patch_path") else 1


def cmd_chat(args):
    """Single-shot minion task."""
    from llm_gc.orchestrator.m1_chat import run_chat
    from llm_gc.skill import parse_read_requests

    read_requests = parse_read_requests(args.read or [])
    result = asyncio.run(run_chat(
        task=args.task,
        preset=args.preset,
        config_path=args.config,
        session_dir=Path(args.sessions),
        repo_root=Path(args.repo_root),
        read_requests=read_requests,
        num_ctx=args.num_ctx,
    ))

    if args.json:
        print(json.dumps({
            "task": args.task,
            "summary": result.get("summary", ""),
            "model": result.get("model"),
        }, indent=2))
    return 0


def cmd_swarm(args):
    """Parallel patches on multiple files."""
    from llm_gc.swarm import Swarm

    swarm = Swarm(
        workers=args.workers,
        max_retries=args.retries,
        repo_root=str(args.repo_root),
    )

    for f in args.files:
        swarm.add_patch(
            description=args.task,
            target=f,
            context_files=[f],
        )

    results = asyncio.run(swarm.run())

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        stats = results["stats"]
        print(f"Completed: {stats['completed']}/{stats['total']}")
    return 0 if results["stats"]["failed"] == 0 else 1


def cmd_setup(args):
    """Verify Ollama and models."""
    import subprocess

    print("Checking Ollama...")
    try:
        result = subprocess.run(
            ["curl", "-s", "http://127.0.0.1:11434/api/tags"],
            capture_output=True, timeout=5
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            models = [m["name"] for m in data.get("models", [])]
            print(f"✓ Ollama running with {len(models)} models")
            for m in models[:5]:
                print(f"  - {m}")
            if len(models) > 5:
                print(f"  ... and {len(models) - 5} more")
        else:
            print("✗ Ollama not responding")
            return 1
    except Exception as e:
        print(f"✗ Ollama check failed: {e}")
        return 1

    print("\nChecking config...")
    from llm_gc.config import load_models
    try:
        models = load_models()
        print(f"✓ Config loaded: {len(models)} roles")
        for role, cfg in models.items():
            print(f"  - {role}: {cfg.model} (ctx: {cfg.num_ctx})")
    except Exception as e:
        print(f"✗ Config error: {e}")
        return 1

    print("\n✓ Setup OK")
    return 0


def cmd_metrics(args):
    """View session stats."""
    from llm_gc.metrics import get_metrics, format_summary

    metrics = get_metrics(limit=args.limit)
    if args.json:
        print(json.dumps(metrics, indent=2, default=str))
    else:
        print(format_summary(metrics))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Minions - Local LLM helpers for code tasks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--json", action="store_true", help="JSON output")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # polish
    p_polish = subparsers.add_parser("polish", help="Auto-apply docstrings/types")
    p_polish.add_argument("files", nargs="+", help="Files to polish")
    p_polish.add_argument("--task", default="all", help="Task: docstrings, types, headers, all")
    p_polish.add_argument("--preset", choices=["lite", "medium", "large"])
    p_polish.add_argument("--num-ctx", type=int, help="Context window size")
    p_polish.add_argument("--backup", action="store_true", help="Create .bak files")
    p_polish.add_argument("--dry-run", action="store_true", help="Preview only")
    p_polish.set_defaults(func=cmd_polish)

    # sweep
    p_sweep = subparsers.add_parser("sweep", help="Scan codebase for missing docs")
    p_sweep.add_argument("directory", help="Directory to sweep")
    p_sweep.add_argument("--task", default="all", choices=["docstrings", "types", "headers", "all"])
    p_sweep.add_argument("--apply", action="store_true", help="Apply fixes")
    p_sweep.add_argument("--max-lines", type=int, default=500, help="Skip files over N lines")
    p_sweep.add_argument("--preset", choices=["lite", "medium", "large"])
    p_sweep.add_argument("--num-ctx", type=int, help="Context window size")
    p_sweep.add_argument("--backup", action="store_true", help="Create .bak files")
    p_sweep.set_defaults(func=cmd_sweep)

    # patch
    p_patch = subparsers.add_parser("patch", help="Generate patch for review")
    p_patch.add_argument("task", help="Task description")
    p_patch.add_argument("--target", action="append", help="Target file(s)")
    p_patch.add_argument("--read", action="append", help="Context file(s)")
    p_patch.add_argument("--preset", choices=["lite", "medium", "large"])
    p_patch.add_argument("--config", type=Path, help="Config file")
    p_patch.add_argument("--sessions", default="sessions", help="Session dir")
    p_patch.add_argument("--repo-root", type=Path, default=Path.cwd())
    p_patch.set_defaults(func=cmd_patch)

    # chat
    p_chat = subparsers.add_parser("chat", help="Single-shot minion task")
    p_chat.add_argument("task", help="Task description")
    p_chat.add_argument("--read", action="append", help="Context file(s)")
    p_chat.add_argument("--preset", choices=["lite", "medium", "large"])
    p_chat.add_argument("--num-ctx", type=int, help="Context window size")
    p_chat.add_argument("--config", type=Path, help="Config file")
    p_chat.add_argument("--sessions", default="sessions", help="Session dir")
    p_chat.add_argument("--repo-root", type=Path, default=Path.cwd())
    p_chat.set_defaults(func=cmd_chat)

    # swarm
    p_swarm = subparsers.add_parser("swarm", help="Parallel patches")
    p_swarm.add_argument("task", help="Task description")
    p_swarm.add_argument("files", nargs="+", help="Target files")
    p_swarm.add_argument("--workers", type=int, default=3, help="Parallel workers")
    p_swarm.add_argument("--retries", type=int, default=2, help="Max retries")
    p_swarm.add_argument("--repo-root", type=Path, default=Path.cwd())
    p_swarm.set_defaults(func=cmd_swarm)

    # setup
    p_setup = subparsers.add_parser("setup", help="Verify Ollama and models")
    p_setup.set_defaults(func=cmd_setup)

    # metrics
    p_metrics = subparsers.add_parser("metrics", help="View session stats")
    p_metrics.add_argument("--limit", type=int, default=50, help="Max events")
    p_metrics.set_defaults(func=cmd_metrics)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
