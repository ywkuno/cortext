from __future__ import annotations

from pathlib import Path

from ..graph import GraphStore


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def export_dot(store: GraphStore, out: Path, max_edges: int = 1000) -> None:
    rows = store.rows(
        """
        SELECT source, target, kind
        FROM edges
        WHERE kind = 'imports'
        ORDER BY source, target
        LIMIT ?
        """,
        (max_edges,),
    )
    lines = ["digraph contextopt_imports {", "  rankdir=LR;"]
    for row in rows:
        lines.append(
            f"  {_quote(row['source'])} -> {_quote(row['target'])} [label={_quote(row['kind'])}];"
        )
    lines.append("}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
