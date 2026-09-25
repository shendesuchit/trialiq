"""Provider-agnostic LLM runtime service with bounded failover."""

from __future__ import annotations

import logging
from functools import lru_cache
from time import perf_counter
from typing import Any, Callable, TypeVar

from langchain_core.messages import BaseMessage
from pydantic import BaseModel

from trialiq.config.settings import Settings, get_llm_provider_priority, get_settings

from .models import (
    LLMInvocationMetadata,
    LLMProviderHealth,
    LLMRuntimeStatus,
    LLMTextResponse,
)
from .providers import (
    LLMProviderAdapter,
    create_provider_adapter,
    provider_configuration,
)

logger = logging.getLogger(__name__)
StructuredModelT = TypeVar("StructuredModelT", bound=BaseModel)
AdapterFactory = Callable[[Settings, str], LLMProviderAdapter]


class LLMUnavailableError(RuntimeError):
    """Raised when no configured provider can complete an invocation.

    Only non-secret operational metadata is attached so callers can expose a
    bounded diagnostic trace without leaking provider credentials or raw errors.
    """

    def __init__(
        self,
        message: str,
        *,
        attempted_providers: list[str] | None = None,
        failover_reason: str | None = None,
        error_category: str | None = None,
        latency_ms: float | None = None,
    ):
        super().__init__(message)
        self.attempted_providers = attempted_providers or []
        self.failover_reason = failover_reason
        self.error_category = error_category
        self.latency_ms = latency_ms


def _error_category(exc: Exception) -> str:
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if "timeout" in name or "timeout" in message:
        return "timeout"
    if "auth" in name or "api key" in message or "unauthorized" in message:
        return "authentication"
    if "rate" in name or "quota" in message or "429" in message:
        return "rate_limit"
    if isinstance(exc, (ValueError, TypeError)):
        return "configuration"
    return "provider_error"


def _message_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                value = item.get("text")
                if isinstance(value, str):
                    parts.append(value)
        return "\n".join(parts).strip()
    return str(content).strip()


