# LLM-01, LLM-02, LLM-03 Implementation and Fallback Fix Report

### Executive Summary

This report documents the implementation, verification, and empirical testing for requirements **LLM-01**, **LLM-02**, and **LLM-03** from `spec/PMO_Startup_Kit_Consolidated_Spec.md` (Revision 30, Section 17 Item 0 and Section 15C).

The work resolves a critical failure mode where Anthropic-to-OpenAI fallback failed due to client parameter ceiling mismatches (`MAX_TOKENS=32768` vs `gpt-4o` 16,384 ceiling), establishes symmetrical reverse fallback (OpenAI-to-Anthropic), detects truncated completions (`finish_reason == "length"` and `stop_reason == "max_tokens"`), and guarantees clean stage-level error propagation (`"{stage} failed: {reason}"`) without raw traceback leaks.

---

### Spec Requirements (Revision 30, Literal `Select-String` Output)

```markdown
| LLM-01 | **Provider-specific token limits.** Every LLM client call uses a `max_tokens` value clamped to the ceiling the target provider and model actually support, never a single shared value passed blindly to whichever provider is called, including a fallback call to a different provider than the one the value was tuned for. Each internal fallback tier (native structured output, prompt-based JSON extraction, a second structured attempt, a final parser-based attempt) independently respects this. | New (bug found via Appendix X; `MAX_TOKENS=32768`, correct for Anthropic, silently broke every Anthropic-to-OpenAI fallback call against `gpt-4o`, whose ceiling is 16384) | `test_llm_client.py` |
| LLM-02 | **Symmetric fallback.** Anthropic-primary falls back to OpenAI on failure (existing; confirmed working once `LLM-01`'s bug is fixed). OpenAI-primary falls back to Anthropic on failure, the reverse direction, which does not exist today (confirmed absent during investigation). Both directions use the same per-provider token-limit correctness (`LLM-01`). | New | `test_llm_client.py` |
| LLM-03 | **Fail gracefully when every provider is exhausted.** If the primary call and every fallback attempt all fail, for any reason, the orchestrator never lets a raw, unhandled exception propagate to either front end. It raises one clear, specific error (the same shape `HTL-26` already specifies for the app: `"{stage} failed: {reason}"`) at the client/orchestrator level, so both the CLI and the app surface a clean message, not just the app. This also covers a response that technically succeeds but is truncated: every provider's response is checked for its own truncation signal (Anthropic's `stop_reason == "max_tokens"`, OpenAI's `finish_reason == "length"`), and a truncated response is treated as a failure -- raising the same clear error -- never silently parsed or returned as if it were complete. `LLM-01`'s token-limit clamp alone does not guarantee this: a genuinely large response can still truncate even when `max_tokens` is validly set to a provider's own ceiling (Appendix X). | New | `test_llm_client.py`, `test_orchestrator.py` |
```

---

### Step 1: Reproduction of Bug Before Fix

#### Reproduction Script
```python
from langchain_openai import ChatOpenAI
from src.config import config

llm = ChatOpenAI(model='gpt-4o', max_tokens=32768, api_key=config.openai_api_key)
llm.invoke('Hi')
```

#### Literal Captured Terminal Output (Before Fix)
```text
Caught expected exception:
OpenAIInvalidRequestError : Error code: 400 - {'error': {'message': 'max_tokens is too large: 32768. This model supports at most 16384 completion tokens, whereas you provided 32768.', 'type': 'invalid_request_error', 'param': 'max_tokens', 'code': 'invalid_value'}}
```

---

### Step 2: Fix LLM-01 (Provider-Specific Token Limits)

- **Implementation**:
  - Implemented `get_clamped_max_tokens(provider, model_name, requested_tokens)` in `src/llm/client.py`.
  - OpenAI models (`gpt-4o`, `gpt-4o-mini`, etc.) are clamped to 16,384 (or 4,096 for `gpt-4-turbo`/`gpt-3.5`, 65,536 for `o1`/`o3`).
  - Anthropic models retain up to 64,000 completion tokens.
  - Initialized `self.anthropic_max_tokens` and `self.openai_max_tokens` on `LangChainLLMClient`, ensuring all chat model invocations and internal fallback tiers inherit provider-safe token ceilings.
- **Commit**: `e4d4766 LLM-01: clamp max_tokens per provider and model ceiling`
- **Pytest Summary Line**: `649 passed in 173.05s (0:02:53)`

#### Literal Captured Terminal Output (After LLM-01 Fix)
```text
Configured max_tokens: 32768
Anthropic clamped max_tokens: 32768
OpenAI clamped max_tokens: 16384
ChatOpenAI internal max_tokens: 16384
Real OpenAI call result: Hello there!
```

---

### Step 3: Fix LLM-02 (Symmetric OpenAI-to-Anthropic Fallback)

- **Implementation**:
  - Added `primary_provider` parameter to `LangChainLLMClient`.
  - Implemented symmetric reverse fallback in `generate_structured`:
    - Native OpenAI structured output -> OpenAI schema-instructed JSON extraction -> Anthropic native structured output -> Anthropic prompt-based JSON extraction.
  - Implemented symmetric reverse fallback in `generate_text`:
    - OpenAI text invocation -> Anthropic text invocation failover.
  - Updated `build_llm_client` in `src/orchestrator.py` so that when `provider="openai"`, both OpenAI and Anthropic credentials are configured, establishing Anthropic as the active fallback.
