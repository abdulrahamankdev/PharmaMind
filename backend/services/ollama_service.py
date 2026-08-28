"""
Ollama Service — interface to local Ollama LLM for AI agent reasoning.
Handles prompt construction, streaming response aggregation, and JSON parsing.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

OLLAMA_URL = f"{settings.ollama_base_url}/api/generate"
MODEL      = settings.ollama_model
TIMEOUT    = 120.0


async def generate(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    expect_json: bool = True,
) -> str | dict:
    """
    Send a generation request to Ollama.
    If expect_json=True, attempts to parse and return dict; otherwise returns raw string.
    """
    payload: dict[str, Any] = {
        "model":  model or MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "top_p": 0.9,
            "num_predict": 2048,
        },
    }
    if system_prompt:
        payload["system"] = system_prompt

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.post(OLLAMA_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

        raw_text = data.get("response", "")

        if expect_json:
            return _extract_json(raw_text)
        return raw_text

    except httpx.ConnectError:
        logger.error("Ollama not reachable at %s — is Ollama running?", settings.ollama_base_url)
        raise RuntimeError(
            "Ollama LLM service is not reachable. "
            "Please start Ollama with: `ollama serve` and ensure the model is pulled."
        )
    except Exception as e:
        logger.error("Ollama generation failed: %s", e)
        raise


def _extract_json(text: str) -> dict:
    """
    Extract the first JSON object or array from a potentially verbose LLM response.
    Falls back to a structured error dict if no valid JSON is found.
    """
    # Try to extract JSON block from markdown code fences
    if "```json" in text:
        start = text.find("```json") + 7
        end   = text.find("```", start)
        text  = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end   = text.find("```", start)
        text  = text[start:end].strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to find first { ... }
    brace_start = text.find("{")
    brace_end   = text.rfind("}") + 1
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start:brace_end])
        except json.JSONDecodeError:
            pass

    # Return raw as fallback
    return {"raw_response": text, "parse_error": "Could not extract JSON from LLM response"}


async def list_local_models() -> list[str]:
    """Return names of models available locally in Ollama."""
    url = f"{settings.ollama_base_url}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []
