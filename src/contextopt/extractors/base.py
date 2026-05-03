from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Node:
    kind: str
    path: str
    name: str
    start_line: int | None = None
    end_line: int | None = None
    meta: dict = field(default_factory=dict)


@dataclass
class Edge:
    source: str
    target: str
    kind: str
    meta: dict = field(default_factory=dict)


@dataclass
class Extraction:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
