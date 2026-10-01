"""Tests for QA-01 LLM record and replay caching client."""

import json
import pytest
from pydantic import BaseModel
from src.core.interfaces import ILLMClient
from src.llm.caching_client import CachingLLMClient, LLMCacheMiss, compute_cache_key


class SampleSchema(BaseModel):
    title: str
    count: int


class DummyInnerClient(ILLMClient):
    def __init__(self):
        self.structured_calls = 0
        self.text_calls = 0

    def generate_structured(self, prompt: str, schema: type, system_prompt: str = None):
        self.structured_calls += 1
        return schema(title=f"Result for {prompt}", count=42)

    def generate_text(self, prompt: str, system_prompt: str = None) -> str:
        self.text_calls += 1
        return f"Text response for {prompt}"


def test_cache_key_computation():
    k1 = compute_cache_key("claude-sonnet-5-5", "Sys", "Prompt", "SampleSchema")
    k2 = compute_cache_key("claude-sonnet-5-5", "Sys", "Prompt", "SampleSchema")
    k3 = compute_cache_key("claude-sonnet-5-5", "Sys", "Different", "SampleSchema")
    assert k1 == k2
    assert k1 != k3
    assert len(k1) == 64


def test_record_and_replay_structured(tmp_path):
    inner = DummyInnerClient()
    client_rec = CachingLLMClient(inner, cache_dir=tmp_path, mode="record", model_id="test-model")
    res1 = client_rec.generate_structured("Extract data", SampleSchema, system_prompt="System instructions")
    assert res1.title == "Result for Extract data"
    assert res1.count == 42
    assert inner.structured_calls == 1

    # In replay mode, should hit cache and NOT call inner
    client_rep = CachingLLMClient(DummyInnerClient(), cache_dir=tmp_path, mode="replay", model_id="test-model")
    res2 = client_rep.generate_structured("Extract data", SampleSchema, system_prompt="System instructions")
    assert res2.title == "Result for Extract data"
    assert res2.count == 42

    # Miss in replay mode must raise LLMCacheMiss
    with pytest.raises(LLMCacheMiss) as excinfo:
        client_rep.generate_structured("Uncached prompt", SampleSchema, system_prompt="System instructions")
    assert "LLM cache miss" in str(excinfo.value)


def test_record_and_replay_text(tmp_path):
    inner = DummyInnerClient()
    client_rec = CachingLLMClient(inner, cache_dir=tmp_path, mode="record", model_id="test-model")
    txt = client_rec.generate_text("Generate summary", system_prompt="System")
    assert txt == "Text response for Generate summary"
    assert inner.text_calls == 1

    client_rep = CachingLLMClient(DummyInnerClient(), cache_dir=tmp_path, mode="replay", model_id="test-model")
    txt_rep = client_rep.generate_text("Generate summary", system_prompt="System")
    assert txt_rep == "Text response for Generate summary"

    with pytest.raises(LLMCacheMiss):
        client_rep.generate_text("Unknown text prompt", system_prompt="System")
