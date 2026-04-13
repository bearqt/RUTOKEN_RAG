from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class GraphNode:
    node_id: str
    node_type: str
    value: str
    metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class GraphEdge:
    source_id: str
    target_id: str
    edge_type: str
    weight: float
    metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class ChunkEntityLink:
    chunk_id: str
    document_id: str
    node_id: str
    entity_type: str
    weight: float


@dataclass(slots=True, frozen=True)
class GraphChunkHit:
    chunk_id: str
    score: float


@dataclass(slots=True)
class GraphSearchResult:
    hits: list[GraphChunkHit] = field(default_factory=list)
    facts: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GraphSnapshot:
    nodes_by_id: dict[str, GraphNode] = field(default_factory=dict)
    entity_neighbors: dict[str, list[tuple[str, float, str]]] = field(default_factory=dict)
    entity_to_chunks: dict[str, list[ChunkEntityLink]] = field(default_factory=dict)
    chunk_to_document: dict[str, str] = field(default_factory=dict)
    document_to_chunks: dict[str, list[str]] = field(default_factory=dict)
