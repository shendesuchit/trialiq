import pytest

from fastapi.testclient import TestClient

from trialiq.api.app import app
from trialiq.api.routes import query as query_route
from trialiq.api.routes import trials as trials_route
from trialiq.agents.models import AgentRunResult, AgentStageTrace, AgentStatus
from trialiq.services.models import AnswerStatus, EvidenceGroundedAnswer


client = TestClient(app)


def make_answer(status: AnswerStatus, answer: str = "Mock answer") -> EvidenceGroundedAnswer:
    return EvidenceGroundedAnswer(
        status=status,
        question="Give me an overview of NCT00000102",
        answer=answer,
        sources=[],
    )


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "trialiq-api"}


def test_trial_catalog_delegates_and_returns_dynamic_suggestions(monkeypatch):
    captured = {}

    def fake_catalog(query, *, limit, offset):
        captured.update({"query": query, "limit": limit, "offset": offset})
        return {
            "query": query,
            "limit": limit,
            "offset": offset,
            "total_count": 2,
            "has_more": False,
            "trials": [
                {
                    "nct_id": "NCT03416088",
                    "brief_title": "Connected demo trial",
                    "official_title": None,
                    "overall_status": "COMPLETED",
                    "related_trial_count": 3,
                    "has_graph_neighbors": True,
                    "relationship_types": [
                        "HAS_CONDITION",
                        "HAS_INTERVENTION",
                        "SPONSORED_BY",
                    ],
                    "suggested_questions": [
                        {
                            "kind": "related_trials",
                            "label": "Find related trials",
                            "question": "Find trials related to NCT03416088.",
                        }
                    ],
                },
                {
                    "nct_id": "NCT09999999",
                    "brief_title": "Isolated trial",
                    "official_title": None,
                    "overall_status": "RECRUITING",
                    "related_trial_count": 0,
                    "has_graph_neighbors": False,
                    "relationship_types": [],
                    "suggested_questions": [
                        {
                            "kind": "overview",
                            "label": "Summarize this trial",
                            "question": "Give me an overview of NCT09999999.",
                        }
                    ],
                },
            ],
        }

    monkeypatch.setattr(trials_route, "get_trial_catalog", fake_catalog)

    response = client.get(
        "/api/v1/trials/catalog",
        params={"query": "retinal", "limit": 10, "offset": 0},
    )

    assert response.status_code == 200
    assert captured == {"query": "retinal", "limit": 10, "offset": 0}
    body = response.json()
    assert body["total_count"] == 2
    assert body["trials"][0]["has_graph_neighbors"] is True
    assert body["trials"][1]["has_graph_neighbors"] is False


def test_trial_catalog_rejects_out_of_range_limit():
    response = client.get("/api/v1/trials/catalog", params={"limit": 101})

    assert response.status_code == 422


def test_trial_overview_delegates_and_returns_answer(monkeypatch):
    captured = {}

    def fake_answer(nct_id):
        captured["nct_id"] = nct_id
        return make_answer(AnswerStatus.GROUNDED)

    monkeypatch.setattr(trials_route, "answer_trial_overview_by_nct_id", fake_answer)

    response = client.post(
        "/api/v1/trials/overview",
        json={"nct_id": "NCT00000102"},
    )

    assert response.status_code == 200
    assert captured["nct_id"] == "NCT00000102"
    assert response.json()["status"] == "GROUNDED"


def test_trial_overview_returns_http_500_for_execution_error(monkeypatch):
    monkeypatch.setattr(
        trials_route,
        "answer_trial_overview_by_nct_id",
        lambda _: make_answer(AnswerStatus.EXECUTION_ERROR, "Failure"),
    )

    response = client.post(
        "/api/v1/trials/overview",
        json={"nct_id": "NCT00000102"},
    )

    assert response.status_code == 500
    assert response.json()["detail"]["status"] == "EXECUTION_ERROR"


def test_query_endpoint_delegates_to_natural_language_answer(monkeypatch):
    captured = {}

    def fake_answer(question):
        captured["question"] = question
        return make_answer(AnswerStatus.GROUNDED)

    monkeypatch.setattr(query_route, "answer_trial_overview", fake_answer)

    question = "Give me an overview of NCT00000102."
    response = client.post("/api/v1/query", json={"question": question})

    assert response.status_code == 200
    assert captured["question"] == question
    assert response.json()["status"] == "GROUNDED"


