"""Unit tests for LangChainLLMClient and OpenAI fallback functionality."""

import pytest
from unittest.mock import MagicMock
from pydantic import BaseModel, Field
from src.llm.client import LangChainLLMClient


class SampleSchema(BaseModel):
    title: str = Field(..., description="Project Title")
    score: int = Field(default=100)


def test_anthropic_success_does_not_invoke_openai():
    """Verify that when Anthropic succeeds, OpenAI fallback is not called."""
    mock_anthropic = MagicMock()
    mock_structured_anthropic = MagicMock()
    expected_result = SampleSchema(title="Anthropic Success", score=99)
    mock_structured_anthropic.invoke.return_value = expected_result
    mock_anthropic.with_structured_output.return_value = mock_structured_anthropic

    mock_openai = MagicMock()

    client = LangChainLLMClient(
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai
    )

    result = client.generate_structured("Extract title", SampleSchema)
    assert result == expected_result
    mock_anthropic.with_structured_output.assert_called_once_with(SampleSchema, method="json_schema")
    mock_structured_anthropic.invoke.assert_called_once()
    mock_openai.with_structured_output.assert_not_called()


def test_anthropic_failure_falls_back_to_openai():
    """Verify that when Anthropic encounters an error (e.g. 404/401), it falls back to OpenAI."""
    mock_anthropic = MagicMock()
    mock_structured_anthropic = MagicMock()
    mock_structured_anthropic.invoke.side_effect = RuntimeError("Anthropic 404 Not Found")
    mock_anthropic.with_structured_output.return_value = mock_structured_anthropic
    # Also fail text generation on Anthropic to trigger full failover
    mock_anthropic.invoke.side_effect = RuntimeError("Anthropic text generation 404")

    mock_openai = MagicMock()
    mock_structured_openai = MagicMock()
    expected_result = SampleSchema(title="OpenAI Fallback Success", score=100)
    mock_structured_openai.invoke.return_value = expected_result
    mock_openai.with_structured_output.return_value = mock_structured_openai

    client = LangChainLLMClient(
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai
    )

    result = client.generate_structured("Extract title", SampleSchema)
    assert result == expected_result
    mock_structured_anthropic.invoke.assert_called_once()
    mock_openai.with_structured_output.assert_called_once()


def test_anthropic_schema_complexity_recovers_via_prompt_json_on_anthropic():
    """Verify that when Anthropic native structured outputs fails with 'Schema is too complex',
    Anthropic fulfills the schema via schema-instructed JSON generation without falling back to OpenAI."""
    mock_anthropic = MagicMock()
    mock_structured_anthropic = MagicMock()
    mock_structured_anthropic.invoke.side_effect = RuntimeError("Error code: 400 - Schema is too complex.")
    mock_anthropic.with_structured_output.return_value = mock_structured_anthropic

    # Anthropic text generation succeeds with valid JSON text as list of blocks
    mock_text_response = MagicMock()
    mock_text_response.content = [
        {"type": "text", "text": '```json\n{"title": "Claude Schema Recovered", "score": 98}\n```'}
    ]
    mock_anthropic.invoke.return_value = mock_text_response

    mock_openai = MagicMock()

    client = LangChainLLMClient(
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai
    )

    # First run on a non-cached schema name
    class NonCachedSchema(BaseModel):
        title: str
        score: int

    result = client.generate_structured("Extract title", NonCachedSchema)
    assert result == NonCachedSchema(title="Claude Schema Recovered", score=98)
    mock_structured_anthropic.invoke.assert_called_once()
    mock_anthropic.invoke.assert_called_once()
    mock_openai.with_structured_output.assert_not_called()


def test_complex_schema_caching_skips_native_structured_call():
    """Verify that schemas in _COMPLEX_SCHEMAS bypass with_structured_output and call Anthropic text generation directly."""
    from src.core.models import CharterExtraction
    mock_anthropic = MagicMock()
    mock_text_response = MagicMock()
    mock_text_response.content = [
        {"type": "text", "text": '{"project_name": "Cached Direct Pass", "client_name": "Pfizer"}'}
    ]
    mock_anthropic.invoke.return_value = mock_text_response

    mock_openai = MagicMock()
    client = LangChainLLMClient(
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai
    )

    result = client.generate_structured("Extract charter", CharterExtraction)
    assert result.project_name == "Cached Direct Pass"
    assert result.client_name == "Pfizer"
    mock_anthropic.with_structured_output.assert_not_called()
    mock_anthropic.invoke.assert_called_once()
    mock_openai.with_structured_output.assert_not_called()


