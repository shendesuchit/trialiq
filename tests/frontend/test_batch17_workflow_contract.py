from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_TSX = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
APP_CSS = (ROOT / "frontend" / "src" / "App.css").read_text(encoding="utf-8")


def test_result_navigation_is_task_based() -> None:
    assert 'type InvestigatorTab = "answer" | "studies" | "connections" | "evidence";' in APP_TSX
    assert 'label="Answer"' in APP_TSX
    assert 'label={`Studies${matches.length ? ` · ${matches.length}` : ""}`}' in APP_TSX
    assert 'label={`Connections${connectionIds.size ? ` · ${connectionIds.size}` : ""}`}' in APP_TSX
    assert 'label="Evidence"' in APP_TSX
    investigator_nav = APP_TSX[APP_TSX.index('function InvestigatorResultWorkspace'):APP_TSX.index('function ProcessingStatus')]
    assert 'How TrialIQ reached this result' not in investigator_nav


def test_question_drives_initial_workspace_without_extra_llm_call() -> None:
    assert "function preferredInvestigatorTab(question: string): InvestigatorTab" in APP_TSX
    assert 'return "studies";' in APP_TSX
    assert 'return "connections";' in APP_TSX
    assert 'return "evidence";' in APP_TSX
    assert "setInvestigatorTab(preferredInvestigatorTab(question))" in APP_TSX


def test_answer_page_is_compact_and_routes_to_deeper_tasks() -> None:
    assert "studies in this answer" in APP_TSX
    assert "connection reasons" in APP_TSX
    assert "Top related studies" in APP_TSX
    assert "Compare studies" in APP_TSX
    assert "Explore connections" in APP_TSX
    assert "Review evidence" in APP_TSX
    assert "How TrialIQ produced this answer" in APP_TSX


def test_studies_workspace_keeps_comparison_and_visual_timeline_separate() -> None:
    assert "function StudiesWorkspace" in APP_TSX
    assert "Review, filter and compare" in APP_TSX
    assert "function StudyTimeline" in APP_TSX
    assert "Study timing at a glance" in APP_TSX
    assert ".visual-timeline-scroll" in APP_CSS
    assert ".studies-workspace > .agent-results-stack > .agent-synthesis-card" in APP_CSS


def test_connections_explain_before_exposing_technical_graph() -> None:
    assert "Why are these studies related?" in APP_TSX
    assert "connection reason" in APP_TSX
    assert "Technical graph explorer" in APP_TSX
    assert "Open technical graph" in APP_TSX
    assert "if (!advancedOpen || !expandedScope || !seedNct)" in APP_TSX


def test_evidence_is_category_first_with_details_on_demand() -> None:
    assert "Evidence supporting this answer" in APP_TSX
    assert "Open only what you need to inspect" in APP_TSX
    assert "evidence-detail-drawer" in APP_TSX
    assert "Technical source details" in APP_TSX
    assert ".evidence-drawer-backdrop" in APP_CSS


def test_workspace_uses_wider_desktop_space_without_changing_reading_width() -> None:
    assert ".investigator-result-shell.reading-active" in APP_CSS
    assert ".investigator-result-shell.workspace-active .task-workspace" in APP_CSS
    assert "width: min(1480px,calc(100vw - 330px))" in APP_CSS
