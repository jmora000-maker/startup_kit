"""LLM Client implementations using LangChain and offline Mock clients."""

import json
import logging
import re
from typing import Type, TypeVar, Optional, Any
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from src.core.interfaces import ILLMClient
from src.config import config, resolve_anthropic_model
from src.llm.caching_client import CachingLLMClient, LLMCacheMiss, compute_cache_key

logger = logging.getLogger(__name__)
T = TypeVar("T")


# Pre-seeded cache of schemas that exceed Anthropic native CFG grammar compilation limits
_KNOWN_COMPLEX_SCHEMAS: set[str] = {
    "CharterExtraction",
    "DeliverablesExtraction",
    "MilestonesExtraction",
    "RAIDExtraction",
    "QuestionsExtraction",
    "SOWInterpretationExtraction",
    "ScopeDecompositionExtraction",
    "AcceptanceProcessExtraction",
    "StakeholdersExtraction",
    "CommunicationsExtraction",
    "CommercialGuardrailsExtraction",
    "TalentOnboardingExtraction",
    "DecisionsExtraction",
    "ContractConflictsExtraction",
}
_COMPLEX_SCHEMAS: set[str] = set(_KNOWN_COMPLEX_SCHEMAS)


def is_complex_schema(schema: Type[Any]) -> bool:
    """Determine if a Pydantic schema exceeds Anthropic native constrained grammar limits."""
    schema_name = getattr(schema, "__name__", str(schema))
    if schema_name in _COMPLEX_SCHEMAS:
        return True
    if hasattr(schema, "model_json_schema"):
        try:
            js = schema.model_json_schema()
            defs = js.get("$defs", {})
            properties = js.get("properties", {})
            if len(defs) >= 1 or len(properties) >= 6:
                _COMPLEX_SCHEMAS.add(schema_name)
                return True
        except Exception:
            pass
    return False