def test_extract_text_content_and_list_blocks():
    """Verify extract_text_content handles strings, dict blocks, object blocks, and filters out thinking blocks."""
    from src.llm.client import extract_text_content, parse_json_response_to_schema

    class BlockObj:
        def __init__(self, text, block_type="text"):
            self.text = text
            self.type = block_type

    # 1. List of dict blocks with thinking block followed by text block
    content_list_dict = [
        {"type": "thinking", "thinking": "let me think...", "signature": "sig123"},
        {"type": "text", "text": '{"title": "DictBlock", "score": 77}'}
    ]
    assert extract_text_content(content_list_dict) == '{"title": "DictBlock", "score": 77}'

    # 2. List of objects with .type and .text, including thinking object
    content_list_obj = [
        BlockObj("reasoning steps...", block_type="thinking"),
        BlockObj('{"title": "ObjBlock", "score": 88}', block_type="text")
    ]
    assert extract_text_content(content_list_obj) == '{"title": "ObjBlock", "score": 88}'

    # 3. Direct parse_json_response_to_schema with list input containing thinking blocks
    parsed = parse_json_response_to_schema(content_list_dict, SampleSchema)
    assert parsed.title == "DictBlock" and parsed.score == 77


def test_parse_json_response_to_schema_variations():
    """Verify that JSON parser helper handles raw JSON, markdown blocks, and surrounding text."""
    from src.llm.client import parse_json_response_to_schema

    # 1. Plain raw JSON
    res1 = parse_json_response_to_schema('{"title": "Plain", "score": 10}', SampleSchema)
    assert res1.title == "Plain" and res1.score == 10

    # 2. Markdown fenced JSON block
    res2 = parse_json_response_to_schema('```json\n{"title": "Fenced", "score": 20}\n```', SampleSchema)
    assert res2.title == "Fenced" and res2.score == 20

    # 3. Conversational preamble and postamble
    res3 = parse_json_response_to_schema(
        'Here is the extracted information:\n{"title": "Preamble", "score": 30}\nHope this helps!',
        SampleSchema
    )
    assert res3.title == "Preamble" and res3.score == 30


def test_openai_only_when_anthropic_not_configured():
    """Verify that if Anthropic is omitted, client seamlessly uses OpenAI."""
    mock_openai = MagicMock()
    mock_structured_openai = MagicMock()
    expected_result = SampleSchema(title="Direct OpenAI Success", score=95)
    mock_structured_openai.invoke.return_value = expected_result
    mock_openai.with_structured_output.return_value = mock_structured_openai

    client = LangChainLLMClient(
        api_key="",
        chat_model=None,
        openai_chat_model=mock_openai
    )

    result = client.generate_structured("Extract title", SampleSchema)
    assert result == expected_result
    mock_structured_openai.invoke.assert_called_once()


def test_text_generation_anthropic_fallback_to_openai():
    """Verify that generate_text falls back to OpenAI on Anthropic failure."""
    mock_anthropic = MagicMock()
    mock_anthropic.invoke.side_effect = RuntimeError("Anthropic API Error")

    mock_openai = MagicMock()
    mock_openai_response = MagicMock()
    mock_openai_response.content = "OpenAI generated text response."
    mock_openai.invoke.return_value = mock_openai_response

    client = LangChainLLMClient(
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai
    )

    text = client.generate_text("Summarize project")
    assert text == "OpenAI generated text response."
    mock_anthropic.invoke.assert_called_once()
    mock_openai.invoke.assert_called_once()


def test_no_keys_configured_raises_value_error():
    """Verify ValueError is raised if neither Anthropic nor OpenAI is configured."""
    client = LangChainLLMClient(
        api_key="",
        openai_api_key="",
        chat_model=None,
        openai_chat_model=None
    )

    with pytest.raises(ValueError, match="LLM client is not initialized with an API key"):
        client.generate_structured("Test prompt", SampleSchema)

    with pytest.raises(ValueError, match="LLM client has no API key configured"):
        client.generate_text("Test prompt")


def test_max_tokens_configuration(monkeypatch):
    """Verify max_tokens defaults to 16384 and is configurable."""
    from src.config import config
    monkeypatch.setattr(config, "max_tokens", 16384)
    client = LangChainLLMClient(
        api_key="",
        openai_api_key="",
        chat_model=None,
        openai_chat_model=None,
    )
    assert client.max_tokens == 16384
    assert client.anthropic_max_tokens == 16384
    assert client.openai_max_tokens == 16384

    client_custom = LangChainLLMClient(
        api_key="",
        openai_api_key="",
        chat_model=None,
        openai_chat_model=None,
        max_tokens=32768,
    )
    assert client_custom.max_tokens == 32768
    assert client_custom.anthropic_max_tokens == 32768
    assert client_custom.openai_max_tokens == 16384


