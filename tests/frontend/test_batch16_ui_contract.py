from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_TSX = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
APP_CSS = (ROOT / "frontend" / "src" / "App.css").read_text(encoding="utf-8")


def test_connections_remain_progressive_and_do_not_eagerly_fetch_expanded_graph() -> None:
    assert "Why are these studies related?" in APP_TSX
    assert "Open technical graph" in APP_TSX
    assert "if (!advancedOpen || !expandedScope || !seedNct)" in APP_TSX
    assert "const analysisGraph = useMemo<GraphViewResponse>" in APP_TSX
    assert "setAdvancedOpen(false)" in APP_TSX
    assert "Study connections map" not in APP_TSX


def test_count_semantics_keep_answer_set_distinct_from_expanded_graph() -> None:
    assert "studies in this answer" in APP_TSX
    assert "Studies shown" in APP_TSX
    assert "Display scope" in APP_TSX
    assert "Result limited" not in APP_TSX


def test_long_supporting_content_is_moved_out_of_answer_landing_page() -> None:
    assert "Top related studies" in APP_TSX
    assert "How TrialIQ produced this answer" in APP_TSX
    assert "function StudiesWorkspace" in APP_TSX
    assert "function StudyTimeline" in APP_TSX


def test_node_link_graph_is_bounded_inside_its_own_viewport() -> None:
    assert "bounded-canvas-shell" in APP_TSX
    assert ".bounded-canvas-shell { height: 650px" in APP_CSS
    assert "overflow: auto" in APP_CSS
    assert "graph-selection-drawer" in APP_TSX


def test_evidence_copy_scopes_sources_to_the_study_of_interest() -> None:
    assert "Evidence supporting this answer" in APP_TSX
    assert "Source-backed evidence for the study of interest" in APP_TSX
