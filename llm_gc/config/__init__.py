"""Configuration helpers for Local Multi LLM orchestrator."""

from __future__ import annotations

import os
from dataclasses import dataclass
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


@dataclass
class ValidationConfig:
    """Configuration for validation behavior."""
    max_retries: int = 1
    notify_on_fail: bool = True


@dataclass
class MinionConfigs:
    """Combined minion and validator configs."""
    minion: ModelConfig
    validator: ModelConfig | None  # None means use minion model
    validation: ValidationConfig


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
    """Get num_ctx from environment variable if set."""
    env_val = os.environ.get("MINIONS_NUM_CTX")
    if env_val:
        try:
            return int(env_val)
        except ValueError:
            return None
    return None


def get_minion_config(preset: str | None = None) -> ModelConfig:
    """Get the single minion model config.

    Supports environment overrides:
        MINIONS_MODEL - override model name
        MINIONS_NUM_CTX - override context window

    Returns:
        ModelConfig for the minion.
    """
    configs = load_models(preset=preset)
    config = configs.get("minion") or next(iter(configs.values()))

    # Apply environment overrides
    model_override = os.environ.get("MINIONS_MODEL")
    ctx_override = get_num_ctx_override()

    if model_override or ctx_override:
        return ModelConfig(
            model=model_override or config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            num_ctx=ctx_override or config.num_ctx,
            seed=config.seed,
        )
    return config


def get_configs(preset: str | None = None, path: str | Path | None = None) -> MinionConfigs:
    """Get both minion and validator configs.

    Supports environment overrides:
        MINIONS_MODEL - override minion model
        MINIONS_VALIDATOR - override validator model
        MINIONS_NUM_CTX - override context window

    Returns:
        MinionConfigs with minion, validator, and validation settings.
    """
    default_path = Path(__file__).with_name("models.yaml")
    config_path = Path(path) if path else default_path

    data = yaml.safe_load(config_path.read_text()) or {}

    # Load validation config
    val_cfg = data.get("validation", {})
    validation = ValidationConfig(
        max_retries=val_cfg.get("max_retries", 1),
        notify_on_fail=val_cfg.get("notify_on_fail", True),
    )

    # Determine which preset to use
    env_preset = os.environ.get("MINIONS_PRESET")
    active_preset = env_preset or preset or data.get("preset")

    presets = data.get("presets", {})
    preset_config = presets.get(active_preset, {})

    # Get minion config
    minion_cfg = preset_config.get("minion", {})
    if not minion_cfg:
        raise ValueError(f"No minion config in preset '{active_preset}'")

    minion = ModelConfig(**minion_cfg)

    # Apply minion environment overrides
    model_override = os.environ.get("MINIONS_MODEL")
    ctx_override = get_num_ctx_override()
    if model_override or ctx_override:
        minion = ModelConfig(
            model=model_override or minion.model,
            temperature=minion.temperature,
            max_tokens=minion.max_tokens,
            num_ctx=ctx_override or minion.num_ctx,
            seed=minion.seed,
        )

    # Get validator config
    validator_cfg = preset_config.get("validator")
    validator: ModelConfig | None = None

    if validator_cfg == "same":
        # Use minion model for validation
        validator = None
    elif isinstance(validator_cfg, dict):
        validator = ModelConfig(**validator_cfg)

        # Apply validator environment overrides
        validator_override = os.environ.get("MINIONS_VALIDATOR")
        if validator_override:
            validator = ModelConfig(
                model=validator_override,
                temperature=validator.temperature,
                max_tokens=validator.max_tokens,
                num_ctx=validator.num_ctx,
                seed=validator.seed,
            )

    return MinionConfigs(minion=minion, validator=validator, validation=validation)


def get_validator_config(configs: MinionConfigs) -> ModelConfig:
    """Get the effective validator config (uses minion if validator is None)."""
    if configs.validator is not None:
        return configs.validator
    # Use minion config but with lower temperature for validation
    return ModelConfig(
        model=configs.minion.model,
        temperature=0.1,
        max_tokens=400,
        num_ctx=configs.minion.num_ctx,
        seed=configs.minion.seed,
    )


__all__ = [
    "ModelConfig",
    "ValidationConfig",
    "MinionConfigs",
    "load_models",
    "available_presets",
    "get_num_ctx_override",
    "get_minion_config",
    "get_configs",
    "get_validator_config",
]