def test_provider_specific_token_limit_clamping():
    """Verify LLM-01: OpenAI models are clamped to 16384 while Anthropic retains up to 64000."""
    from src.llm.client import get_clamped_max_tokens

    # OpenAI gpt-4o clamped to 16384
    assert get_clamped_max_tokens("openai", "gpt-4o", 32768) == 16384
    assert get_clamped_max_tokens("openai", "gpt-4o-mini", 32768) == 16384
    assert get_clamped_max_tokens("openai", "gpt-4o", 8192) == 8192

    # OpenAI gpt-4-turbo clamped to 4096
    assert get_clamped_max_tokens("openai", "gpt-4-turbo", 32768) == 4096

    # OpenAI o1/o3 support up to 65536
    assert get_clamped_max_tokens("openai", "o1-preview", 32768) == 32768
    assert get_clamped_max_tokens("openai", "o3-mini", 70000) == 65536

    # Anthropic models support up to 64000
    assert get_clamped_max_tokens("anthropic", "claude-sonnet-5-5", 32768) == 32768
    assert get_clamped_max_tokens("anthropic", "claude-sonnet-5-5", 70000) == 64000

    # Client instantiation clamps internal model parameters
    client = LangChainLLMClient(
        api_key="sk-ant-test",
        model_name="claude-sonnet-5-5",
        openai_api_key="sk-openai-test",
        openai_model_name="gpt-4o",
        max_tokens=32768,
    )
    assert client._chat_model.max_tokens == 32768
    assert client._openai_chat_model.max_tokens == 16384


def test_anthropic_truncation_raises_runtime_error_and_falls_back_to_openai():
    """Verify that when Anthropic reaches max_tokens (truncation), it is treated as fatal and falls back to OpenAI."""
    mock_anthropic = MagicMock()
    mock_response = MagicMock()
    mock_response.response_metadata = {"stop_reason": "max_tokens"}
    mock_response.content = '{"title": "Truncated json'
    mock_anthropic.invoke.return_value = mock_response

    mock_openai = MagicMock()
    mock_openai_response = MagicMock()
    mock_openai_response.content = '{"title": "Full OpenAI Title", "score": 100}'
    mock_openai.invoke.return_value = mock_openai_response

    client = LangChainLLMClient(
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai,
    )

    # In generate_text with Anthropic, truncation raises RuntimeError and falls back to OpenAI
    text = client.generate_text("Summarize project")
    assert text == '{"title": "Full OpenAI Title", "score": 100}'
    mock_anthropic.invoke.assert_called_once()
    mock_openai.invoke.assert_called_once()


def test_anthropic_model_resolution_and_aliases():
    """Verify that retired/legacy Claude model IDs automatically map to active replacements."""
    from src.config import resolve_anthropic_model

    # Sonnet replacements -> claude-sonnet-5-5
    assert resolve_anthropic_model("claude-3-5-sonnet-20240620") == "claude-sonnet-5-5"
    assert resolve_anthropic_model("claude-3-7-sonnet-20250219") == "claude-sonnet-5-5"
    assert resolve_anthropic_model("claude-3-5-sonnet-20241022") == "claude-sonnet-5-5"
    assert resolve_anthropic_model("claude-3-5-sonnet-latest") == "claude-sonnet-5-5"

    # Haiku replacements -> claude-haiku-4-5-20251001
    assert resolve_anthropic_model("claude-3-haiku-20240307") == "claude-haiku-4-5-20251001"
    assert resolve_anthropic_model("claude-3-5-haiku-20241022") == "claude-haiku-4-5-20251001"
    assert resolve_anthropic_model("claude-3-5-haiku-latest") == "claude-haiku-4-5-20251001"

    # Default fallback when None/empty
    assert resolve_anthropic_model(None) == "claude-sonnet-5-5"
    assert resolve_anthropic_model("") == "claude-sonnet-5-5"

    # Unknown custom ID is preserved
    assert resolve_anthropic_model("custom-enterprise-claude") == "custom-enterprise-claude"

    # Verify LangChainLLMClient resolves model_name upon initialization
    client = LangChainLLMClient(
        api_key="",
        model_name="claude-3-7-sonnet-20250219",
        chat_model=None,
        openai_chat_model=None,
    )
    assert client.model_name == "claude-sonnet-5-5"

    client_haiku = LangChainLLMClient(
        api_key="",
        model_name="claude-3-5-haiku-20241022",
        chat_model=None,
        openai_chat_model=None,
    )
    assert client_haiku.model_name == "claude-haiku-4-5-20251001"


