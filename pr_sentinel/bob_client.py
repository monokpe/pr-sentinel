"""
Bob 2.0 client — thin wrapper around the local Bob API.

All inference calls go through this module.  Nothing is sent to any
external service; Bob runs locally via Bob Desktop.
"""
from __future__ import annotations

import os
import json
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

_BOB_API_URL = os.getenv("BOB_API_URL", "http://localhost:11434")
_BOB_MODEL = os.getenv("BOB_MODEL", "bob2")
_TIMEOUT = 120.0  # seconds — local inference can be slow on first call


def _endpoint(path: str) -> str:
    return f"{_BOB_API_URL.rstrip('/')}{path}"


def chat(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.2,
    extra: dict[str, Any] | None = None,
) -> str:
    """
    Send a chat request to the local Bob instance and return the
    assistant's text response.

    Parameters
    ----------
    messages:
        OpenAI-compatible message list, e.g.
        ``[{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]``
    model:
        Override the default model from ``BOB_MODEL`` env var.
    temperature:
        Sampling temperature (lower = more deterministic).
    extra:
        Any additional fields to merge into the request body.
    """
    payload: dict[str, Any] = {
        "model": model or _BOB_MODEL,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    if extra:
        payload.update(extra)

    with httpx.Client(timeout=_TIMEOUT) as client:
        response = client.post(_endpoint("/api/chat"), json=payload)
        response.raise_for_status()
        data = response.json()

    # Bob Desktop (Ollama-compatible) response shape
    return data.get("message", {}).get("content", "") or data.get("response", "")


def is_available() -> bool:
    """Return True if the local Bob instance is reachable."""
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(_endpoint("/api/tags"))
            return r.status_code < 400
    except Exception:
        return False
