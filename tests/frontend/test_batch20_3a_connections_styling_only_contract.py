from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "frontend" / "src" / "App.css").read_text(encoding="utf-8")


def graph_view() -> str:
    return APP[APP.index("function GraphView"):APP.index("function InspectorRow")]


def test_connections_keeps_batch20_2a_interaction_structure() -> None:
    source = graph_view()
    assert "connection-explorer-shell" in source
    assert "connection-category-grid" in source
    assert "connection-category-card" in source
    assert "connection-branch-panel" in source
    assert "visibleEntityStudies" in source
    assert "openBroaderGraph" in source
    assert "View wider network" in source
    assert "Show {Math.min(5" in source
    assert "connection-segmented-control" not in source
    assert "connection-study-table" not in source
    assert "connection-network-section" not in source
    assert "connection-comparison-table" not in source


def test_graph_labels_wrap_without_replacing_graph_controls() -> None:
    source = graph_view()
    assert "function splitGraphLabel" in APP
    assert "labelLines.map" in APP
    assert "CONNECTED STUDY ·" in APP
    assert "graph-filter-row" in source
    assert "graph-depth-switch" in source
    assert "Network" in source and "Table" in source


def test_graph_metrics_describe_visible_filtered_content() -> None:
    source = graph_view()
    assert "visibleRelatedStudyCount = connectionRows.length" in source
    assert 'Metric label="Shared entities"' in source
    assert 'Metric label="Evidence links"' in source
    assert 'Metric label="Items"' not in source
    assert 'Metric label="Connections"' not in source
    assert "Counts reflect the visible subset" in source


def test_empty_relationship_filter_is_explicit_instead_of_seed_only_canvas() -> None:
    source = graph_view()
    assert "visibleEdges.length && connectionRows.length" in source
    assert "No visible connections for this filter" in source
    assert "no study-to-entity evidence" in source


def test_relationship_filter_refits_existing_technical_graph() -> None:
    source = graph_view()
    assert "const sourceGraph = expandedScope ? graph : analysisGraph" in source
    assert "filteredEdges = relationshipFilter" in source
    assert "const fitted = buildGraphLayout(filteredNodes, maxHops)" in source
    assert "setViewport({ x: 0, y: 0, width: fitted.width, height: fitted.height })" in source


def test_reviewer_visual_language_is_scoped_to_existing_connections_ui() -> None:
    assert "Batch 20.3a: Connections styling-only correction" in CSS
    assert "--connections-ink: #182420" in CSS
    assert "--connections-paper: #f7f6f2" in CSS
    assert "--connections-teal: #2b6e63" in CSS
    assert 'font-family: "Source Serif 4"' in CSS
    assert 'font-family: "IBM Plex Mono"' in CSS
    assert ".task-connections .connection-category-card" in CSS
    assert ".task-connections .connection-branch-panel" in CSS
    assert ".task-connections .advanced-graph-gate" in CSS
    assert ".connection-scientific-document" not in CSS
