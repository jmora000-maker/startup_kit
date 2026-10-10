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
    """Verify LLM-01: OpenAI models are clamped to 16384 while Anthropic retains up to 128000/64000 per model."""
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

    # Anthropic models: claude-sonnet-5-5 supports up to 128000
    assert get_clamped_max_tokens("anthropic", "claude-sonnet-5-5", 32768) == 32768
    assert get_clamped_max_tokens("anthropic", "claude-sonnet-5-5", 150000) == 128000

    # Anthropic models: claude-haiku-4-5-20251001 supports up to 64000
    assert get_clamped_max_tokens("anthropic", "claude-haiku-4-5-20251001", 32768) == 32768
    assert get_clamped_max_tokens("anthropic", "claude-haiku-4-5-20251001", 70000) == 64000

    # Anthropic legacy models: claude-3-5-sonnet supports up to 8192
    assert get_clamped_max_tokens("anthropic", "claude-3-5-sonnet-20240620", 32768) == 8192
    # Anthropic legacy models: claude-3-haiku supports up to 4096
    assert get_clamped_max_tokens("anthropic", "claude-3-haiku-20240307", 32768) == 4096

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


def test_openai_truncation_raises_runtime_error_and_falls_back_to_anthropic():
    """Verify LLM-03 (4b): finish_reason == 'length' from OpenAI is treated as fatal truncation and falls back to Anthropic."""
    mock_openai = MagicMock()
    mock_openai_response = MagicMock()
    mock_openai_response.response_metadata = {"finish_reason": "length"}
    mock_openai_response.content = '{"title": "Truncated OpenAI'
    mock_openai.invoke.return_value = mock_openai_response

    mock_anthropic = MagicMock()
    mock_anthropic_resp = MagicMock()
    mock_anthropic_resp.content = '{"title": "Complete Anthropic Title", "score": 100}'
    mock_anthropic.invoke.return_value = mock_anthropic_resp

    client = LangChainLLMClient(
        primary_provider="openai",
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai,
    )

    text = client.generate_text("Summarize project")
    assert text == '{"title": "Complete Anthropic Title", "score": 100}'
    assert "TextGeneration" in client.fallback_domains
    mock_openai.invoke.assert_called_once()
    mock_anthropic.invoke.assert_called_once()


def test_openai_truncation_exhaustion_raises_clear_error():
    """Verify LLM-03 (4b): finish_reason == 'length' when no fallback is available raises clear RuntimeError, not silently parsed."""
    mock_openai = MagicMock()
    mock_openai_response = MagicMock()
    mock_openai_response.response_metadata = {"finish_reason": "length"}
    mock_openai_response.content = '{"title": "Truncated OpenAI'
    mock_openai.invoke.return_value = mock_openai_response

    client = LangChainLLMClient(
        primary_provider="openai",
        api_key="",
        chat_model=None,
        openai_chat_model=mock_openai,
    )

    with pytest.raises(RuntimeError, match="OpenAI response was truncated due to reaching max_tokens"):
        client.generate_text("Summarize project")


def test_both_providers_fail_generate_structured_exhaustion():
    """Verify LLM-03 (4a): when both providers fail, generate_structured raises the failure exception."""
    mock_anthropic = MagicMock()
    mock_anthropic.with_structured_output.side_effect = RuntimeError("Anthropic 429 RateLimit")
    mock_anthropic.invoke.side_effect = RuntimeError("Anthropic text 429 RateLimit")

    mock_openai = MagicMock()
    mock_openai.with_structured_output.side_effect = RuntimeError("OpenAI 429 InsufficientQuota")
    mock_openai.invoke.side_effect = RuntimeError("OpenAI text 429 InsufficientQuota")

    client = LangChainLLMClient(
        primary_provider="anthropic",
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai,
    )

    with pytest.raises(RuntimeError, match="OpenAI text 429 InsufficientQuota"):
        client.generate_structured("Extract project", SampleSchema)


