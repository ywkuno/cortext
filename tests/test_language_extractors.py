from __future__ import annotations

import json
from pathlib import Path

from contextopt.graph import GraphStore
from contextopt.exporters.json_export import export_json
from contextopt.ids import stable_node_id
from contextopt.mapper import map_project
from contextopt.slicer import export_slice


def _nodes(store: GraphStore) -> list[dict[str, object]]:
    return [dict(row) for row in store.rows("SELECT * FROM nodes")]


def _edges(store: GraphStore) -> list[dict[str, object]]:
    return [dict(row) for row in store.rows("SELECT * FROM edges")]


def test_java_files_map_package_imports_types_methods_and_entrypoints(tmp_path: Path) -> None:
    package_dir = tmp_path / "src" / "main" / "java" / "net" / "swordie" / "ms"
    package_dir.mkdir(parents=True)
    (package_dir / "ServerConstants.java").write_text(
        "package net.swordie.ms;\n\n"
        "public final class ServerConstants {\n"
        "    public static final int LOGIN_PORT = 8484;\n"
        "}\n",
        encoding="utf-8",
    )
    (package_dir / "Server.java").write_text(
        "package net.swordie.ms;\n\n"
        "import net.swordie.ms.ServerConstants;\n\n"
        "public final class Server {\n"
        "    public static void main(String[] args) {\n"
        "        boot();\n"
        "    }\n\n"
        "    private static void boot() {\n"
        "        System.out.println(ServerConstants.LOGIN_PORT);\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path / ".contextopt" / "context.db")

    map_project(tmp_path, store)

    nodes = _nodes(store)
    edges = _edges(store)
    server_file = next(node for node in nodes if node["path"].endswith("Server.java") and node["kind"] == "file")
    server_meta = json.loads(str(server_file["meta_json"]))
    main_method = next(node for node in nodes if node["path"].endswith("Server.java") and node["name"] == "main")
    main_meta = json.loads(str(main_method["meta_json"]))

    assert server_meta["language"] == "java"
    assert server_meta["package"] == "net.swordie.ms"
    assert any(node["kind"] == "class" and node["name"] == "Server" for node in nodes)
    assert any(node["kind"] == "method" and node["name"] == "boot" for node in nodes)
    assert main_meta["parent_class"] == "Server"
    assert main_meta["entrypoint"] is True
    assert any(
        edge["kind"] == "imports" and edge["target"] == "module:net.swordie.ms.ServerConstants"
        for edge in edges
    )


def test_java_slice_resolves_local_package_imports(tmp_path: Path) -> None:
    package_dir = tmp_path / "src" / "main" / "java" / "net" / "swordie" / "ms"
    package_dir.mkdir(parents=True)
    (package_dir / "ServerConstants.java").write_text(
        "package net.swordie.ms;\n\npublic final class ServerConstants {}\n",
        encoding="utf-8",
    )
    (package_dir / "Server.java").write_text(
        "package net.swordie.ms;\n\n"
        "import net.swordie.ms.ServerConstants;\n\n"
        "public final class Server {\n"
        "    public static void main(String[] args) {}\n"
        "}\n",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    map_project(tmp_path, store)

    out = tmp_path / ".contextopt" / "slices" / "server.md"
    result = export_slice(
        store,
        "server boot",
        out,
        seed_paths=["src/main/java/net/swordie/ms/Server.java"],
    )

    text = out.read_text(encoding="utf-8")
    assert "src/main/java/net/swordie/ms/Server.java" in text
    assert "src/main/java/net/swordie/ms/ServerConstants.java" in text
    assert result["symbol_count"] >= 2


def test_json_export_resolves_java_package_imports_to_local_files(tmp_path: Path) -> None:
    package_dir = tmp_path / "src" / "main" / "java" / "net" / "swordie" / "ms"
    package_dir.mkdir(parents=True)
    (package_dir / "ServerConstants.java").write_text(
        "package net.swordie.ms;\n\npublic final class ServerConstants {}\n",
        encoding="utf-8",
    )
    (package_dir / "Server.java").write_text(
        "package net.swordie.ms;\n\n"
        "import net.swordie.ms.ServerConstants;\n\n"
        "public final class Server {}\n",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    map_project(tmp_path, store)

    out = tmp_path / ".contextopt" / "graph-data.json"
    export_json(store, out)

    payload = json.loads(out.read_text(encoding="utf-8"))
    server_id = stable_node_id(
        "file",
        "src/main/java/net/swordie/ms/Server.java",
        "src/main/java/net/swordie/ms/Server.java",
    )
    constants_id = stable_node_id(
        "file",
        "src/main/java/net/swordie/ms/ServerConstants.java",
        "src/main/java/net/swordie/ms/ServerConstants.java",
    )

    assert any(
        edge["kind"] == "imports" and edge["source"] == server_id and edge["target"] == constants_id
        for edge in payload["edges"]
    )


def test_generic_extractor_maps_common_non_python_languages(tmp_path: Path) -> None:
    (tmp_path / "cmd").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "cmd" / "server.go").write_text(
        'package main\n\nimport "net/http"\n\ntype Server struct {}\nfunc main() {}\n',
        encoding="utf-8",
    )
    (tmp_path / "src" / "lib.rs").write_text(
        "use crate::engine;\n\npub struct Engine {}\npub fn run() {}\n",
        encoding="utf-8",
    )
    (tmp_path / "Program.cs").write_text(
        "using System;\n\npublic class Program {\n    public static void Main(string[] args) {}\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "worker.rb").write_text(
        'require "json"\n\nclass Worker\n  def perform\n  end\nend\n',
        encoding="utf-8",
    )
    store = GraphStore(tmp_path / ".contextopt" / "context.db")

    map_project(tmp_path, store)

    nodes = _nodes(store)
    file_languages = {
        json.loads(str(node["meta_json"])).get("language")
        for node in nodes
        if node["kind"] == "file"
    }
    names = {str(node["name"]) for node in nodes if node["kind"] in {"class", "function", "method"}}

    assert {"go", "rust", "csharp", "ruby"}.issubset(file_languages)
    assert {"Server", "main", "Engine", "run", "Program", "Main", "Worker", "perform"}.issubset(
        names
    )
