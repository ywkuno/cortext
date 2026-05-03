from __future__ import annotations
import re
from pathlib import Path
from .base import Edge, Extraction, Node

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def extract_markdown(path: Path, rel_path: str) -> Extraction:
    text = path.read_text(encoding="utf-8", errors="replace")
    out = Extraction()
    file_id = f"file:{rel_path}"
    out.nodes.append(Node(kind="doc", path=rel_path, name=rel_path, meta={"language": "markdown"}))
    for i, line in enumerate(text.splitlines(), start=1):
        m = HEADING_RE.match(line)
        if m:
            level = len(m.group(1))
            heading = m.group(2).strip()
            out.nodes.append(
                Node(
                    kind="heading", path=rel_path, name=heading, start_line=i, meta={"level": level}
                )
            )
            out.edges.append(
                Edge(source=file_id, target=f"heading:{rel_path}:{heading}", kind="contains")
            )
    return out
