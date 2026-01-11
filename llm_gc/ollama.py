"""Helpers for configuring Ollama endpoints."""

from __future__ import annotations

import os
from functools import lru_cache

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


@lru_cache(maxsize=1)
def get_ollama_base_url() -> str:
    """Return the Ollama base URL, honoring OLLAMA_BASE_URL env var."""

    value = os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL).strip()
    if value.endswith("/"):
        value = value[:-1]
    return value or DEFAULT_OLLAMA_URL


__all__ = ["DEFAULT_OLLAMA_URL", "get_ollama_base_url"]