@pytest.mark.parametrize(
    "answer_status",
    [
        AnswerStatus.INSUFFICIENT_EVIDENCE,
        AnswerStatus.MISSING_NCT_ID,
        AnswerStatus.UNSUPPORTED,
        AnswerStatus.VALIDATION_FAILED,
    ],
)
def test_query_endpoint_preserves_non_execution_status(monkeypatch, answer_status):
    monkeypatch.setattr(
        query_route,
        "answer_trial_overview",
        lambda _: make_answer(answer_status),
    )

    response = client.post(
        "/api/v1/query",
        json={"question": "test question"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == answer_status.value


def test_query_endpoint_returns_http_500_for_execution_error(monkeypatch):
    monkeypatch.setattr(
        query_route,
        "answer_trial_overview",
        lambda _: make_answer(AnswerStatus.EXECUTION_ERROR, "Failure"),
    )

    response = client.post(
        "/api/v1/query",
        json={"question": "test question"},
    )

    assert response.status_code == 500
    assert response.json()["detail"]["status"] == "EXECUTION_ERROR"


def test_query_endpoint_rejects_empty_question():
    response = client.post("/api/v1/query", json={"question": ""})

    assert response.status_code == 422


def test_query_endpoint_rejects_unknown_fields():
    response = client.post(
        "/api/v1/query",
        json={"question": "test question", "unexpected": True},
    )

    assert response.status_code == 422



def make_agent_run(status=AgentStatus.SUCCESS, answer_status=AnswerStatus.GROUNDED):
    return AgentRunResult(
        run_id="run-test-123",
        status=status,
        answer=make_answer(answer_status),
        trace=[
            AgentStageTrace(
                stage="retrieval",
                status=status,
                duration_ms=1.25,
                details={"tool_name": "get_trial_evidence", "transport": "mcp"},
            )
        ],
    )


def test_query_endpoint_defaults_to_standard_mode_and_sets_headers(monkeypatch):
    monkeypatch.setattr(
        query_route,
        "answer_trial_overview",
        lambda _: make_answer(AnswerStatus.GROUNDED),
    )

    response = client.post(
        "/api/v1/query",
        json={"question": "Give me an overview of NCT00000102"},
    )

    assert response.status_code == 200
    assert response.headers["X-TrialIQ-Workflow-Mode"] == "standard"
    assert response.headers["X-TrialIQ-Run-ID"]


def test_query_endpoint_agent_mode_uses_agent_workflow(monkeypatch):
    captured = {}

    def fake_run(question, *, limit):
        captured["question"] = question
        captured["limit"] = limit
        return make_agent_run()

    monkeypatch.setattr(query_route, "run_agent_question", fake_run)

    response = client.post(
        "/api/v1/query",
        json={
            "question": "Give me an overview of NCT00000102",
            "mode": "agent",
            "limit": 7,
        },
    )

    assert response.status_code == 200
    assert captured == {
        "question": "Give me an overview of NCT00000102",
        "limit": 7,
    }
    assert response.json()["status"] == "GROUNDED"
    assert response.headers["X-TrialIQ-Workflow-Mode"] == "agent"
    assert response.headers["X-TrialIQ-Run-ID"] == "run-test-123"


def test_query_endpoint_agent_mode_returns_http_500_for_execution_error(monkeypatch):
    monkeypatch.setattr(
        query_route,
        "run_agent_question",
        lambda question, *, limit: make_agent_run(
            AgentStatus.EXECUTION_ERROR,
            AnswerStatus.EXECUTION_ERROR,
        ),
    )

    response = client.post(
        "/api/v1/query",
        json={"question": "test", "mode": "agent"},
    )

    assert response.status_code == 500
    assert response.json()["detail"]["status"] == "EXECUTION_ERROR"


def test_explicit_agent_endpoint_returns_observable_run(monkeypatch):
    monkeypatch.setattr(
        query_route,
        "run_agent_question",
        lambda question, *, limit: make_agent_run(),
    )

    response = client.post(
        "/api/v1/query/agent",
        json={"question": "Give me an overview of NCT00000102"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "run-test-123"
    assert body["status"] == "SUCCESS"
    assert body["trace"][0]["stage"] == "retrieval"
    assert body["trace"][0]["details"]["transport"] == "mcp"


def test_query_endpoint_rejects_unknown_mode():
    response = client.post(
        "/api/v1/query",
        json={"question": "test", "mode": "unknown"},
    )

    assert response.status_code == 422


def test_query_endpoint_rejects_out_of_range_limit():
    response = client.post(
        "/api/v1/query",
        json={"question": "test", "mode": "agent", "limit": 101},
    )

    assert response.status_code == 422



def test_explicit_agent_endpoint_preserves_failure_trace(monkeypatch):
    monkeypatch.setattr(
        query_route,
        "run_agent_question",
        lambda question, *, limit: make_agent_run(
            AgentStatus.EXECUTION_ERROR,
            AnswerStatus.EXECUTION_ERROR,
        ),
    )

    response = client.post(
        "/api/v1/query/agent",
        json={"question": "test"},
    )

    assert response.status_code == 200
    assert response.json()["run_id"] == "run-test-123"
    assert response.json()["status"] == "EXECUTION_ERROR"
    assert response.json()["trace"][0]["stage"] == "retrieval"
