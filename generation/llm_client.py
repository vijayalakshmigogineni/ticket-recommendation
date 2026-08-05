"""Provider-independent LLM client abstraction. OllamaClient talks to a local
Ollama server over its native REST API (POST /api/chat) -- no API keys, no
cloud batch jobs, no cloud-side retry/backoff. Every generation.pipeline stage
depends only on the call_sync(request) -> BaseModel contract below, so a
different local or remote provider could be swapped in later behind the same
interface without touching sampling/state/qa/pipeline/ingest/cli.

request is the dict shape generation/prompts/*.py build_request() functions
return: {"system": str | None, "messages": [{"role": "user", "content": ...}],
"output_format": <Pydantic model class>}. Structured output is enforced via
Ollama's `format` field, which accepts a raw JSON Schema (confirmed against a
local qwen3:4b server, including nested schemas with $defs/$ref -- no schema
translation needed for our existing Pydantic models).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import requests
from pydantic import BaseModel

DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_TIMEOUT_SECONDS = 300  # local inference on a long prompt can be slow
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BACKOFF_SECONDS = 2.0


class GenerationError(Exception):
    """Raised when a generation call fails -- a connection error, a non-2xx
    response, or a schema-validation failure on the model's output. state.py's
    retry machinery treats all of these the same way: requeue the unit under
    the retry cap, regardless of which of the three caused it."""


class OllamaClient:
    """The one LLM client generation.pipeline constructs and calls. No
    execution-mode split (batch vs sync) -- Ollama has no batch API, so every
    call is a direct synchronous request/response against the local server.
    Concurrency (when the pipeline wants to fan out several calls) is the
    caller's concern (see Pipeline._run_concurrent), not this client's.
    """

    def __init__(
        self,
        model: str,
        host: str = DEFAULT_HOST,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def call_sync(self, request: dict[str, Any]) -> BaseModel:
        output_format: type[BaseModel] = request["output_format"]
        messages = list(request["messages"])
        if request.get("system"):
            messages = [{"role": "system", "content": request["system"]}, *messages]

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "format": output_format.model_json_schema(),
        }

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = requests.post(
                    f"{self.host}/api/chat", json=payload, timeout=self.timeout
                )
                response.raise_for_status()
                content = response.json()["message"]["content"]
                return output_format.model_validate(json.loads(content))
            except requests.RequestException as exc:
                last_error = exc
            except (KeyError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc

            if attempt < self.max_retries:
                time.sleep(DEFAULT_RETRY_BACKOFF_SECONDS * (attempt + 1))

        raise GenerationError(str(last_error))
