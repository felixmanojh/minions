"""Auto-bootstrap virtual environment and dependencies."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VENV_DIR = REPO_ROOT / ".venv"
REQUIREMENTS = [
    "pydantic",
    "pyyaml",
    "httpx",
    "rich",
    "diff-match-patch",
    "tqdm",
    "diskcache",
    "networkx",
]

OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_HEALTH_RETRIES = 3
OLLAMA_HEALTH_BACKOFF = 2.0  # seconds


def check_ollama_running() -> bool:
    """Check if Ollama is running and responding."""
    try:
        import httpx

        resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


def wait_for_ollama(
    retries: int = OLLAMA_HEALTH_RETRIES,
    backoff: float = OLLAMA_HEALTH_BACKOFF,
    quiet: bool = False,
) -> bool:
    """Wait for Ollama with exponential backoff.

    Args:
        retries: Number of retry attempts
        backoff: Initial backoff in seconds (doubles each retry)
        quiet: Suppress progress messages

    Returns:
        True if Ollama is running, False otherwise
    """
    for attempt in range(retries + 1):
        if check_ollama_running():
            return True

        if attempt < retries:
            wait = backoff * (2**attempt)
            if not quiet:
                print(f"[minions] Waiting for Ollama... ({wait:.1f}s)", file=sys.stderr)
            time.sleep(wait)

    return False


def get_available_models() -> list[str]:
    """Get list of models available in Ollama."""
    try:
        import httpx

        resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
        if resp.status_code == 200:
            return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        pass
    return []


def check_models_available(required: list[str]) -> tuple[list[str], list[str]]:
    """Check which required models are available.

    Args:
        required: List of model names to check

    Returns:
        Tuple of (available, missing) model lists
    """
    available_models = get_available_models()
    available = []
    missing = []

    for model in required:
        # Check exact match or prefix match
        base = model.split(":")[0]
        if any(model in m or m.startswith(base) for m in available_models):
            available.append(model)
        else:
            missing.append(model)

    return available, missing


def ensure_ollama(required_models: list[str] | None = None) -> None:
    """Ensure Ollama is running and required models are available.

    Args:
        required_models: List of model names to verify (optional)

    Raises:
        RuntimeError: If Ollama is not running or models are missing
    """
    if not wait_for_ollama():
        raise RuntimeError(
            "Ollama is not running.\nStart it with: ollama serve\nOr install: brew install ollama"
        )

    if required_models:
        available, missing = check_models_available(required_models)
        if missing:
            raise RuntimeError(
                f"Missing models: {', '.join(missing)}\nPull with: ollama pull {missing[0]}"
            )


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
