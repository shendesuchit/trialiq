"""Provider adapters for TrialIQ's LLM service."""

from __future__ import annotations

from typing import Any, Protocol, TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from trialiq.config.settings import Settings


StructuredModelT = TypeVar("StructuredModelT", bound=BaseModel)


class LLMProviderAdapter(Protocol):
    name: str
    model: str

    def invoke(self, messages: Any) -> BaseMessage:
        ...

    def invoke_structured(
        self,
        messages: Any,
        schema: type[StructuredModelT],
    ) -> StructuredModelT:
        ...


class LangChainProviderAdapter:
    """Thin adapter around one LangChain chat model."""

    def __init__(self, name: str, model: str, client: BaseChatModel):
        self.name = name
        self.model = model
        self.client = client

    def invoke(self, messages: Any) -> BaseMessage:
        return self.client.invoke(messages)

    def invoke_structured(
        self,
        messages: Any,
        schema: type[StructuredModelT],
    ) -> StructuredModelT:
        result = self.client.with_structured_output(schema).invoke(messages)
        if not isinstance(result, schema):
            raise TypeError("LLM returned an unexpected structured-output type.")
        return result


def _require_value(value: str | None, setting_name: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"Required LLM configuration is missing: {setting_name}")
    return value.strip()


def provider_configuration(settings: Settings, provider: str) -> tuple[str, str] | None:
    """Return ``(api_key, model)`` when a provider is fully configured."""
    api_key = getattr(settings, f"{provider}_api_key", None)
    model = getattr(settings, f"{provider}_model", None)
    if not isinstance(api_key, str) or not api_key.strip():
        return None
    if not isinstance(model, str) or not model.strip():
        return None
    return api_key.strip(), model.strip()


def create_provider_adapter(settings: Settings, provider: str) -> LLMProviderAdapter:
    """Create one configured provider adapter without exposing SDK types upstream."""
    configured = provider_configuration(settings, provider)
    if configured is None:
        raise ValueError(f"LLM provider is not fully configured: {provider}")
    api_key, model = configured
    timeout = settings.llm_request_timeout_seconds
    max_retries = settings.llm_max_retries

    if provider == "openai":
        client = ChatOpenAI(
            model=model,
            api_key=api_key,
            temperature=0,
            timeout=timeout,
            max_retries=max_retries,
        )
    elif provider == "openrouter":
        client = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=settings.openrouter_base_url,
            temperature=0,
            timeout=timeout,
            max_retries=max_retries,
        )
    elif provider == "gemini":
        client = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=0,
            timeout=timeout,
            max_retries=max_retries,
        )
    else:
        raise ValueError(f"Unsupported LLM provider configured: {provider}")

    return LangChainProviderAdapter(provider, model, client)
