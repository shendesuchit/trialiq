from trialiq.mcp import server
from trialiq.services.models import AnswerStatus, EvidenceGroundedAnswer


def make_answer(status=AnswerStatus.GROUNDED):
    return EvidenceGroundedAnswer(
        status=status,
        question="Give me an overview of NCT00000102",
        answer="Mock grounded answer",
        sources=[],
    )


def test_get_trial_overview_delegates_to_nct_answer_service(monkeypatch):
    captured = {}

    def fake_answer(nct_id):
        captured["nct_id"] = nct_id
        return make_answer()

    monkeypatch.setattr(server, "answer_trial_overview_by_nct_id", fake_answer)

    result = server.get_trial_overview("NCT00000102")

    assert captured["nct_id"] == "NCT00000102"
    assert isinstance(result, EvidenceGroundedAnswer)
    assert result.status == AnswerStatus.GROUNDED
    assert result.answer == "Mock grounded answer"


def test_get_trial_overview_preserves_non_grounded_status(monkeypatch):
    monkeypatch.setattr(
        server,
        "answer_trial_overview_by_nct_id",
        lambda _: make_answer(AnswerStatus.INSUFFICIENT_EVIDENCE),
    )

    result = server.get_trial_overview("NCT99999999")

    assert result.status == AnswerStatus.INSUFFICIENT_EVIDENCE
