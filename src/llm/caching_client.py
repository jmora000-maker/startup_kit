"""LLM record and replay caching client wrapper (QA-01)."""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
from src.core.interfaces import ILLMClient

logger = logging.getLogger(__name__)
T = TypeVar("T")


class LLMCacheMiss(Exception):
    """Raised when an LLM call is not found in the replay cache in replay mode."""
    def __init__(self, key: str, prompt: str, schema_name: Optional[str] = None):
        self.key = key
        self.prompt = prompt
        self.schema_name = schema_name
        msg = f"LLM cache miss for key '{key}' (schema: '{schema_name}'). Prompt preview: {prompt[:150]!r}"
        super().__init__(msg)


def compute_cache_key(
    model_id: str,
    system_prompt: Optional[str],
    prompt: str,
    schema_name: Optional[str] = None
) -> str:
    """Compute deterministic SHA-256 cache key across model ID, system prompt, prompt, and schema name."""
    hasher = hashlib.sha256()
    hasher.update((model_id or "").strip().encode("utf-8"))
    hasher.update(b"\x00")
    hasher.update((system_prompt or "").strip().encode("utf-8"))
    hasher.update(b"\x00")
    hasher.update((prompt or "").strip().encode("utf-8"))
    hasher.update(b"\x00")
    hasher.update((schema_name or "").strip().encode("utf-8"))
    return hasher.hexdigest()


class CachingLLMClient(ILLMClient):
    """Caching wrapper around ILLMClient with record, replay, and off modes (QA-01)."""

    def __init__(
        self,
        inner_client: ILLMClient,
        cache_dir: Optional[Path] = None,
        mode: str = "off",
        model_id: str = "claude-sonnet-5-5"
    ):
        self.inner_client = inner_client
        self.cache_dir = Path(cache_dir or Path("tests/fixtures/llm_cache"))
        self.mode = mode.lower()  # 'off', 'record', 'replay'
        self.model_id = model_id

    def _get_cache_file(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None
    ) -> T:
        schema_name = getattr(schema, "__name__", str(schema))
        key = compute_cache_key(self.model_id, system_prompt, prompt, schema_name)
        cache_file = self._get_cache_file(key)

        if self.mode == "replay":
            if not cache_file.exists():
                raise LLMCacheMiss(key, prompt, schema_name)
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                payload = cached_data.get("response")
                if isinstance(payload, dict):
                    return schema.model_validate(payload)
                if isinstance(payload, list) and hasattr(schema, "model_validate"):
                    return schema.model_validate(payload)
                if isinstance(payload, str):
                    from src.llm.client import parse_json_response_to_schema
                    return parse_json_response_to_schema(payload, schema)
                return payload
            except Exception as e:
                if isinstance(e, LLMCacheMiss):
                    raise
                raise RuntimeError(f"Failed to load cached response for key {key}: {e}") from e

        # If mode is 'off' or 'record'
        result = self.inner_client.generate_structured(prompt, schema, system_prompt=system_prompt)

        if self.mode == "record":
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            if hasattr(result, "model_dump"):
                resp_payload = result.model_dump(mode="json")
            else:
                resp_payload = result
            record_obj = {
                "key": key,
                "model_id": self.model_id,
                "schema_name": schema_name,
                "system_prompt": system_prompt,
                "prompt": prompt,
                "response": resp_payload
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(record_obj, f, indent=2, ensure_ascii=False)

        return result

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        key = compute_cache_key(self.model_id, system_prompt, prompt, None)
        cache_file = self._get_cache_file(key)

        if self.mode == "replay":
            if not cache_file.exists():
                raise LLMCacheMiss(key, prompt, None)
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            return str(cached_data.get("response", ""))

        result = self.inner_client.generate_text(prompt, system_prompt=system_prompt)

        if self.mode == "record":
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            record_obj = {
                "key": key,
                "model_id": self.model_id,
                "schema_name": None,
                "system_prompt": system_prompt,
                "prompt": prompt,
                "response": result
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(record_obj, f, indent=2, ensure_ascii=False)

        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner_client, name)
