"""
Shared utilities for PR Sentinel agents.
"""
from __future__ import annotations

import json
import re


def extract_json(text: str) -> dict:
    """
    Robustly extract a JSON object from an LLM response.

    Handles the common cases where the model:
    - Wraps JSON in a markdown code fence (```json ... ```)
    - Adds a preamble like "Here is the result:" before the JSON
    - Adds trailing commentary after the closing brace
    - Returns valid bare JSON with no wrapping

    Raises ``ValueError`` if no valid JSON object can be extracted.
    """
    if not text:
        raise ValueError("Empty response from model")

    # 1. Try parsing the whole response as-is (ideal case)
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown code fences:  ```json\n...\n```  or  ```\n...\n```
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", stripped, re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # 3. Find the first '{' ... last '}' substring and try that
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = stripped[start : end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from model response. Raw: {text[:300]!r}")
