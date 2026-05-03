import json
from pathlib import Path

from contextopt.activity import parse_activity_stream
from contextopt.exporters.json_export import export_json
from contextopt.exporters.web import export_web_visualization
from contextopt.graph import GraphStore
from contextopt.mapper import map_project


def test_visualization_export(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    db = tmp_path / "context.db"
    store = GraphStore(db)
    map_project(root, store)
    out_dir = tmp_path / "visual"
    html = export_web_visualization(store, out_dir)
    assert html.exists()
    assert (out_dir / "graph-data.json").exists()
    assert (out_dir / "app.js").exists()
    assert "clearSelectionBtn" in html.read_text(encoding="utf-8")
    html_text = html.read_text(encoding="utf-8")
    css_text = (out_dir / "styles.css").read_text(encoding="utf-8")
    js_text = (out_dir / "app.js").read_text(encoding="utf-8")
    assert "layerStructure" in html_text
    assert "layerImports" in html_text
    assert "focusSelectionBtn" in html_text
    assert "layoutMode" in html_text
    assert "roleFilter" in html_text
    assert "roleLegend" in html_text
    assert "repo-tree" in html_text
    assert "cluster-grid" in html_text
    assert "tooltip" in html_text
    assert "activityNow" in html_text
    assert "activitySummary" in html_text
    assert "activityTrailLayer" in html_text
    assert "agentMarkerLayer" in html_text
    assert "function clearSelection()" in js_text
    assert "function applyLayout()" in js_text
    assert "function applyRepoTreeLayout" in js_text
    assert "function applyClusterGridLayout" in js_text
    assert "function topLevelGroupKey" in js_text
    assert "groupsPerColumn" in js_text
    assert "function toggleFocusMode()" in js_text
    assert "function nodeLayerVisible" in js_text
    assert "function edgeLayerVisible" in js_text
    assert "function nodeRole" in js_text
    assert "function populateRoleFilter" in js_text
    assert "function populateRoleLegend" in js_text
    assert "function activityAgentId" in js_text
    assert "function renderActivitySummary" in js_text
    assert "function renderAgentMarkers" in js_text
    assert "function renderActivityTrails" in js_text
    assert "function zoomAtPointer" in js_text
    assert "state.tx = pointer.x - world.x * nextScale" in js_text
    assert "activitySearch" in html_text
    assert "function eventLabel" in js_text
    assert "function eventMatchesQuery" in js_text
    assert "state.activity.query" in js_text
    assert "activityRunFilter" in html_text
    assert "activityAgentFilter" in html_text
    assert "jumpEventBtn" in html_text
    assert "touchedOnlyBtn" in html_text
    assert "function populateActivityFilters" in js_text
    assert "function jumpToActivityNode" in js_text
    assert "function setTouchedOnly" in js_text
    assert "state.activityNodeIds" in js_text
    assert "contextSummary" in html_text
    assert "contextNodeIds" in js_text
    assert "function loadContextOverlay" in js_text
    assert "function renderContextSummary" in js_text
    assert "role-badge" not in css_text
    assert "setAttribute('class', 'role-badge')" not in js_text
    assert "appendChild(badge)" not in js_text
    assert "function showTooltip" in js_text


def test_graph_json_export_schema_and_hierarchy_edges(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    package = root / "pkg"
    docs = root / "docs"
    tests = root / "tests"
    package.mkdir(parents=True)
    docs.mkdir()
    tests.mkdir()
    (root / "AGENTS.md").write_text("# Agent instructions\n", encoding="utf-8")
    (root / ".gitignore").write_text(".contextopt/\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (package / "service.py").write_text(
        """
class Service:
    def run(self):
        return helper()

def helper():
    return 1
""",
        encoding="utf-8",
    )
    (docs / "guide.md").write_text("# Guide\n\n## Setup\n", encoding="utf-8")
    (tests / "test_service.py").write_text("def test_service():\n    assert True\n", encoding="utf-8")

    store = GraphStore(tmp_path / "context.db")
    map_project(root, store)
    out = tmp_path / "graph-data.json"
    export_json(store, out)
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert set(payload) == {"meta", "nodes", "edges"}
    assert payload["meta"]["schema_version"] == 1
    assert payload["nodes"]
    assert payload["edges"]
    for node in payload["nodes"]:
        assert set(node) == {
            "id",
            "kind",
            "path",
            "name",
            "label",
            "start_line",
            "end_line",
            "meta",
        }
    for edge in payload["edges"]:
        assert set(edge) == {"source", "target", "kind", "meta"}

    nodes_by_kind_name = {(node["kind"], node["name"]): node["id"] for node in payload["nodes"]}
    roles_by_name = {node["name"]: node["meta"].get("role") for node in payload["nodes"]}
    edges = {(edge["source"], edge["target"], edge["kind"]) for edge in payload["edges"]}
    assert roles_by_name["AGENTS.md"] == "agent"
    assert roles_by_name[".gitignore"] == "repo"
    assert roles_by_name["pyproject.toml"] == "package"
    assert roles_by_name["tests/test_service.py"] == "test"
    assert roles_by_name["docs/guide.md"] == "doc"
    assert roles_by_name["pkg/service.py"] == "source"
    assert ("folder", "pkg") in nodes_by_kind_name
    assert ("file", "pkg/service.py") in nodes_by_kind_name
    assert (
        nodes_by_kind_name[("folder", "pkg")],
        nodes_by_kind_name[("file", "pkg/service.py")],
        "contains",
    ) in edges
    assert (
        nodes_by_kind_name[("file", "pkg/service.py")],
        nodes_by_kind_name[("class", "Service")],
        "contains",
    ) in edges
    assert (
        nodes_by_kind_name[("class", "Service")],
        nodes_by_kind_name[("method", "run")],
        "contains",
    ) in edges
    assert (
        nodes_by_kind_name[("doc", "docs/guide.md")],
        nodes_by_kind_name[("heading", "Setup")],
        "contains",
    ) in edges


def test_stable_node_ids_across_two_map_runs(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    store = GraphStore(tmp_path / "context.db")

    map_project(root, store)
    first_out = tmp_path / "first.json"
    export_json(store, first_out)
    first_ids = sorted(node["id"] for node in json.loads(first_out.read_text())["nodes"])

    map_project(root, store)
    second_out = tmp_path / "second.json"
    export_json(store, second_out)
    second_ids = sorted(node["id"] for node in json.loads(second_out.read_text())["nodes"])

    assert first_ids == second_ids


def test_activity_stream_parser_accepts_valid_jsonl(tmp_path: Path) -> None:
    activity = tmp_path / "activity.jsonl"
    activity.write_text(
        '{"ts":"2026-05-03T02:00:00Z","run_id":"demo","agent_id":"codex",'
        '"event":"file_read","node_id":"file::app.py","from_node_id":"folder::.",'
        '"to_node_id":"file::app.py","duration_ms":750,"status":"ok","severity":"info",'
        '"path":"app.py","estimated_tokens":123,"actual_tokens":145,"meta":{"ok":true}}\n',
        encoding="utf-8",
    )

    events, warnings = parse_activity_stream(activity)

    assert warnings == []
    assert events[0]["event"] == "file_read"
    assert events[0]["from_node_id"] == "folder::."
    assert events[0]["to_node_id"] == "file::app.py"
    assert events[0]["duration_ms"] == 750
    assert events[0]["status"] == "ok"
    assert events[0]["severity"] == "info"
    assert events[0]["estimated_tokens"] == 123
    assert events[0]["actual_tokens"] == 145
    assert events[0]["meta"] == {"ok": True}


def test_activity_payload_includes_summary(tmp_path: Path) -> None:
    activity = tmp_path / "activity.jsonl"
    activity.write_text(
        '{"agent_id":"codex","event":"file_read","estimated_tokens":100,"duration_ms":500}\n'
        '{"agent_id":"cortext","event":"context_pack_generated","estimated_tokens":25,'
        '"actual_tokens":30,"duration_ms":250}\n',
        encoding="utf-8",
    )

    from contextopt.activity import write_activity_payload

    out = tmp_path / "activity.json"
    write_activity_payload(activity, out)
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert payload["summary"] == {
        "event_count": 2,
        "agent_count": 2,
        "agents": ["codex", "cortext"],
        "estimated_tokens": 125,
        "actual_tokens": 30,
        "duration_ms": 750,
    }


def test_visualization_export_accepts_malformed_activity_rows(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    activity = tmp_path / "activity.jsonl"
    activity.write_text(
        '{"ts":"2026-05-03T02:00:00Z","event":"file_read","path":"app.py"}\n'
        "not json\n"
        '{"event":"missing optional fields","node_id":"function::app.py::main"}\n',
        encoding="utf-8",
    )
    store = GraphStore(tmp_path / "context.db")
    map_project(root, store)

    out_dir = tmp_path / "visual"
    html = export_web_visualization(store, out_dir, activity_path=activity)

    assert html.exists()
    payload = json.loads((out_dir / "activity-stream.json").read_text(encoding="utf-8"))
    assert len(payload["events"]) == 2
    assert payload["warnings"]


def test_visualization_export_copies_context_overlay(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    context = tmp_path / "slice.json"
    context.write_text(
        '{"schema_version":1,"query":"main","node_ids":["file::app.py"],'
        '"estimated_tokens":10,"full_context_estimated_tokens":100}\n',
        encoding="utf-8",
    )
    store = GraphStore(tmp_path / "context.db")
    map_project(root, store)

    out_dir = tmp_path / "visual"
    export_web_visualization(store, out_dir, context_path=context)

    copied = json.loads((out_dir / "context-overlay.json").read_text(encoding="utf-8"))
    assert copied["node_ids"] == ["file::app.py"]