def test_env_var_llm_provider_openai_routes_through_build_llm_client(monkeypatch):
    """Verify LLM-02/LLM-01: setting LLM_PROVIDER=openai in environment and routing through build_llm_client
    (a) configures primary_provider as 'openai', and
    (b) ensures calls through that exact path use the clamped 16384 token ceiling (even when MAX_TOKENS=32768).
    """
    import src.config
    from src.orchestrator import build_llm_client

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("MAX_TOKENS", "32768")
    monkeypatch.setattr(src.config.config, "default_provider", "openai")
    monkeypatch.setattr(src.config.config, "max_tokens", 32768)

    client = build_llm_client(
        provider=src.config.config.default_provider,
        anthropic_api_key="sk-ant-test",
        openai_api_key="sk-proj-test",
        mock=False,
    )

    inner = client.inner_client
    # (a) Check primary_provider is correctly "openai"
    assert inner.primary_provider == "openai"
    assert inner.max_tokens == 32768

    # (b) Check clamped token ceiling on OpenAI chat model
    assert inner.openai_max_tokens == 16384
    assert inner._openai_chat_model.max_tokens == 16384

    # Verify faithful invocation through this exact path
    mock_resp = MagicMock()
    mock_resp.content = "OpenAI response from primary provider with clamped ceiling"
    mock_resp.response_metadata = {"finish_reason": "stop"}

    monkeypatch.setattr("langchain_openai.ChatOpenAI.invoke", MagicMock(return_value=mock_resp))
    result = client.generate_text("Test prompt")
    assert result == "OpenAI response from primary provider with clamped ceiling"


def test_anthropic_usage_cap_error_immediately_falls_back_to_openai_without_redundant_retry():
    """Verify that when Anthropic native structured outputs fails with a provider error (e.g. workspace usage limit),
    it immediately falls back to OpenAI without redundantly re-attempting Anthropic text generation in Step 1b."""
    mock_anthropic = MagicMock()
    mock_structured_anthropic = MagicMock()
    mock_structured_anthropic.invoke.side_effect = RuntimeError(
        "AnthropicInvalidRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'You have reached your specified workspace API usage limits. Please increase your limit in your workspace settings.'}}"
    )
    mock_anthropic.with_structured_output.return_value = mock_structured_anthropic

    mock_openai = MagicMock()
    mock_structured_openai = MagicMock()
    expected_result = SampleSchema(title="OpenAI Fallback Success After Anthropic Cap", score=100)
    mock_structured_openai.invoke.return_value = expected_result
    mock_openai.with_structured_output.return_value = mock_structured_openai

    client = LangChainLLMClient(
        primary_provider="anthropic",
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai,
    )

    result = client.generate_structured("Extract project", SampleSchema)
    assert result == expected_result
    mock_structured_anthropic.invoke.assert_called_once()
    # Step 1b must be skipped so Anthropic text invoke is NOT called
    mock_anthropic.invoke.assert_not_called()
    mock_openai.with_structured_output.assert_called_once()
    assert "SampleSchema" in client.fallback_domains


def test_openai_primary_quota_error_immediately_falls_back_to_anthropic_without_redundant_retry():
    """Verify that when OpenAI native structured outputs fails with a provider error (e.g. 429 Quota Exceeded),
    it immediately falls back to Anthropic without redundantly re-attempting OpenAI text generation in Step 1b."""
    mock_openai = MagicMock()
    mock_structured_openai = MagicMock()
    mock_structured_openai.invoke.side_effect = RuntimeError("OpenAI 429 InsufficientQuota")
    mock_openai.with_structured_output.return_value = mock_structured_openai

    mock_anthropic = MagicMock()
    mock_structured_anthropic = MagicMock()
    expected_result = SampleSchema(title="Anthropic Fallback Success After OpenAI Quota", score=95)
    mock_structured_anthropic.invoke.return_value = expected_result
    mock_anthropic.with_structured_output.return_value = mock_structured_anthropic

    client = LangChainLLMClient(
        primary_provider="openai",
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai,
    )

    result = client.generate_structured("Extract project", SampleSchema)
    assert result == expected_result
    mock_structured_openai.invoke.assert_called_once()
    # Step 1b must be skipped so OpenAI text invoke is NOT called
    mock_openai.invoke.assert_not_called()
    mock_anthropic.with_structured_output.assert_called_once()
    assert "SampleSchema" in client.fallback_domains


def test_complex_schema_anthropic_usage_cap_falls_back_to_openai():
    """Verify that when a complex schema (e.g. CharterExtraction) is processed and Anthropic hits
    workspace usage limit in Step 1b prompt extraction, generate_text gracefully falls back to OpenAI."""
    from src.core.models import CharterExtraction

    mock_anthropic = MagicMock()
    mock_anthropic.invoke.side_effect = RuntimeError(
        "AnthropicInvalidRequestError: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'You have reached your specified workspace API usage limits.'}}"
    )

    mock_openai = MagicMock()
    mock_openai_response = MagicMock()
    mock_openai_response.content = '{"project_name": "OpenAI SOW Project", "executive_summary": "Extracted via OpenAI fallback."}'
    mock_openai.invoke.return_value = mock_openai_response

    client = LangChainLLMClient(
        primary_provider="anthropic",
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai,
    )

    result = client.generate_structured("Extract charter", CharterExtraction)
    assert isinstance(result, CharterExtraction)
    assert result.project_name == "OpenAI SOW Project"
    assert result.executive_summary == "Extracted via OpenAI fallback."
    mock_anthropic.invoke.assert_called_once()
    mock_openai.invoke.assert_called_once()
    mock_openai.with_structured_output.assert_not_called()
    assert "CharterExtraction" in client.fallback_domains


