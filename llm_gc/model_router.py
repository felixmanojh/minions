"""Model router - infer role from task and pick the right model.

Role mapping:
  • Implementer: write new code, refactor, add tests, add docs
  • Reviewer: find bugs, security issues, edge cases, correctness
  • Patcher: minimal diffs, apply patch, FIM edits, surgical fixes
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

ROLE_IMPLEMENTER = "implementer"
ROLE_REVIEWER = "reviewer"
ROLE_PATCHER = "patcher"

# Diff markers that indicate patcher intent
DIFF_MARKERS = [
    "diff --git",
    "@@",
    "+++ b/",
    "--- a/",
    "+++ ",
    "--- ",
]

# File extensions that suggest patcher when combined with action words
CODE_EXTENSIONS = [
    ".py",
    ".ts",
    ".js",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".swift",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".rb",
    ".php",
    ".cs",
    ".scala",
]

# Signals that strengthen patcher intent
PATCHER_SIGNALS = [
    "minimal change",
    "smallest change",
    "one line",
    "single line",
    "this line",
    "just change",
    "only change",
]


@dataclass(frozen=True)
class RoleModels:
    primary: str
    fallbacks: list[str]


@dataclass(frozen=True)
class RoutingRules:
    patcher_keywords: list[str]
    reviewer_keywords: list[str]
    implementer_keywords: list[str]


@dataclass(frozen=True)
class ModelConfig:
    preset: str
    roles: dict[str, RoleModels]
    routing: RoutingRules


def load_model_config(path: str | Path | None = None) -> ModelConfig:
    """Load model configuration from YAML file."""
    if path is None:
        path = Path(__file__).parent / "config" / "models.yaml"

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    roles: dict[str, RoleModels] = {}
    for role, cfg in data.get("roles", {}).items():
        roles[role] = RoleModels(
            primary=str(cfg["primary"]),
            fallbacks=[str(x) for x in cfg.get("fallbacks", [])],
        )

    routing_raw = data.get("routing", {})
    routing = RoutingRules(
        patcher_keywords=[str(x).lower() for x in routing_raw.get("patcher_keywords", [])],
        reviewer_keywords=[str(x).lower() for x in routing_raw.get("reviewer_keywords", [])],
        implementer_keywords=[str(x).lower() for x in routing_raw.get("implementer_keywords", [])],
    )

    return ModelConfig(
        preset=str(data.get("preset", "medium")),
        roles=roles,
        routing=routing,
    )


def _has_diff_markers(text: str) -> bool:
    """Check if text contains unified diff markers."""
    return any(marker in text for marker in DIFF_MARKERS)


def _has_file_reference(text: str) -> bool:
    """Check if text references a specific file."""
    return any(ext in text.lower() for ext in CODE_EXTENSIONS)


def _has_patcher_signals(text: str) -> bool:
    """Check for phrases that suggest minimal/surgical changes."""
    text_lower = text.lower()
    return any(signal in text_lower for signal in PATCHER_SIGNALS)


def _handle_fix_keyword(text: str, rules: RoutingRules) -> str | None:
    """Smart handling of 'fix' which is ambiguous.

    Rules:
      - fix + patch signals or file or diff markers → patcher
      - fix + bug or error or failing → reviewer
      - else → None (let other logic decide)
    """
    text_lower = text.lower()

    if "fix" not in text_lower:
        return None

    # fix + patcher signals → patcher
    if _has_diff_markers(text) or _has_patcher_signals(text):
        return ROLE_PATCHER

    # fix + file reference with action words → patcher
    if _has_file_reference(text) and any(w in text_lower for w in ["this", "line", "change"]):
        return ROLE_PATCHER

    # fix + bug/error/failing → reviewer
    reviewer_signals = ["bug", "error", "failing", "broken", "issue", "wrong"]
    if any(signal in text_lower for signal in reviewer_signals):
        return ROLE_REVIEWER

    # Ambiguous fix → let other logic decide
    return None


def infer_role(user_request: str, rules: RoutingRules) -> str:
    """Infer the best role based on keywords and patterns.

    Priority: Patcher > Reviewer > Implementer (default)
    """
    text = user_request.lower().strip()

    # Check for diff markers first (strong patcher signal)
    if _has_diff_markers(user_request):
        return ROLE_PATCHER

    # Handle ambiguous 'fix' keyword
    fix_role = _handle_fix_keyword(user_request, rules)
    if fix_role:
        return fix_role

    # Check for patcher signals
    if _has_patcher_signals(text):
        return ROLE_PATCHER

    # Patcher keywords
    if any(k in text for k in rules.patcher_keywords):
        return ROLE_PATCHER

    # Reviewer keywords
    if any(k in text for k in rules.reviewer_keywords):
        return ROLE_REVIEWER

    # Implementer keywords
    if any(k in text for k in rules.implementer_keywords):
        return ROLE_IMPLEMENTER

    # Default: implementer
    return ROLE_IMPLEMENTER


def apply_env_override(role: str, candidates: list[str]) -> list[str]:
    """Apply environment variable overrides for model selection.

    Supports:
        MINIONS_IMPLEMENTER_MODEL
        MINIONS_REVIEWER_MODEL
        MINIONS_PATCHER_MODEL

    Override goes first, original candidates follow as fallbacks.
    """
    env_map = {
        ROLE_IMPLEMENTER: "MINIONS_IMPLEMENTER_MODEL",
        ROLE_REVIEWER: "MINIONS_REVIEWER_MODEL",
        ROLE_PATCHER: "MINIONS_PATCHER_MODEL",
    }
    key = env_map.get(role)
    if not key:
        return candidates
    val = os.getenv(key, "").strip()
    if not val:
        return candidates
    # Put override first, keep original ordering behind it
    return [val] + [m for m in candidates if m != val]


def choose_model_for_role(role: str, cfg: ModelConfig) -> str:
    """Get the primary model for a role."""
    if role not in cfg.roles:
        role = ROLE_IMPLEMENTER
    return cfg.roles[role].primary


def choose_model_candidates_for_role(role: str, cfg: ModelConfig) -> list[str]:
    """Get all model candidates for a role (primary + fallbacks)."""
    if role not in cfg.roles:
        role = ROLE_IMPLEMENTER
    rm = cfg.roles[role]
    return [rm.primary] + list(rm.fallbacks)


def validate_model_available(model: str) -> bool:
    """Check if a model is available locally in Ollama."""
    try:
        import httpx

        resp = httpx.get("http://127.0.0.1:11434/api/tags", timeout=5.0)
        if resp.status_code != 200:
            return False
        data = resp.json()
        available = [m["name"] for m in data.get("models", [])]
        # Check exact match or prefix match (qwen2.5-coder:7b matches qwen2.5-coder:7b-instruct)
        return any(model in name or name.startswith(model.split(":")[0]) for name in available)
    except Exception:
        return False


def validate_models(candidates: list[str]) -> tuple[list[str], list[str]]:
    """Validate which models are available locally.

    Returns:
        Tuple of (available_models, missing_models)
    """
    available = []
    missing = []
    for model in candidates:
        if validate_model_available(model):
            available.append(model)
        else:
            missing.append(model)
    return available, missing


def route(user_request: str, cfg_path: str | Path | None = None) -> tuple[str, list[str]]:
    """Route a user request to a role and return model candidates.

    Args:
        user_request: The task description
        cfg_path: Path to models.yaml (optional)

    Returns:
        Tuple of (role, model_candidates)
    """
    cfg = load_model_config(cfg_path)
    role = infer_role(user_request, cfg.routing)
    candidates = choose_model_candidates_for_role(role, cfg)
    candidates = apply_env_override(role, candidates)
    return role, candidates


def route_with_validation(
    user_request: str,
    cfg_path: str | Path | None = None,
    log: bool = True,
) -> tuple[str, str, list[str]]:
    """Route and validate models, with optional logging.

    Args:
        user_request: The task description
        cfg_path: Path to models.yaml (optional)
        log: Whether to print role/model info

    Returns:
        Tuple of (role, selected_model, all_candidates)

    Raises:
        RuntimeError: If no models are available
    """
    role, candidates = route(user_request, cfg_path)
    available, missing = validate_models(candidates)

    if log:
        print(
            f"Role: {role.capitalize()}, Model: {available[0] if available else 'NONE'}",
            file=sys.stderr,
        )

    if not available:
        missing_str = ", ".join(missing)
        raise RuntimeError(
            f"No models available for {role}. Missing: {missing_str}\n"
            f"Run: ollama pull {missing[0]}\n"
            f"Or run: ./install.sh"
        )

    if missing and log:
        print(f"  (fallbacks missing: {', '.join(missing)})", file=sys.stderr)

    return role, available[0], candidates


def route_explicit(role: str, cfg_path: str | Path | None = None) -> list[str]:
    """Get model candidates for an explicit role.

    Args:
        role: One of "implementer", "reviewer", "patcher"
        cfg_path: Path to models.yaml (optional)

    Returns:
        List of model candidates
    """
    cfg = load_model_config(cfg_path)
    candidates = choose_model_candidates_for_role(role, cfg)
    return apply_env_override(role, candidates)


__all__ = [
    "ROLE_IMPLEMENTER",
    "ROLE_REVIEWER",
    "ROLE_PATCHER",
    "ModelConfig",
    "RoleModels",
    "RoutingRules",
    "load_model_config",
    "infer_role",
    "apply_env_override",
    "choose_model_for_role",
    "choose_model_candidates_for_role",
    "validate_model_available",
    "validate_models",
    "route",
    "route_with_validation",
    "route_explicit",
]
