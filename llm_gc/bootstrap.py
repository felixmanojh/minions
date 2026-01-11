"""Auto-bootstrap virtual environment and dependencies."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = REPO_ROOT / ".venv"
REQUIREMENTS = ["pydantic", "pyyaml", "httpx", "rich", "diff-match-patch"]


def ensure_venv() -> None:
    """Ensure virtual environment exists and dependencies are installed."""
    # Skip if already in a venv
    if sys.prefix != sys.base_prefix:
        return

    # Check if our venv exists and has pip
    venv_python = VENV_DIR / "bin" / "python"
    if not venv_python.exists():
        print("[minions] Creating virtual environment...", file=sys.stderr)
        subprocess.run([sys.executable, "-m", "venv", str(VENV_DIR)], check=True)

    # Check if dependencies are installed
    try:
        result = subprocess.run(
            [str(venv_python), "-c", "import pydantic, yaml, httpx, rich"],
            capture_output=True,
        )
        if result.returncode == 0:
            # Dependencies exist, re-exec with venv python
            os.execv(str(venv_python), [str(venv_python)] + sys.argv)
    except Exception:
        pass

    # Install dependencies
    print("[minions] Installing dependencies...", file=sys.stderr)
    pip = VENV_DIR / "bin" / "pip"
    subprocess.run(
        [str(pip), "install", "--quiet"] + REQUIREMENTS,
        check=True,
    )
    print("[minions] Setup complete!", file=sys.stderr)

    # Re-exec with venv python
    os.execv(str(venv_python), [str(venv_python)] + sys.argv)