class LLMService:
    """Own provider selection, health checks, invocation and failover."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        adapter_factory: AdapterFactory = create_provider_adapter,
    ):
        self.settings = settings or get_settings()
        self.adapter_factory = adapter_factory
        self._runtime_status = LLMRuntimeStatus()
        self._active_provider: str | None = None

    def _ordered_candidates(self) -> list[str]:
        priority = get_llm_provider_priority(self.settings)
        if self.settings.llm_provider != "auto":
            return [self.settings.llm_provider]
        return priority

    def _configured_candidates(self) -> list[str]:
        return [
            provider
            for provider in self._ordered_candidates()
            if provider_configuration(self.settings, provider) is not None
        ]

    def preflight(self, *, probe: bool | None = None) -> LLMRuntimeStatus:
        """Select a usable provider, optionally verifying it with real inference."""
        should_probe = self.settings.llm_startup_probe if probe is None else probe
        provider_health: list[LLMProviderHealth] = []
        selected_provider: str | None = None
        selected_model: str | None = None

        for provider in self._ordered_candidates():
            configured = provider_configuration(self.settings, provider)
            if configured is None:
                provider_health.append(
                    LLMProviderHealth(provider=provider, configured=False, healthy=False)
                )
                continue

            _, model = configured
            started = perf_counter()
            if not should_probe:
                provider_health.append(
                    LLMProviderHealth(
                        provider=provider,
                        model=model,
                        configured=True,
                        healthy=True,
                        latency_ms=round((perf_counter() - started) * 1000, 3),
                    )
                )
                selected_provider = provider
                selected_model = model
                break

            try:
                adapter = self.adapter_factory(self.settings, provider)
                response = adapter.invoke("Reply with exactly OK.")
                if not _message_text(response):
                    raise ValueError("LLM startup probe returned an empty response.")
                provider_health.append(
                    LLMProviderHealth(
                        provider=provider,
                        model=model,
                        configured=True,
                        healthy=True,
                        latency_ms=round((perf_counter() - started) * 1000, 3),
                    )
                )
                selected_provider = provider
                selected_model = model
                break
            except Exception as exc:
                category = _error_category(exc)
                logger.warning(
                    "LLM startup probe failed provider=%s model=%s category=%s",
                    provider,
                    model,
                    category,
                )
                provider_health.append(
                    LLMProviderHealth(
                        provider=provider,
                        model=model,
                        configured=True,
                        healthy=False,
                        latency_ms=round((perf_counter() - started) * 1000, 3),
                        error_category=category,
                    )
                )

        self._active_provider = selected_provider
        self._runtime_status = LLMRuntimeStatus(
            healthy=selected_provider is not None,
            selected_provider=selected_provider,
            selected_model=selected_model,
            providers=provider_health,
        )
        return self._runtime_status

    def status(self) -> LLMRuntimeStatus:
        return self._runtime_status

    def _invocation_candidates(self) -> list[str]:
        configured = self._configured_candidates()
        if not configured:
            return []
        if self._active_provider in configured:
            return [
                self._active_provider,
                *[provider for provider in configured if provider != self._active_provider],
            ]
        return configured

    def _invoke(
        self,
        operation: Callable[[LLMProviderAdapter], Any],
    ) -> tuple[Any, LLMInvocationMetadata]:
        invocation_started = perf_counter()
        candidates = self._invocation_candidates()
        if not candidates:
            raise LLMUnavailableError(
                "No configured LLM provider is available.",
                attempted_providers=[],
                error_category="unavailable",
                latency_ms=round((perf_counter() - invocation_started) * 1000, 3),
            )

        attempted: list[str] = []
        failover_reason: str | None = None
        last_error: Exception | None = None

        for provider in candidates:
            attempted.append(provider)
            configured = provider_configuration(self.settings, provider)
            if configured is None:
                continue
            _, model = configured
            started = perf_counter()
            try:
                adapter = self.adapter_factory(self.settings, provider)
                result = operation(adapter)
                latency_ms = round((perf_counter() - started) * 1000, 3)
                if provider != self._active_provider:
                    logger.warning(
                        "LLM failover selected provider=%s model=%s attempted=%s reason=%s",
                        provider,
                        model,
                        attempted,
                        failover_reason,
                    )
                self._active_provider = provider
                self._runtime_status = self._runtime_status.model_copy(
                    update={
                        "healthy": True,
                        "selected_provider": provider,
                        "selected_model": model,
                    }
                )
                return result, LLMInvocationMetadata(
                    provider=provider,
                    model=model,
                    attempted_providers=attempted.copy(),
                    failover_reason=failover_reason,
                    latency_ms=latency_ms,
                )
            except Exception as exc:
                last_error = exc
                category = _error_category(exc)
                failover_reason = category
                logger.warning(
                    "LLM invocation failed provider=%s model=%s category=%s",
                    provider,
                    model,
                    category,
                )
                if self.settings.llm_provider != "auto":
                    break

        category = _error_category(last_error) if last_error else "unavailable"
        raise LLMUnavailableError(
            f"All eligible LLM providers failed; category={category}; attempted={attempted}",
            attempted_providers=attempted.copy(),
            failover_reason=failover_reason,
            error_category=category,
            latency_ms=round((perf_counter() - invocation_started) * 1000, 3),
        ) from last_error

    def invoke_text(self, messages: Any) -> LLMTextResponse:
        def operation(adapter: LLMProviderAdapter) -> str:
            text = _message_text(adapter.invoke(messages))
            if not text:
                raise RuntimeError("LLM provider returned an empty response.")
            return text

        text, metadata = self._invoke(operation)
        return LLMTextResponse(text=text, metadata=metadata)

    def invoke_structured(
        self,
        messages: Any,
        schema: type[StructuredModelT],
    ) -> tuple[StructuredModelT, LLMInvocationMetadata]:
        result, metadata = self._invoke(
            lambda adapter: adapter.invoke_structured(messages, schema)
        )
        if not isinstance(result, schema):
            raise TypeError("LLM returned an unexpected structured-output type.")
        return result, metadata


@lru_cache
def get_llm_service() -> LLMService:
    return LLMService()
