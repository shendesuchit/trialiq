"""Backward-compatible LangChain model factory.

New application code should use :mod:`trialiq.llm.service`. This module remains
for narrow compatibility with existing injected-model tests and callers.
"""

from langchain_core.language_models.chat_models import BaseChatModel

from trialiq.config.settings import get_settings
from trialiq.llm.providers import LangChainProviderAdapter, create_provider_adapter


def _require_value(value: str | None, setting_name: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"Required LLM configuration is missing: {setting_name}")
    return value


def create_llm() -> BaseChatModel:
    settings = get_settings()
    provider = settings.llm_provider
    if provider == "auto":
        raise ValueError(
            "create_llm() requires an explicit provider; use LLMService for auto selection."
        )
    if provider not in {"openai", "gemini", "openrouter"}:
        raise ValueError(f"Unsupported LLM provider configured: {provider}")

    _require_value(
        getattr(settings, f"{provider}_api_key", None),
        f"{provider.upper()}_API_KEY",
    )
    _require_value(
        getattr(settings, f"{provider}_model", None),
        f"{provider.upper()}_MODEL",
    )
    adapter = create_provider_adapter(settings, provider)
    if not isinstance(adapter, LangChainProviderAdapter):
        raise TypeError("Configured provider did not create a LangChain adapter.")
    return adapter.client