def test_schema_complexity_error_anthropic_usage_cap_falls_back_to_openai():
    """Verify that when native structured fails with 'schema is too complex' and Anthropic text prompt
    subsequently hits usage limits, it falls back to OpenAI text generation via LLM-02 fallback."""
    class CustomComplexSchema(BaseModel):
        title: str
        score: int

    mock_anthropic = MagicMock()
    mock_structured_anthropic = MagicMock()
    mock_structured_anthropic.invoke.side_effect = RuntimeError("Error code: 400 - schema is too complex")
    mock_anthropic.with_structured_output.return_value = mock_structured_anthropic
    mock_anthropic.invoke.side_effect = RuntimeError(
        "AnthropicInvalidRequestError: You have reached your specified workspace API usage limits."
    )

    mock_openai = MagicMock()
    mock_openai_response = MagicMock()
    mock_openai_response.content = '{"title": "OpenAI Recovered Schema", "score": 95}'
    mock_openai.invoke.return_value = mock_openai_response

    client = LangChainLLMClient(
        primary_provider="anthropic",
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai,
    )

    result = client.generate_structured("Extract custom", CustomComplexSchema)
    assert isinstance(result, CustomComplexSchema)
    assert result.title == "OpenAI Recovered Schema"
    assert result.score == 95
    mock_structured_anthropic.invoke.assert_called_once()
    mock_anthropic.invoke.assert_called_once()
    mock_openai.invoke.assert_called_once()
    mock_openai.with_structured_output.assert_not_called()
    assert "CustomComplexSchema" in client.fallback_domains


def test_is_unsupported_temperature_error_detection():
    """Verify is_unsupported_temperature_error accurately matches temperature restriction errors."""
    from src.llm.client import is_unsupported_temperature_error

    err1 = RuntimeError(
        "Error code: 400 - {'error': {'message': \"Unsupported value: 'temperature' does not support 0.0 with this model. Only the default (1) value is supported.\", 'type': 'invalid_request_error', 'param': 'temperature', 'code': 'unsupported_value'}}"
    )
    err2 = RuntimeError(
        "Unsupported value: 'temperature' parameter only supports the default value of 1 with this model."
    )
    err3 = RuntimeError("OpenAI 429 InsufficientQuota")
    err4 = RuntimeError("Anthropic 404 Not Found")

    assert is_unsupported_temperature_error(err1) is True
    assert is_unsupported_temperature_error(err2) is True
    assert is_unsupported_temperature_error(err3) is False
    assert is_unsupported_temperature_error(err4) is False


def test_openai_unsupported_temperature_retries_and_succeeds_structured():
    """Verify that when OpenAI structured output fails with an unsupported temperature error,
    it automatically reconfigures temperature to None and retries successfully without raising an error."""
    mock_openai = MagicMock()
    mock_openai.temperature = 0.0
    mock_structured = MagicMock()

    temp_error = RuntimeError(
        "Error code: 400 - {'error': {'message': \"Unsupported value: 'temperature' does not support 0.0 with this model. Only the default (1) value is supported.\", 'type': 'invalid_request_error', 'param': 'temperature', 'code': 'unsupported_value'}}"
    )
    expected_result = SampleSchema(title="Retry Success", score=100)
    mock_structured.invoke.side_effect = [temp_error, expected_result]
    mock_openai.with_structured_output.return_value = mock_structured

    client = LangChainLLMClient(
        primary_provider="openai",
        openai_chat_model=mock_openai,
        temperature=0.0,
    )

    result = client.generate_structured("Extract project", SampleSchema)
    assert result == expected_result
    assert mock_structured.invoke.call_count == 2
    assert client.temperature is None
    assert mock_openai.temperature is None


