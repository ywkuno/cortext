from __future__ import annotations

from pathlib import Path

from contextopt.extractors.js_ts import extract_js_ts


def test_js_ts_extractor_finds_modern_exports_imports_and_next_route(tmp_path: Path):
    page = tmp_path / "app" / "users" / "[id]" / "page.tsx"
    page.parent.mkdir(parents=True)
    page.write_text(
        """
import React from "react";
import "./page.css";

export const loader = async () => {
  return null;
};

const helper = function () {
  return "ok";
};

export default function Page() {
  return <main />;
}

export class Widget {}
""",
        encoding="utf-8",
    )

    extraction = extract_js_ts(page, "app/users/[id]/page.tsx")
    functions = {node.name for node in extraction.nodes if node.kind == "function"}
    classes = {node.name for node in extraction.nodes if node.kind == "class"}
    routes = [node for node in extraction.nodes if node.kind == "route"]
    import_targets = {edge.target for edge in extraction.edges if edge.kind == "imports"}

    assert functions == {"Page", "helper", "loader"}
    assert classes == {"Widget"}
    assert routes[0].name == "/users/:id"
    assert routes[0].meta["framework"] == "nextjs"
    assert import_targets >= {"module:react", "module:./page.css"}
