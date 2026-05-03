from __future__ import annotations

from pathlib import Path
from typing import Any

from .gain import compute_gain
from .graph import GraphStore
from .mapper import map_project
from .query import query_graph
from .read_modes import format_read_result, read_path
from .references import find_references
from .retrieval import format_retrieved_source, retrieve_source
from .slicer import default_slice_path, export_slice


class McpDependencyError(RuntimeError):
    pass


def mcp_tool_specs() -> list[dict[str, str]]:
    return [
        {
            "name": "codeprism_prime",
            "description": "Map a local repo and write a focused context slice for a task.",
        },
        {
            "name": "codeprism_gain",
            "description": "Report estimated saved tokens and map freshness.",
        },
        {
            "name": "codeprism_query",
            "description": "Query the local CodePrism graph for relevant files and symbols.",
        },
        {
            "name": "codeprism_read",
            "description": "Read one file through token-aware modes: map, signatures, diff, or full.",
        },
        {
            "name": "codeprism_get",
            "description": "Fetch exact source for one mapped node ID.",
        },
        {
            "name": "codeprism_references",
            "description": "Show incoming and outgoing graph references for one node ID.",
        },
    ]


def _load_fastmcp():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise McpDependencyError(
            "The MCP SDK is not installed. Install with `pip install -e .[mcp]`."
        ) from exc
    return FastMCP


def create_mcp_server(*, root: Path, db: Path):
    FastMCP = _load_fastmcp()
    root = root.resolve()
    mcp = FastMCP("CodePrism")

    @mcp.tool()
    def codeprism_query(text: str, limit: int = 20) -> list[dict[str, Any]]:
        """Query the local CodePrism graph."""
        return query_graph(GraphStore(db), text, limit)

    @mcp.tool()
    def codeprism_gain() -> dict[str, Any]:
        """Report estimated saved tokens and map freshness."""
        return compute_gain(root, GraphStore(db))

    @mcp.tool()
    def codeprism_get(node_id: str) -> str:
        """Fetch exact source for a mapped node."""
        return format_retrieved_source(retrieve_source(GraphStore(db), root, node_id))

    @mcp.tool()
    def codeprism_read(path: str, mode: str = "signatures") -> str:
        """Read a file through token-aware modes."""
        result = read_path(root=root, path=path, mode=mode, store=GraphStore(db))
        return format_read_result(result)

    @mcp.tool()
    def codeprism_references(node_id: str) -> dict[str, Any]:
        """Show graph references for a mapped node."""
        return find_references(GraphStore(db), node_id)

    @mcp.tool()
    def codeprism_prime(query: str, limit: int = 12) -> dict[str, Any]:
        """Map the repo and write a focused slice."""
        store = GraphStore(db)
        map_project(root, store)
        out = default_slice_path(query)
        result = export_slice(store, query, root / out, limit=limit)
        return result

    return mcp


def run_mcp_server(*, root: Path, db: Path, transport: str = "stdio") -> None:
    create_mcp_server(root=root, db=db).run(transport=transport)
