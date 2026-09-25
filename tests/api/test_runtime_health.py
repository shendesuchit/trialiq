from trialiq.api.runtime_health import (
    RuntimeComponentHealth,
    get_runtime_readiness,
)
from trialiq.api import runtime_health


def test_runtime_readiness_reports_all_required_components(monkeypatch):
    monkeypatch.setattr(
        runtime_health,
        "check_neo4j",
        lambda: RuntimeComponentHealth(healthy=True, status="healthy"),
    )
    monkeypatch.setattr(
        runtime_health,
        "check_mcp",
        lambda: RuntimeComponentHealth(healthy=True, status="healthy"),
    )
    monkeypatch.setattr(
        runtime_health,
        "llm_component",
        lambda: RuntimeComponentHealth(
            healthy=True,
            status="healthy",
            provider="gemini",
            model="test-model",
        ),
    )

    result = get_runtime_readiness()

    assert result.status == "ready"
    assert set(result.components) == {"api", "neo4j", "mcp", "llm"}
    assert result.components["llm"].provider == "gemini"
    assert result.components["llm"].model == "test-model"


def test_runtime_readiness_is_degraded_when_llm_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        runtime_health,
        "check_neo4j",
        lambda: RuntimeComponentHealth(healthy=True, status="healthy"),
    )
    monkeypatch.setattr(
        runtime_health,
        "check_mcp",
        lambda: RuntimeComponentHealth(healthy=True, status="healthy"),
    )
    monkeypatch.setattr(
        runtime_health,
        "llm_component",
        lambda: RuntimeComponentHealth(healthy=False, status="unavailable"),
    )

    result = get_runtime_readiness()

    assert result.status == "degraded"
    assert result.components["api"].healthy is True
    assert result.components["llm"].healthy is False