def test_openai_unsupported_temperature_retries_and_succeeds_text():
    """Verify that when OpenAI text generation fails with an unsupported temperature error,
    it automatically reconfigures temperature to None and retries successfully."""
    mock_openai = MagicMock()
    mock_openai.temperature = 0.0

    temp_error = RuntimeError(
        "Error code: 400 - {'error': {'message': \"Unsupported value: 'temperature' does not support 0.0 with this model. Only the default (1) value is supported.\", 'type': 'invalid_request_error', 'param': 'temperature', 'code': 'unsupported_value'}}"
    )
    mock_response = MagicMock()
    mock_response.content = "OpenAI text retry success"
    mock_openai.invoke.side_effect = [temp_error, mock_response]

    client = LangChainLLMClient(
        primary_provider="openai",
        openai_chat_model=mock_openai,
        temperature=0.0,
    )

    result = client.generate_text("Prompt test")
    assert result == "OpenAI text retry success"
    assert mock_openai.invoke.call_count == 2
    assert client.temperature is None
    assert mock_openai.temperature is None


def test_openai_temperature_state_persists_for_subsequent_calls():
    """Verify that once temperature is reconfigured to None after an error, subsequent domain extractions
    execute directly with temperature=None without redundant re-triggers."""
    mock_openai = MagicMock()
    mock_openai.temperature = 0.0
    mock_structured = MagicMock()

    temp_error = RuntimeError(
        "Error code: 400 - {'error': {'message': \"Unsupported value: 'temperature' does not support 0.0 with this model. Only the default (1) value is supported.\", 'type': 'invalid_request_error', 'param': 'temperature', 'code': 'unsupported_value'}}"
    )
    result_1 = SampleSchema(title="First Extraction", score=10)
    result_2 = SampleSchema(title="Second Extraction", score=20)

    # First call fails on attempt 1, succeeds on attempt 2. Second call succeeds on attempt 1.
    mock_structured.invoke.side_effect = [temp_error, result_1, result_2]
    mock_openai.with_structured_output.return_value = mock_structured

    client = LangChainLLMClient(
        primary_provider="openai",
        openai_chat_model=mock_openai,
        temperature=0.0,
    )

    r1 = client.generate_structured("Extract 1", SampleSchema)
    assert r1 == result_1
    assert mock_structured.invoke.call_count == 2
    assert client.temperature is None

    r2 = client.generate_structured("Extract 2", SampleSchema)
    assert r2 == result_2
    assert mock_structured.invoke.call_count == 3


def test_openai_concurrent_threads_unsupported_temperature_all_recover():
    """Verify that when 14 concurrent threads all hit a 400 temperature error simultaneously,
    every thread retries and recovers successfully with at most one reconfiguration warning."""
    from concurrent.futures import ThreadPoolExecutor
    import logging
    import threading

    mock_openai = MagicMock()
    mock_openai.temperature = 0.0

    temp_error = RuntimeError(
        "Error code: 400 - {'error': {'message': \"Unsupported value: 'temperature' does not support 0.0 with this model. Only the default (1) value is supported.\", 'type': 'invalid_request_error', 'param': 'temperature', 'code': 'unsupported_value'}}"
    )

    call_count = 0
    lock = threading.Lock()

    def mock_invoke(messages):
        nonlocal call_count
        with lock:
            call_count += 1
            # If the client still has temperature == 0.0, raise 400; once reconfigured to None, succeed
            if mock_openai.temperature == 0.0:
                raise temp_error
            return SampleSchema(title="Concurrent Success", score=call_count)

    mock_structured = MagicMock()
    mock_structured.invoke.side_effect = mock_invoke
    mock_openai.with_structured_output.return_value = mock_structured

    client = LangChainLLMClient(
        primary_provider="openai",
        openai_model_name="test-concurrent-reasoning-model",
        openai_chat_model=mock_openai,
        temperature=0.0,
    )

    results = []
    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = [
            executor.submit(client.generate_structured, f"Extract {i}", SampleSchema)
            for i in range(14)
        ]
        for f in futures:
            results.append(f.result())

    assert len(results) == 14
    for r in results:
        assert isinstance(r, SampleSchema)
        assert r.title == "Concurrent Success"
    assert client.temperature is None
    assert mock_openai.temperature is None


def test_openai_new_client_inherits_unsupported_model_cache():
    """Verify that a newly instantiated client recognizes models recorded in _UNSUPPORTED_TEMPERATURE_MODELS
    and configures them with temperature=None from the start."""
    from src.llm.client import _UNSUPPORTED_TEMPERATURE_MODELS

    _UNSUPPORTED_TEMPERATURE_MODELS.add("cached-reasoning-model")

    client = LangChainLLMClient(
        primary_provider="openai",
        openai_model_name="cached-reasoning-model",
        openai_api_key="sk-fake",
        temperature=0.0,
    )

    assert client._openai_chat_model.temperature is None
