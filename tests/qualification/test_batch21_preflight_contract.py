from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT = (ROOT / "scripts" / "demo_preflight.py").read_text(encoding="utf-8")


def test_demo_preflight_accepts_and_resumes_hitl_checkpoint():
    assert 'run.get("status") == "REVIEW_REQUIRED"' in PREFLIGHT
    assert '/api/v1/query/agent/continue' in PREFLIGHT
    assert '"mode": "SELECTED"' in PREFLIGHT
    assert 'human_review_decision' in PREFLIGHT


def test_demo_preflight_still_requires_mcp_and_validated_synthesis():
    assert 'retrieval.get("transport") == "mcp"' in PREFLIGHT
    assert 'generation.get("method") == "LLM"' in PREFLIGHT
    assert '"metrics", "validation", "synthesis"' in PREFLIGHT


def test_batch21_small_candidate_discovery_is_memory_bounded():
    qualifier = (ROOT / "scripts" / "qualify_batch21_stable_demo.py").read_text(encoding="utf-8")

    assert "SMALL_ENTITY_SCAN_LIMIT = 2000" in qualifier
    assert "entity.loaded_trial_count >= 3" in qualifier
    assert "entity.loaded_trial_count <= 7" in qualifier
    assert "LIMIT {SMALL_ENTITY_SCAN_LIMIT}" in qualifier
    assert "collect(DISTINCT entity)" not in qualifier
    assert "collect(DISTINCT peer)" not in qualifier