def extract_text_content(content: Any) -> str:
    """Extract plain text string from str, list of content blocks, or AIMessage objects.

    Filters out thinking blocks, signatures, tool calls, and other non-text artifacts.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                block_type = block.get("type")
                if block_type == "text":
                    parts.append(str(block.get("text", "")))
                elif block_type is None and "text" in block:
                    parts.append(str(block["text"]))
                # Note: thinking, signature, tool_use, redacted_thinking blocks are explicitly skipped
            elif hasattr(block, "type"):
                if getattr(block, "type") == "text":
                    parts.append(str(getattr(block, "text", "")))
            elif hasattr(block, "text"):
                parts.append(str(getattr(block, "text", "")))
        return "".join(parts)
    if hasattr(content, "content"):
        return extract_text_content(content.content)
    return str(content) if content is not None else ""


def parse_json_response_to_schema(text: Any, schema: Type[T], parser: Optional[PydanticOutputParser] = None) -> T:
    """Parse JSON or markdown-fenced JSON text into a validated Pydantic model instance."""
    raw_str = extract_text_content(text).strip()
    cleaned = raw_str
    # Strip markdown code blocks if present (```json ... ``` or ``` ... ```)
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if match:
        cleaned = match.group(1).strip()
    else:
        # If text contains preamble/postamble, extract from outermost JSON object braces
        first_brace = cleaned.find("{")
        last_brace = cleaned.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            cleaned = cleaned[first_brace:last_brace + 1]

    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return schema.model_validate(data)
        if isinstance(data, list) and hasattr(schema, "model_validate"):
            return schema.model_validate(data)
    except Exception as json_exc:
        logger.debug("Direct json.loads failed (%s), trying PydanticOutputParser: %s", json_exc, raw_str[:200])

    if parser is None:
        parser = PydanticOutputParser(pydantic_object=schema)
    try:
        return parser.parse(cleaned)
    except Exception:
        return parser.parse(raw_str)


class LangChainLLMClient(ILLMClient):
    """LangChain wrapper client supporting Anthropic Claude with OpenAI fallback and structured outputs."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        chat_model: Optional[Any] = None,
        openai_api_key: Optional[str] = None,
        openai_model_name: Optional[str] = None,
        openai_chat_model: Optional[Any] = None,
        max_tokens: Optional[int] = None,
    ):
        self.api_key = api_key if api_key is not None else config.anthropic_api_key
        raw_model = model_name or config.anthropic_model
        self.model_name = resolve_anthropic_model(raw_model)
        self.temperature = temperature if temperature is not None else config.temperature
        self.openai_api_key = openai_api_key if openai_api_key is not None else config.openai_api_key
        self.openai_model_name = openai_model_name or config.openai_model
        self.max_tokens = max_tokens if max_tokens is not None else getattr(config, "max_tokens", 16384)
        self.fallback_domains: list[str] = []

        # Primary Anthropic model
        if chat_model is not None:
            self._chat_model = chat_model
        elif self.api_key:
            # Modern Anthropic Claude models (e.g. claude-sonnet-5-5, Opus 5.5, reasoning models)
            # deprecate the temperature parameter and return 400 Bad Request if passed.
            # Setting temperature=None ensures ChatAnthropic omits temperature from API payloads.
            self._chat_model = ChatAnthropic(
                model=self.model_name,
                temperature=None,
                api_key=self.api_key,
                max_tokens=self.max_tokens,
            )
        else:
            self._chat_model = None

        # Secondary OpenAI model (fallback or primary if Anthropic key is omitted)
        if openai_chat_model is not None:
            self._openai_chat_model = openai_chat_model
        elif self.openai_api_key:
            self._openai_chat_model = ChatOpenAI(
                model=self.openai_model_name,
                temperature=self.temperature,
                api_key=self.openai_api_key,
                max_tokens=self.max_tokens,
            )
        else:
            self._openai_chat_model = None

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None
    ) -> T:
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        schema_name = getattr(schema, "__name__", str(schema))

        # 1. Attempt primary Anthropic model if configured
        if self._chat_model is not None:
            # Check if schema is known or detected to exceed Anthropic native grammar compilation limits
            skip_native = is_complex_schema(schema)
            if skip_native:
                logger.info(
                    "Schema '%s' is identified as complex. Directly executing Anthropic schema-instructed JSON extraction...",
                    schema_name,
                )
            else:
                # Step 1a: Attempt Anthropic native structured outputs
                try:
                    structured_llm = self._chat_model.with_structured_output(schema, method="json_schema")
                    result = structured_llm.invoke(messages)
                    if isinstance(result, schema):
                        return result
                    if isinstance(result, dict):
                        return schema.model_validate(result)
                    return schema.model_validate(result)
                except Exception as anthropic_exc:
                    err_msg = str(anthropic_exc).lower()
                    if "schema is too complex" in err_msg or "invalid_request_error" in err_msg:
                        _COMPLEX_SCHEMAS.add(schema_name)
                    logger.warning(
                        "Anthropic native structured output failed (%s): %s. Attempting Anthropic schema-instructed JSON extraction...",
                        type(anthropic_exc).__name__,
                        anthropic_exc,
                    )

            # Step 1b: Attempt Anthropic prompt-based JSON extraction with schema format instructions
            try:
                parser = PydanticOutputParser(pydantic_object=schema)
                format_instructions = parser.get_format_instructions()
                fallback_prompt = (
                    f"{prompt}\n\n"
                    f"IMPORTANT: Output your response as a valid JSON object strictly conforming to the following JSON schema. "
                    f"Do not include preamble, conversational remarks, or markdown text outside the JSON object.\n\n"
                    f"{format_instructions}"
                )
                response_text = self.generate_text(fallback_prompt, system_prompt=system_prompt, force_openai=False)
                return parse_json_response_to_schema(response_text, schema, parser)
            except Exception as anthropic_text_exc:
                logger.warning(
                    "Anthropic schema-instructed JSON extraction failed (%s): %s",
                    type(anthropic_text_exc).__name__,
                    anthropic_text_exc,
                    exc_info=True,
                )
                # Step 1c: If OpenAI fallback is available, fail over to OpenAI
                if self._openai_chat_model is not None:
                    if schema_name not in self.fallback_domains:
                        self.fallback_domains.append(schema_name)
                    logger.info(
                        "Falling back to OpenAI model '%s' for schema '%s' after Anthropic failure...",
                        self.openai_model_name,
                        schema_name,
                    )
                    try:
                        structured_openai = self._openai_chat_model.with_structured_output(schema)
                        result = structured_openai.invoke(messages)
                        if isinstance(result, schema):
                            return result
                        if isinstance(result, dict):
                            return schema.model_validate(result)
                        return schema.model_validate(result)
                    except Exception as openai_exc:
                        logger.warning(
                            "OpenAI structured invoke failed (%s): %s. Falling back to PydanticOutputParser via OpenAI.",
                            type(openai_exc).__name__,
                            openai_exc,
                            exc_info=True,
                        )
                        parser = PydanticOutputParser(pydantic_object=schema)
                        format_instructions = parser.get_format_instructions()
                        fallback_prompt = f"{prompt}\n\n{format_instructions}"
                        response = self.generate_text(fallback_prompt, system_prompt=system_prompt, force_openai=True)
                        return parse_json_response_to_schema(response, schema, parser)
                else:
                    raise anthropic_text_exc

        # 2. If Anthropic is not configured, attempt OpenAI directly
        elif self._openai_chat_model is not None:
            try:
                structured_openai = self._openai_chat_model.with_structured_output(schema)
                result = structured_openai.invoke(messages)
                if isinstance(result, schema):
                    return result
                if isinstance(result, dict):
                    return schema.model_validate(result)
                return schema.model_validate(result)
            except Exception as openai_exc:
                logger.warning(
                    "OpenAI structured invoke failed (%s): %s. Falling back to PydanticOutputParser via OpenAI.",
                    type(openai_exc).__name__,
                    openai_exc,
                    exc_info=True,
                )
                parser = PydanticOutputParser(pydantic_object=schema)
                format_instructions = parser.get_format_instructions()
                fallback_prompt = f"{prompt}\n\n{format_instructions}"
                response = self.generate_text(fallback_prompt, system_prompt=system_prompt)
                return parse_json_response_to_schema(response, schema, parser)

        else:
            raise ValueError(
                "LLM client is not initialized with an API key. "
                "Please set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable or pass a mock chat model."
            )

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        force_openai: bool = False,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        if not force_openai and self._chat_model is not None:
            try:
                response = self._chat_model.invoke(messages)
                stop_reason = None
                if hasattr(response, "response_metadata") and isinstance(response.response_metadata, dict):
                    stop_reason = response.response_metadata.get("stop_reason")
                elif hasattr(response, "additional_kwargs") and isinstance(response.additional_kwargs, dict):
                    stop_reason = response.additional_kwargs.get("stop_reason")
                if stop_reason == "max_tokens":
                    logger.error(
                        "Anthropic response was truncated due to reaching max_tokens (%d). Output is incomplete.",
                        self.max_tokens,
                    )
                    raise RuntimeError(
                        f"Anthropic response was truncated due to reaching max_tokens ({self.max_tokens}). "
                        "Payload is incomplete and cannot be parsed safely."
                    )
                return extract_text_content(response.content if hasattr(response, "content") else response)
            except Exception as anthropic_exc:
                logger.warning(
                    "Anthropic text generation failed (%s): %s",
                    type(anthropic_exc).__name__,
                    anthropic_exc,
                    exc_info=True,
                )
                if self._openai_chat_model is not None:
                    if "TextGeneration" not in self.fallback_domains:
                        self.fallback_domains.append("TextGeneration")
                    logger.info(
                        "Falling back to OpenAI text generation ('%s')...",
                        self.openai_model_name,
                    )
                    response = self._openai_chat_model.invoke(messages)
                    return extract_text_content(response.content if hasattr(response, "content") else response)
                raise anthropic_exc
        elif self._openai_chat_model is not None:
            response = self._openai_chat_model.invoke(messages)
            return extract_text_content(response.content if hasattr(response, "content") else response)
        else:
            raise ValueError(
                "LLM client has no API key configured. "
                "Please set ANTHROPIC_API_KEY or OPENAI_API_KEY."
            )


class MockLLMClient(ILLMClient):
    """Deterministic Mock LLM client for offline unit and integration tests."""

    def __init__(self, responses_by_schema: Optional[dict] = None):
        self.responses_by_schema = responses_by_schema or {}
        self.call_history = []

    def set_response(self, schema: Type[Any], response_obj: Any):
        self.responses_by_schema[schema] = response_obj

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None
    ) -> T:
        self.call_history.append({
            "type": "structured",
            "prompt": prompt,
            "schema": schema,
            "system_prompt": system_prompt
        })
        if schema in self.responses_by_schema:
            res = self.responses_by_schema[schema]
            if isinstance(res, schema):
                return res
            if isinstance(res, dict):
                return schema.model_validate(res)
            return res
        # If not explicitly mapped, try instantiating default empty schema
        try:
            return schema()
        except Exception:
            raise KeyError(f"No mock response configured for schema {schema.__name__}")

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        self.call_history.append({
            "type": "text",
            "prompt": prompt,
            "system_prompt": system_prompt
        })
        return "Mock response for prompt."