def test_anthropic_temperature_omitted_for_modern_claude():
    """Verify that ChatAnthropic is instantiated with temperature=None to avoid 400 Bad Request."""
    client = LangChainLLMClient(
        api_key="sk-ant-test-key",
        model_name="claude-sonnet-5-5",
        temperature=0.0,
    )
    assert client._chat_model is not None
    assert client._chat_model.temperature is None


def test_fallback_domains_tracking():
    """Verify that fallback_domains records schema names when failing over to OpenAI."""
    mock_anthropic = MagicMock()
    mock_anthropic.with_structured_output.side_effect = RuntimeError("Anthropic 500 Server Error")
    mock_anthropic.invoke.side_effect = RuntimeError("Anthropic text 500")

    mock_openai = MagicMock()
    mock_structured_openai = MagicMock()
    mock_structured_openai.invoke.return_value = SampleSchema(title="OpenAI Tracked", score=90)
    mock_openai.with_structured_output.return_value = mock_structured_openai

    client = LangChainLLMClient(
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai
    )

    assert client.fallback_domains == []
    result = client.generate_structured("Extract", SampleSchema)
    assert result.title == "OpenAI Tracked"
    assert "SampleSchema" in client.fallback_domains


def test_openai_primary_falls_back_to_anthropic_structured():
    """Verify LLM-02: when OpenAI is primary and fails, client falls back to Anthropic."""
    mock_openai = MagicMock()
    mock_openai.with_structured_output.side_effect = RuntimeError("OpenAI 429 Quota Exceeded")
    mock_openai.invoke.side_effect = RuntimeError("OpenAI text 429")

    mock_anthropic = MagicMock()
    mock_structured_anthropic = MagicMock()
    mock_structured_anthropic.invoke.return_value = SampleSchema(title="Anthropic Reverse Fallback", score=95)
    mock_anthropic.with_structured_output.return_value = mock_structured_anthropic

    client = LangChainLLMClient(
        primary_provider="openai",
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai,
    )

    assert client.fallback_domains == []
    result = client.generate_structured("Extract project", SampleSchema)
    assert result.title == "Anthropic Reverse Fallback"
    assert result.score == 95
    assert "SampleSchema" in client.fallback_domains


def test_openai_primary_falls_back_to_anthropic_text():
    """Verify LLM-02: text generation falls back to Anthropic when OpenAI primary fails."""
    mock_openai = MagicMock()
    mock_openai.invoke.side_effect = RuntimeError("OpenAI RateLimitError")

    mock_anthropic = MagicMock()
    mock_anthropic_resp = MagicMock()
    mock_anthropic_resp.content = "Anthropic fallback text response"
    mock_anthropic.invoke.return_value = mock_anthropic_resp

    client = LangChainLLMClient(
        primary_provider="openai",
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai,
    )

    assert client.fallback_domains == []
    result = client.generate_text("Summarize project")
    assert result == "Anthropic fallback text response"
    assert "TextGeneration" in client.fallback_domains
    mock_openai.invoke.assert_called_once()
    mock_anthropic.invoke.assert_called_once()


def test_build_llm_client_configures_symmetric_fallback():
    """Verify LLM-02: orchestrator build_llm_client configures fallback models in both directions."""
    from src.orchestrator import build_llm_client

    # Case 1: Anthropic primary with OpenAI key provided -> Anthropic primary with OpenAI fallback
    c_anthropic = build_llm_client(
        provider="anthropic",
        anthropic_api_key="sk-ant-test",
        openai_api_key="sk-openai-test",
        mock=False,
    )
    assert c_anthropic.inner_client.primary_provider == "anthropic"
    assert c_anthropic.inner_client._chat_model is not None
    assert c_anthropic.inner_client._openai_chat_model is not None

    # Case 2: OpenAI primary with Anthropic key provided -> OpenAI primary with Anthropic fallback
    c_openai = build_llm_client(
        provider="openai",
        anthropic_api_key="sk-ant-test",
        openai_api_key="sk-openai-test",
        mock=False,
    )
    assert c_openai.inner_client.primary_provider == "openai"
    assert c_openai.inner_client._chat_model is not None
    assert c_openai.inner_client._openai_chat_model is not None
