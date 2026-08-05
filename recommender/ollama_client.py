"""Thin wrappers around the local Ollama REST API for the two things this
pipeline needs from it: embeddings (offline indexing + online query encoding)
and structured chat completions (the LLM Decision Layer). Mirrors the
request/retry pattern already used by generation/llm_client.py rather than
inventing a second convention.
"""

from __future__ import annotations

import json
import time
from typing import Any

import requests
from pydantic import BaseModel

DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BACKOFF_SECONDS = 2.0


class OllamaError(Exception):
    """Connection failure, non-2xx response, or malformed output from Ollama."""


def embed_texts(
    texts: list[str],
    model: str,
    host: str = "http://localhost:11434",
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> list[list[float]]:
    """Batch-embed via POST /api/embed. Returns one vector per input text, in order."""
    if not texts:
        return []
    try:
        response = requests.post(
            f"{host.rstrip('/')}/api/embed",
            json={"model": model, "input": texts},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data["embeddings"]
    except requests.RequestException as exc:
        raise OllamaError(f"embedding request failed: {exc}") from exc
    except (KeyError, json.JSONDecodeError) as exc:
        raise OllamaError(f"malformed embedding response: {exc}") from exc

    if len(embeddings) != len(texts):
        raise OllamaError(
            f"expected {len(texts)} embeddings, got {len(embeddings)}"
        )
    return embeddings


def embed_text(text: str, model: str, host: str = "http://localhost:11434") -> list[float]:
    return embed_texts([text], model=model, host=host)[0]


def chat_structured(
    messages: list[dict[str, str]],
    output_format: type[BaseModel],
    model: str,
    host: str = "http://localhost:11434",
    temperature: float = 0.0,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> BaseModel:
    """Structured-output chat completion, enforced via Ollama's `format` field
    (a raw JSON Schema) -- same mechanism generation/llm_client.py relies on."""
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": output_format.model_json_schema(),
        "options": {"temperature": temperature},
    }

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(
                f"{host.rstrip('/')}/api/chat", json=payload, timeout=timeout
            )
            response.raise_for_status()
            content = response.json()["message"]["content"]
            return output_format.model_validate(json.loads(content))
        except requests.RequestException as exc:
            last_error = exc
        except (KeyError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc

        if attempt < max_retries:
            time.sleep(DEFAULT_RETRY_BACKOFF_SECONDS * (attempt + 1))

    raise OllamaError(str(last_error))


def get_model_info(model: str, host: str = "http://localhost:11434") -> dict:
    """Fetch model-identity metadata (digest, modified_at, parameter size /
    quantization) from Ollama, so eval output can record exactly which model
    build produced a given run. Without this, a future silent model update
    would look indistinguishable from the sampling non-determinism already
    confirmed at the decision and reranker layers -- there'd be no way to
    rule either explanation in or out after the fact. Never raises: a
    metadata-lookup failure shouldn't fail an eval run.
    """
    info: dict[str, Any] = {"model": model}
    try:
        response = requests.get(f"{host.rstrip('/')}/api/tags", timeout=DEFAULT_TIMEOUT_SECONDS)
        response.raise_for_status()
        for entry in response.json().get("models", []):
            if entry.get("name") == model or entry.get("model") == model:
                info["digest"] = entry.get("digest")
                info["modified_at"] = entry.get("modified_at")
                info["size_bytes"] = entry.get("size")
                break
    except (requests.RequestException, json.JSONDecodeError, KeyError) as exc:
        info["tags_error"] = str(exc)

    try:
        response = requests.post(
            f"{host.rstrip('/')}/api/show", json={"model": model}, timeout=DEFAULT_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        details = response.json().get("details", {}) or {}
        info["parameter_size"] = details.get("parameter_size")
        info["quantization_level"] = details.get("quantization_level")
        info["family"] = details.get("family")
    except (requests.RequestException, json.JSONDecodeError, KeyError) as exc:
        info["show_error"] = str(exc)

    return info
