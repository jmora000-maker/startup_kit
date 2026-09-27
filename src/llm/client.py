"""LLM Client implementations using LangChain and offline Mock clients."""

import logging
from typing import Type, TypeVar, Optional, Any
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from src.core.interfaces import ILLMClient

logger = logging.getLogger(__name__)
T = TypeVar("T")


class LangChainLLMClient(ILLMClient):
    """LangChain wrapper client supporting OpenAI and structured outputs."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gpt-4o",
        temperature: float = 0.0,
        chat_model: Optional[Any] = None,
    ):
        self.model_name = model_name
        self.temperature = temperature
        self.api_key = api_key

        if chat_model is not None:
            self._chat_model = chat_model
        elif api_key:
            self._chat_model = ChatOpenAI(
                model=model_name,
                temperature=temperature,
                api_key=api_key,
            )
        else:
            self._chat_model = None

    def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None
    ) -> T:
        if self._chat_model is None:
            raise ValueError(
                "LLM client is not initialized with an API key. "
                "Please set OPENAI_API_KEY environment variable or pass a mock chat model."
            )

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        try:
            structured_llm = self._chat_model.with_structured_output(schema)
            result = structured_llm.invoke(messages)
            if isinstance(result, schema):
                return result
            if isinstance(result, dict):
                return schema.model_validate(result)
            return schema.model_validate(result)
        except Exception as exc:
            logger.warning("Structured output invoke failed, falling back to PydanticOutputParser: %s", exc)
            # Fallback to parser
            parser = PydanticOutputParser(pydantic_object=schema)
            format_instructions = parser.get_format_instructions()
            fallback_prompt = f"{prompt}\n\n{format_instructions}"
            response = self.generate_text(fallback_prompt, system_prompt=system_prompt)
            return parser.parse(response)

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        if self._chat_model is None:
            raise ValueError("LLM client has no API key configured.")

        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        response = self._chat_model.invoke(messages)
        return response.content if hasattr(response, "content") else str(response)


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
