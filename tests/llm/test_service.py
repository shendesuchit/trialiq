from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from trialiq.llm.service import LLMService, LLMUnavailableError


class FakeAdapter:
    def __init__(self, name, model, *, fail=False):
        self.name = name
        self.model = model
        self.fail = fail

    def invoke(self, messages):
        if self.fail:
            raise TimeoutError(f"{self.name} timed out")
        return AIMessage(content=f"ok from {self.name}")

    def invoke_structured(self, messages, schema):
        if self.fail:
            raise TimeoutError(f"{self.name} timed out")
        return schema(intent="UNSUPPORTED")


def settings(**overrides):
    values = dict(
        llm_provider="auto",
        llm_provider_priority="openai,gemini,openrouter",
        llm_startup_probe=True,
        llm_request_timeout_seconds=10.0,
        llm_max_retries=0,
        openai_api_key="openai-key",
        openai_model="openai-model",
        gemini_api_key="gemini-key",
        gemini_model="gemini-model",
        openrouter_api_key="openrouter-key",
        openrouter_model="openrouter-model",
        openrouter_base_url="https://openrouter.ai/api/v1",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def test_preflight_selects_first_healthy_provider():
    def factory(_settings, provider):
        return FakeAdapter(provider, f"{provider}-model", fail=provider == "openai")

    service = LLMService(settings(), adapter_factory=factory)
    status = service.preflight()

    assert status.healthy is True
    assert status.selected_provider == "gemini"
    assert status.selected_model == "gemini-model"
    assert [item.provider for item in status.providers] == ["openai", "gemini"]
    assert status.providers[0].error_category == "timeout"


def test_runtime_invocation_fails_over_once_in_auto_mode():
    failing = {"openai": False, "gemini": False}

    def factory(_settings, provider):
        return FakeAdapter(provider, f"{provider}-model", fail=failing.get(provider, False))

    service = LLMService(settings(), adapter_factory=factory)
    service.preflight()
    failing["openai"] = True

    response = service.invoke_text("hello")

    assert response.text == "ok from gemini"
    assert response.metadata.provider == "gemini"
    assert response.metadata.attempted_providers == ["openai", "gemini"]
    assert response.metadata.failover_reason == "timeout"


def test_explicit_provider_does_not_silently_fail_over():
    def factory(_settings, provider):
        return FakeAdapter(provider, f"{provider}-model", fail=True)

    service = LLMService(
        settings(llm_provider="openai"),
        adapter_factory=factory,
    )

    with pytest.raises(LLMUnavailableError, match="attempted=\\['openai'\\]"):
        service.invoke_text("hello")


def test_failed_invocation_exposes_non_secret_operational_metadata():
    def factory(_settings, provider):
        return FakeAdapter(provider, f"{provider}-model", fail=True)

    service = LLMService(settings(), adapter_factory=factory)

    with pytest.raises(LLMUnavailableError) as exc_info:
        service.invoke_text("hello")

    error = exc_info.value
    assert error.attempted_providers == ["openai", "gemini", "openrouter"]
    assert error.error_category == "timeout"
    assert error.failover_reason == "timeout"
    assert error.latency_ms is not None
    assert "openai-key" not in str(error)
