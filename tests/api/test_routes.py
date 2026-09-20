import pytest

from fastapi.testclient import TestClient

from trialiq.api.app import app
from trialiq.api.routes import query as query_route
from trialiq.api.routes import trials as trials_route
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