- **Commit**: `630fc79 LLM-02: symmetric OpenAI-to-Anthropic fallback`
- **Pytest Summary Line**: `652 passed in 293.93s (0:04:53)`

---

### Step 4: Fix LLM-03 (Graceful Error Propagation & Truncation Handling)

- **Implementation**:
  - **4a (Raw Exception Propagation)**: Wrapped multi-pass concurrent extractions, validation, and generation in `StartupKitController.run()`. When LLM providers are exhausted or stage execution fails, raises `RuntimeError("{stage} failed: {reason}")` without raw stack trace leaks, which integrates cleanly with both CLI logging and Streamlit UI (`format_run_error`).
  - **4b (Silent Truncation Detection)**: Added OpenAI truncation signal detection (`finish_reason == "length"` in `response_metadata` and `additional_kwargs`) mirroring Anthropic's `stop_reason == "max_tokens"`. Raises explicit `RuntimeError` on truncated completions, preventing corrupted or partial payloads from being parsed as valid data.
- **Commit**: `3504287 LLM-03: graceful stage error propagation and finish_reason truncation handling`
- **Pytest Summary Line**: `656 passed in 192.48s (0:03:12)`

---

### End-to-End Fallback Verification

Re-running the exact reproduction through `generate_structured` with `max_tokens=32768` (simulating Anthropic failure at the network boundary and executing a real OpenAI call):

```text
=== RE-RUNNING END-TO-END REPRODUCTION WITH MAX_TOKENS=32768 ===
Client max_tokens: 32768
Client Anthropic max_tokens: 32768
Client OpenAI max_tokens: 16384
Internal _openai_chat_model max_tokens: 16384
WARNING: Anthropic native structured output failed (BadRequestError): Error code: 400 - You have reached your specified workspace API usage limits.. Attempting Anthropic schema-instructed JSON extraction...
WARNING: Anthropic schema-instructed JSON extraction failed (BadRequestError): Error code: 400 - You have reached your specified workspace API usage limits.
...
INFO: Falling back to OpenAI model 'gpt-4o' for schema 'ProjectSummarySchema' after Anthropic failure...
INFO: HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"

Final generate_structured result from OpenAI fallback:
Result type: ProjectSummarySchema
Result content: title='Cloud Platform' status='In Progress'
Fallback domains: ['ProjectSummarySchema']
=== END REPRODUCTION ===
```

---

### Test Suite Execution Summary

| Checkpoint | Pytest Summary Output |
| :--- | :--- |
| **Initial Baseline** | `648 passed in 230.01s (0:03:50)` |
| **After Step 2 (LLM-01)** | `649 passed in 173.05s (0:02:53)` |
| **After Step 3 (LLM-02)** | `652 passed in 293.93s (0:04:53)` |
| **After Step 4 (LLM-03)** | `656 passed in 192.48s (0:03:12)` |

---

### Verification Code Samples

#### 1. LLM-02 Reverse Fallback (`tests/test_llm_client.py`)
```python
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

    result = client.generate_structured("Extract project", SampleSchema)
    assert result.title == "Anthropic Reverse Fallback"
    assert result.score == 95
    assert "SampleSchema" in client.fallback_domains
```

#### 2. LLM-03 Stage Error Propagation (`tests/test_orchestrator.py`)
```python
def test_orchestrator_exhausted_providers_raises_clear_stage_error(tmp_path):
    """Verify LLM-03 (4a): when extraction fails across all providers, orchestrator raises clear stage error."""
    mock_anthropic = MagicMock()
    mock_anthropic.with_structured_output.side_effect = RuntimeError("Anthropic 429 RateLimit")
    mock_anthropic.invoke.side_effect = RuntimeError("Anthropic 429 RateLimit")

    mock_openai = MagicMock()
    mock_openai.with_structured_output.side_effect = RuntimeError("OpenAI 429 QuotaExceeded")
    mock_openai.invoke.side_effect = RuntimeError("OpenAI 429 QuotaExceeded")

    client = LangChainLLMClient(
        primary_provider="anthropic",
        chat_model=mock_anthropic,
        openai_chat_model=mock_openai,
    )

    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    (inputs_dir / "sow.txt").write_text("Statement of Work content", encoding="utf-8")
    output_dir = tmp_path / "output"

    controller = StartupKitController(llm_client=client)

    with pytest.raises(RuntimeError) as exc_info:
        controller.run(inputs_dir=inputs_dir, output_dir=output_dir)

    err_str = str(exc_info.value)
    assert err_str.startswith("extraction failed:")
    assert "OpenAI 429 QuotaExceeded" in err_str
    assert "Traceback (most recent call last)" not in err_str
```

#### 3. LLM-03 Truncation Signal Detection (`tests/test_llm_client.py`)
```python
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
```

---

### Stash Confirmation

`git stash list` confirms the set-aside HTL-13 work remains preserved:
```text
stash@{0}: On main: WIP HTL-13 review storage
```
