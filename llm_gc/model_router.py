"""Model router - infer role from task and pick the right model."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import yaml


ROLE_IMPLEMENTER = "implementer"
ROLE_REVIEWER = "reviewer"
ROLE_PATCHER = "patcher"


@dataclass(frozen=True)
class RoleModels:
    primary: str
    fallbacks: List[str]


@dataclass(frozen=True)
class RoutingRules:
    patcher_keywords: List[str]
    reviewer_keywords: List[str]
    implementer_keywords: List[str]


@dataclass(frozen=True)
class ModelConfig:
    preset: str
    roles: Dict[str, RoleModels]
    routing: RoutingRules


def load_model_config(path: str | Path | None = None) -> ModelConfig:
    """Load model configuration from YAML file."""
    if path is None:
        path = Path(__file__).parent / "config" / "models.yaml"

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))

    roles: Dict[str, RoleModels] = {}
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


def infer_role(user_request: str, rules: RoutingRules) -> str:
    """Infer the best role based on keywords in the user request.

    Priority: Patcher > Reviewer > Implementer (default)
    """
    text = user_request.lower().strip()

    # Patcher first: surgical edits should override other intents
    if any(k in text for k in rules.patcher_keywords):
        return ROLE_PATCHER

    # Reviewer next
    if any(k in text for k in rules.reviewer_keywords):
        return ROLE_REVIEWER

    # Implementer last (also the default)
    if any(k in text for k in rules.implementer_keywords):
        return ROLE_IMPLEMENTER

    # Default: implementer
    return ROLE_IMPLEMENTER


def apply_env_override(role: str, candidates: List[str]) -> List[str]:
    """Apply environment variable overrides for model selection.

    Supports:
        MINIONS_IMPLEMENTER_MODEL
        MINIONS_REVIEWER_MODEL
        MINIONS_PATCHER_MODEL
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
    # Put override first, keep rest as fallback
    return [val] + [m for m in candidates if m != val]


def choose_model_for_role(role: str, cfg: ModelConfig) -> str:
    """Get the primary model for a role."""
    if role not in cfg.roles:
        role = ROLE_IMPLEMENTER
    return cfg.roles[role].primary


def choose_model_candidates_for_role(role: str, cfg: ModelConfig) -> List[str]:
    """Get all model candidates for a role (primary + fallbacks)."""
    if role not in cfg.roles:
        role = ROLE_IMPLEMENTER
    rm = cfg.roles[role]
    return [rm.primary] + list(rm.fallbacks)


def route(user_request: str, cfg_path: str | Path | None = None) -> Tuple[str, List[str]]:
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


def route_explicit(role: str, cfg_path: str | Path | None = None) -> List[str]:
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
    "route",
    "route_explicit",
]
