from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
APP_TSX = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
APP_CSS = (ROOT / "frontend" / "src" / "App.css").read_text(encoding="utf-8")


def test_investigation_context_and_result_navigation_are_in_normal_flow() -> None:
    assert 'className="investigator-session-shell"' in APP_TSX
    assert "Batch 18: stable investigation context" in APP_CSS
    batch18_css = APP_CSS[APP_CSS.index("/* Batch 18:"):]
    assert ".investigator-result-tabs" in batch18_css
    assert "position: static" in batch18_css
    assert ".investigator-session-shell > .query-summary-strip" in batch18_css


def test_graph_result_frame_has_network_and_table_views() -> None:
    assert 'type GraphDisplayMode = "network" | "table";' in APP_TSX
    assert "Network explorer" in APP_TSX
    assert '> Network</button>' in APP_TSX
    assert '> Table</button>' in APP_TSX
    assert 'className="graph-table-view"' in APP_TSX


def test_graph_result_frame_has_pan_zoom_fit_minimize_and_maximize() -> None:
    assert "handleGraphPointerDown" in APP_TSX
    assert "handleGraphPointerMove" in APP_TSX
    assert "zoomGraph(.8)" in APP_TSX
    assert "zoomGraph(1.25)" in APP_TSX
    assert "Fit graph to view" in APP_TSX
    assert "Minimize graph" in APP_TSX
    assert "Maximize graph" in APP_TSX
    assert "graph-frame-maximized" in APP_TSX
    assert ".graph-frame-maximized" in APP_CSS
    assert "body.graph-workspace-open" in APP_CSS


def test_graph_result_frame_supports_copy_and_download_formats() -> None:
    assert "Copy visible graph as text" in APP_TSX
    assert "PNG image" in APP_TSX
    assert "SVG image" in APP_TSX
    assert "CSV · visible studies" in APP_TSX
    assert "CSV · visible connections" in APP_TSX
    assert "JSON · graph data" in APP_TSX
    assert "downloadClientFile" in APP_TSX
    assert "copyClientText" in APP_TSX


def test_batch18_does_not_add_a_new_graph_backend_contract() -> None:
    graph_view = APP_TSX[APP_TSX.index("function GraphView"):APP_TSX.index("function InspectorRow")]
    assert "/api/v1/lineage/trials/${encodeURIComponent(seedNct)}/graph" in graph_view
    assert "fetch(" in graph_view
    assert "generated cypher" not in graph_view.lower()
