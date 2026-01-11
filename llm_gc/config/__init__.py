"""Configuration helpers for Local Multi LLM orchestrator."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ModelConfig(BaseModel):
    """Model configuration sourced from YAML."""

    model: str
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(512, gt=0)
    num_ctx: int = Field(8192, gt=0)  # context window size
    seed: int | None = None


def load_models(
    path: str | Path | None = None,
    preset: str | None = None,
) -> dict[str, ModelConfig]:
    """Load model configs from YAML file.

    Supports presets (nano, small, medium, large) and custom model definitions.

    Priority:
        1. Environment variable MINIONS_PRESET overrides preset
        2. preset parameter overrides yaml preset
        3. Custom role definitions override preset roles

    Args:
        path: Optional override path. Defaults to `llm_gc/config/models.yaml`.
        preset: Optional preset name (nano, small, medium, large).

    Returns:
        Mapping of role -> ModelConfig.
    """

    default_path = Path(__file__).with_name("models.yaml")
    config_path = Path(path) if path else default_path
    if not config_path.exists():
        raise FileNotFoundError(f"Model config not found: {config_path}")

    data = yaml.safe_load(config_path.read_text()) or {}

    # Determine which preset to use
    env_preset = os.environ.get("MINIONS_PRESET")
    active_preset = env_preset or preset or data.get("preset")

    presets = data.get("presets", {})

    # Start with preset config if available
    role_configs: dict[str, dict] = {}
    if active_preset and active_preset in presets:
        role_configs = dict(presets[active_preset])

    # Override with any custom role definitions (not 'preset' or 'presets' keys)
    for key, value in data.items():
        if key not in ("preset", "presets") and isinstance(value, dict) and "model" in value:
            role_configs[key] = value

    return {role: ModelConfig(**cfg) for role, cfg in role_configs.items()}


def available_presets(path: str | Path | None = None) -> list[str]:
    """List available preset names."""
    default_path = Path(__file__).with_name("models.yaml")
    config_path = Path(path) if path else default_path
    if not config_path.exists():
        return []

    data = yaml.safe_load(config_path.read_text()) or {}
    return list(data.get("presets", {}).keys())


def get_num_ctx_override() -> int | None:
    """Get num_ctx from environment variable if set.

    Returns:
        num_ctx value from MINIONS_NUM_CTX env var, or None if not set.
    """
    env_val = os.environ.get("MINIONS_NUM_CTX")
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            return None
    return None


__all__ = ["ModelConfig", "load_models", "available_presets", "get_num_ctx_override"]
