"""Shared helpers for the minimal orchestrator."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from time import perf_counter

import httpx
from rich.console import Console

from llm_gc.config import ModelConfig
from llm_gc.ollama import get_ollama_base_url

console = Console()


@dataclass
class ChatTurn:
    """Represents a single agent response."""

    role: str
    content: str
    latency_ms: float
    token_estimate: int
    model: str
    round_index: int

    def to_dict(self) -> dict:
        return asdict(self)


class OllamaClient:
    """Thin wrapper around the Ollama HTTP API."""

    def __init__(self, base_url: str | None = None, timeout: float = 30.0) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url or get_ollama_base_url(), timeout=timeout
        )

    async def prompt(self, prompt: str, config: ModelConfig) -> tuple[str, float]:
        payload = {
            "model": config.model,
            "prompt": prompt,
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
            },
            "stream": False,
        }
        start = perf_counter()
        response = await self._client.post("/api/generate", json=payload)
        latency_ms = (perf_counter() - start) * 1000
        response.raise_for_status()
        data = response.json()
        text = (data.get("response") or "").strip()
        return text, latency_ms


def render_turn(turn: ChatTurn) -> None:
    """Pretty-print a chat turn."""

    console.rule(f"{turn.role}")
    console.print(turn.content)
    console.print(
        f"[dim]{turn.model} | {turn.latency_ms:.0f} ms | ~{turn.token_estimate} tokens | round {turn.round_index + 1}[/dim]"
    )


def persist_transcript(
    *,
    task: str,
    turns: Iterable[ChatTurn],
    summary: str,
    output_dir: Path,
    metadata: dict | None = None,
) -> Path:
    """Write transcript JSON to disk."""

    output_dir.mkdir(parents=True, exist_ok=True)

    data = {
        "task": task,
        "summary": summary,
        "turns": [t.to_dict() for t in turns],
    }
    if metadata:
        data["metadata"] = metadata

    timestamp_name = (metadata or {}).get("session_id")
    if not timestamp_name:
        timestamp_name = datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    path = output_dir / f"{timestamp_name}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return path


__all__ = ["ChatTurn", "OllamaClient", "persist_transcript", "render_turn"]
