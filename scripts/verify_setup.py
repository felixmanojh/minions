#!/usr/bin/env python3
"""
Minions Setup Verification

Quick diagnostic tool to check if everything is configured correctly.
Run from anywhere: python ~/.local/share/minions/scripts/verify_setup.py
"""

import os
import sys
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from llm_gc.ollama import get_ollama_base_url

OLLAMA_BASE_URL = get_ollama_base_url()


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"  {Colors.GREEN}✓{Colors.RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {Colors.RED}✗{Colors.RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {Colors.YELLOW}!{Colors.RESET} {msg}")


def info(msg: str) -> None:
    print(f"  {Colors.BLUE}i{Colors.RESET} {msg}")


def check_command(cmd: str) -> bool:
    """Check if a command exists."""
    result = subprocess.run(
        ["which", cmd],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def check_ollama_running() -> bool:
    """Check if Ollama daemon is responding."""
    try:
        import httpx

        resp = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def get_ollama_models() -> list[str]:
    """Get list of installed Ollama models."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        # Parse model names from output
        lines = result.stdout.strip().split("\n")[1:]  # Skip header
        return [line.split()[0] for line in lines if line.strip()]
    except Exception:
        return []


def find_minions_dir() -> Path | None:
    """Find the minions installation directory."""
    candidates = [
        Path.home() / ".local" / "share" / "minions",
        Path.home() / ".claude" / "plugins" / "minions",
        Path.home() / "minions",
        Path.cwd(),
    ]

    for path in candidates:
        if (path / "llm_gc" / "__init__.py").exists():
            return path
    return None


def check_venv(minions_dir: Path) -> bool:
    """Check if venv exists and has required packages."""
    venv_path = minions_dir / ".venv"
    if not venv_path.exists():
        return False

    # Try to check for packages
    python_path = venv_path / "bin" / "python"
    if not python_path.exists():
        return False

    result = subprocess.run(
        [str(python_path), "-c", "import httpx, pydantic, rich, yaml"],
        capture_output=True,
    )
    return result.returncode == 0


def check_skills_linked() -> dict[str, bool]:
    """Check which skills are symlinked."""
    skills_dir = Path.home() / ".claude" / "skills"
    skills = ["minion-fix", "minion-check", "minion-swarm", "minion-metrics", "minion-setup"]

    results = {}
    for skill in skills:
        skill_path = skills_dir / skill
        results[skill] = skill_path.is_symlink() or skill_path.is_dir()

    return results


def main():
    print()
    print(f"{Colors.BLUE}=== Minions Setup Verification ==={Colors.RESET}")
    print()

    all_ok = True

    # 1. Ollama installation
    print("Ollama:")
    if check_command("ollama"):
        ok("Ollama is installed")
    else:
        fail("Ollama is not installed")
        info("Install: brew install ollama (macOS) or curl -fsSL https://ollama.com/install.sh | sh (Linux)")
        all_ok = False

    # 2. Ollama daemon
    if check_ollama_running():
        ok("Ollama daemon is running")
    else:
        fail("Ollama daemon is not running")
        info("Start: ollama serve")
        all_ok = False

    # 3. Models
    print()
    print("Models:")
    models = get_ollama_models()
    required = {
        "qwen2.5-coder": "Implementer model (ollama pull qwen2.5-coder:1.5b)",
        "deepseek-coder": "Reviewer model (ollama pull deepseek-coder:1.3b)",
    }

    for model_prefix, description in required.items():
        found = any(m.startswith(model_prefix) for m in models)
        if found:
            ok(f"{model_prefix} available")
        else:
            fail(f"{model_prefix} missing")
            info(f"Pull: {description}")
            all_ok = False

    # 4. Minions directory
    print()
    print("Installation:")
    minions_dir = find_minions_dir()
    if minions_dir:
        ok(f"Minions found at {minions_dir}")

        # Check venv
        if check_venv(minions_dir):
            ok("Virtual environment configured")
        else:
            fail("Virtual environment missing or incomplete")
            info(f"Setup: cd {minions_dir} && python3 -m venv .venv && source .venv/bin/activate && pip install httpx pydantic pyyaml rich diff-match-patch")
            all_ok = False
    else:
        fail("Minions installation not found")
        info("Clone: git clone https://github.com/felixmanojh/minions.git ~/.local/share/minions")
        all_ok = False

    # 5. Skills
    print()
    print("Skills:")
    skills_status = check_skills_linked()
    for skill, linked in skills_status.items():
        if linked:
            ok(f"{skill} linked")
        else:
            warn(f"{skill} not linked")
            if minions_dir:
                info(f"Link: ln -sf {minions_dir}/skills/{skill} ~/.claude/skills/{skill}")

    # Summary
    print()
    print("=" * 36)
    if all_ok:
        print(f"{Colors.GREEN}All checks passed! Minions ready.{Colors.RESET}")
        print()
        print("Try: /minion-fix or /minion-swarm")
    else:
        print(f"{Colors.YELLOW}Some issues found. See above for fixes.{Colors.RESET}")

    print()
    return 0 if all_ok else 1


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from llm_gc.ollama import get_ollama_base_url

OLLAMA_BASE_URL = get_ollama_base_url()
...
if __name__ == "__main__":
    sys.exit(main())
