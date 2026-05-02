from __future__ import annotations

from collections import defaultdict
from itertools import combinations

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import Settings
from app.domain.graph_models import (
    ChunkEntityLink,
    GraphNode,
    GraphRelationLink,
    GraphSnapshot,
)
from app.domain.models import Chunk
from app.services.entity_canonicalizer import SYMMETRIC_RELATIONS


ENTITY_KEYS = (
    "products",
    "interfaces",
    "os_tags",
    "language_tags",
    "components",
    "api_symbols",
    "pkcs11_objects",
    "pkcs11_mechanisms",
    "error_codes",
)

ENTITY_LINK_WEIGHTS = {
    "products": 0.9,
    "interfaces": 1.0,
    "os_tags": 0.6,
    "language_tags": 0.5,
    "components": 1.1,
    "api_symbols": 1.8,
    "pkcs11_objects": 1.3,
    "pkcs11_mechanisms": 1.3,
    "error_codes": 1.2,
}

STRUCTURAL_EDGE_TYPES = {
    "document_contains_chunk",
    "chunk_belongs_to_doc_family",
    "chunk_mentions_entity",
    "entity_belongs_to_doc_family",
}


class GraphRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def ensure_schema(self) -> None:
        statements = [
            """
            CREATE TABLE IF NOT EXISTS graph_nodes (
                id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                value TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS graph_edges (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                weight DOUBLE PRECISION NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                PRIMARY KEY (source_id, target_id, edge_type)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS chunk_entity_links (
                chunk_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                node_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                weight DOUBLE PRECISION NOT NULL,
                PRIMARY KEY (chunk_id, node_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS relation_chunk_links (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                edge_type TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                confidence DOUBLE PRECISION NOT NULL,
                PRIMARY KEY (source_id, target_id, edge_type, chunk_id)
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_graph_edges_type ON graph_edges(edge_type)",
            "CREATE INDEX IF NOT EXISTS idx_relation_chunk_links_chunk ON relation_chunk_links(chunk_id)",
        ]
        with self._connect() as conn:
            for statement in statements:
                conn.execute(statement)

    def replace_graph(self, chunks: list[Chunk]) -> None:
        nodes: dict[str, tuple[str, str, dict]] = {}
        edges: dict[tuple[str, str, str], tuple[float, dict]] = {}
        chunk_entity_links: dict[tuple[str, str], tuple[str, str, float]] = {}
        relation_chunk_links: dict[tuple[str, str, str, str], tuple[str, float]] = {}

        for chunk_index, chunk in enumerate(chunks):
            document_node_id = f"document:{chunk.document_id}"
            chunk_node_id = f"chunk:{chunk.chunk_id}"
            doc_family = str(chunk.metadata.get("doc_family") or "general")
            doc_family_node_id = f"doc_family:{doc_family}"

            nodes[document_node_id] = (
                "document",
                chunk.document_id,
                {
                    "title": chunk.title,
                    "page_id": chunk.page_id,
                    "source_url": chunk.source_url,
                },
            )
            nodes[chunk_node_id] = (
                "chunk",
                chunk.chunk_id,
                {
                    "document_id": chunk.document_id,
                    "page_id": chunk.page_id,
                    "source_url": chunk.source_url,
                    "title": chunk.title,
                    "heading_path": chunk.heading_path,
                    "heading_path_text": chunk.metadata.get("heading_path_text", ""),
                    "chunk_type": chunk.chunk_type,
                    "chunk_index": chunk_index,
                    "doc_family": doc_family,
                    **chunk.metadata,
                },
            )
            nodes[doc_family_node_id] = ("doc_family", doc_family, {})

            self._upsert_edge(edges, document_node_id, chunk_node_id, "document_contains_chunk", 1.0)
            self._upsert_edge(edges, chunk_node_id, doc_family_node_id, "chunk_belongs_to_doc_family", 0.4)

            entity_nodes_in_chunk: list[tuple[str, float]] = []
            for entity_type in ENTITY_KEYS:
                values = chunk.metadata.get(entity_type, [])
                if not isinstance(values, list):
                    continue
                for value in values:
                    node_id = f"{entity_type}:{value}"
                    weight = ENTITY_LINK_WEIGHTS.get(entity_type, 1.0)
                    nodes[node_id] = ("entity", value, {"entity_type": entity_type})
                    self._upsert_edge(
                        edges,
                        chunk_node_id,
                        node_id,
                        "chunk_mentions_entity",
                        weight,
                        {"entity_type": entity_type},
                    )
                    self._upsert_edge(
                        edges,
                        node_id,
                        doc_family_node_id,
                        "entity_belongs_to_doc_family",
                        0.25,
                        {"entity_type": entity_type},
                    )
                    chunk_entity_links[(chunk.chunk_id, node_id)] = (
                        chunk.document_id,
                        entity_type,
                        weight,
                    )
                    entity_nodes_in_chunk.append((node_id, weight))

            unique_entities = list(dict.fromkeys(entity_nodes_in_chunk))
            for (left_id, left_weight), (right_id, right_weight) in combinations(unique_entities, 2):
                pair_weight = round((left_weight + right_weight) / 2.0, 4)
                left_entity = left_id.split(":", 1)[0]
                right_entity = right_id.split(":", 1)[0]
                self._upsert_edge(
                    edges,
                    *sorted((left_id, right_id)),
                    "entity_cooccurs_with_entity",
                    pair_weight,
                    {"source_types": [left_entity, right_entity]},
                )

            relations = chunk.metadata.get("graph_relations", [])
            if not isinstance(relations, list):
                relations = []
            for relation in relations:
                if not isinstance(relation, dict):
                    continue
                src_type = str(relation.get("src_type") or "").strip()
                src_value = str(relation.get("src_value") or "").strip()
                tgt_type = str(relation.get("tgt_type") or "").strip()
                tgt_value = str(relation.get("tgt_value") or "").strip()
                predicate = str(relation.get("predicate") or "").strip()
                if not src_type or not src_value or not tgt_type or not tgt_value or not predicate:
                    continue

                src_id = f"{src_type}:{src_value}"
                tgt_id = f"{tgt_type}:{tgt_value}"
                if predicate in SYMMETRIC_RELATIONS and tgt_id < src_id:
                    src_id, tgt_id = tgt_id, src_id
                    src_type, tgt_type = tgt_type, src_type
                    src_value, tgt_value = tgt_value, src_value

                nodes[src_id] = ("entity", src_value, {"entity_type": src_type})
                nodes[tgt_id] = ("entity", tgt_value, {"entity_type": tgt_type})
                confidence = _safe_float(relation.get("confidence"), default=1.0)
                self._upsert_edge(
                    edges,
                    src_id,
                    tgt_id,
                    predicate,
                    confidence,
                    {
                        "confidence": confidence,
                        "source": relation.get("source", "llm"),
                        "evidence": str(relation.get("evidence") or ""),
                    },
                )
                relation_chunk_links[(src_id, tgt_id, predicate, chunk.chunk_id)] = (
                    chunk.document_id,
                    confidence,
                )

        with self._connect() as conn:
            conn.execute("DELETE FROM relation_chunk_links")
            conn.execute("DELETE FROM chunk_entity_links")
            conn.execute("DELETE FROM graph_edges")
            conn.execute("DELETE FROM graph_nodes")

            for node_id, (node_type, value, metadata) in nodes.items():
                conn.execute(
                    """
                    INSERT INTO graph_nodes (id, node_type, value, metadata)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (node_id, node_type, value, Jsonb(metadata)),
                )

            for (source_id, target_id, edge_type), (weight, metadata) in edges.items():
                conn.execute(
                    """
                    INSERT INTO graph_edges (source_id, target_id, edge_type, weight, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (source_id, target_id, edge_type, weight, Jsonb(metadata)),
                )

            for (chunk_id, node_id), (document_id, entity_type, weight) in chunk_entity_links.items():
                conn.execute(
                    """
                    INSERT INTO chunk_entity_links (chunk_id, document_id, node_id, entity_type, weight)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (chunk_id, document_id, node_id, entity_type, weight),
                )

            for (source_id, target_id, edge_type, chunk_id), (document_id, confidence) in relation_chunk_links.items():
                conn.execute(
                    """
                    INSERT INTO relation_chunk_links (
                        source_id,
                        target_id,
                        edge_type,
                        chunk_id,
                        document_id,
                        confidence
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (source_id, target_id, edge_type, chunk_id, document_id, confidence),
                )

    def has_index(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM graph_nodes").fetchone()
        return bool(row and row["count"])

    def load_graph(self) -> GraphSnapshot:
        snapshot = GraphSnapshot()
        with self._connect() as conn:
            node_rows = conn.execute(
                "SELECT id, node_type, value, metadata FROM graph_nodes"
            ).fetchall()
            edge_rows = conn.execute(
                """
                SELECT source_id, target_id, edge_type, weight, metadata
                FROM graph_edges
                """
            ).fetchall()
            link_rows = conn.execute(
                """
                SELECT chunk_id, document_id, node_id, entity_type, weight
                FROM chunk_entity_links
                """
            ).fetchall()
            relation_rows = conn.execute(
                """
                SELECT source_id, target_id, edge_type, chunk_id, document_id, confidence
                FROM relation_chunk_links
                """
            ).fetchall()

        snapshot.nodes_by_id = {
            row["id"]: GraphNode(
                node_id=row["id"],
                node_type=row["node_type"],
                value=row["value"],
                metadata=row["metadata"] or {},
            )
            for row in node_rows
        }

        cooccurrence_neighbors: dict[str, list[tuple[str, float, str]]] = defaultdict(list)
        typed_entity_neighbors: dict[str, list[tuple[str, float, str]]] = defaultdict(list)
        entity_degrees: dict[str, set[str]] = defaultdict(set)
        for row in edge_rows:
            source_id = row["source_id"]
            target_id = row["target_id"]
            edge_type = row["edge_type"]
            weight = float(row["weight"])
            source_node = snapshot.nodes_by_id.get(source_id)
            target_node = snapshot.nodes_by_id.get(target_id)
            if source_node is None or target_node is None:
                continue
            if source_node.node_type != "entity" or target_node.node_type != "entity":
                continue

            if edge_type == "entity_cooccurs_with_entity":
                cooccurrence_neighbors[source_id].append((target_id, weight, edge_type))
                cooccurrence_neighbors[target_id].append((source_id, weight, edge_type))
            else:
                typed_entity_neighbors[source_id].append((target_id, weight, edge_type))
                typed_entity_neighbors[target_id].append((source_id, weight, edge_type))
            entity_degrees[source_id].add(target_id)
            entity_degrees[target_id].add(source_id)

        snapshot.entity_neighbors = dict(cooccurrence_neighbors)
        snapshot.typed_entity_neighbors = dict(typed_entity_neighbors)
        snapshot.entity_degrees = {node_id: len(neighbors) for node_id, neighbors in entity_degrees.items()}

        entity_to_chunks: dict[str, list[ChunkEntityLink]] = defaultdict(list)
        for row in link_rows:
            link = ChunkEntityLink(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                node_id=row["node_id"],
                entity_type=row["entity_type"],
                weight=float(row["weight"]),
            )
            entity_to_chunks[link.node_id].append(link)

        relation_to_chunks: dict[tuple[str, str, str], list[GraphRelationLink]] = defaultdict(list)
        for row in relation_rows:
            relation_link = GraphRelationLink(
                source_id=row["source_id"],
                target_id=row["target_id"],
                edge_type=row["edge_type"],
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                confidence=float(row["confidence"]),
            )
            relation_to_chunks[(relation_link.source_id, relation_link.target_id, relation_link.edge_type)].append(relation_link)

        chunk_metadata_by_id: dict[str, dict] = {}
        chunk_to_document: dict[str, str] = {}
        document_to_indexed_chunks: dict[str, list[tuple[int, str]]] = defaultdict(list)
        for node in snapshot.nodes_by_id.values():
            if node.node_type != "chunk":
                continue
            chunk_id = node.value
            metadata = node.metadata or {}
            chunk_metadata_by_id[chunk_id] = metadata
            document_id = str(metadata.get("document_id") or "")
            if document_id:
                chunk_to_document[chunk_id] = document_id
                document_to_indexed_chunks[document_id].append((int(metadata.get("chunk_index") or 0), chunk_id))

        snapshot.chunk_metadata_by_id = chunk_metadata_by_id
        snapshot.chunk_to_document = chunk_to_document
        snapshot.document_to_chunks = {
            document_id: [chunk_id for _, chunk_id in sorted(indexed_chunks)]
            for document_id, indexed_chunks in document_to_indexed_chunks.items()
        }
        snapshot.entity_to_chunks = dict(entity_to_chunks)
        snapshot.relation_to_chunks = dict(relation_to_chunks)
        return snapshot

    @staticmethod
    def _upsert_edge(
        edges: dict[tuple[str, str, str], tuple[float, dict]],
        source_id: str,
        target_id: str,
        edge_type: str,
        weight: float,
        metadata: dict | None = None,
    ) -> None:
        key = (source_id, target_id, edge_type)
        existing = edges.get(key)
        if existing is None:
            edges[key] = (weight, metadata or {})
            return
        current_weight, current_metadata = existing
        merged_metadata = dict(current_metadata)
        merged_metadata.update(metadata or {})
        if edge_type in STRUCTURAL_EDGE_TYPES:
            next_weight = max(current_weight, weight)
        elif edge_type == "entity_cooccurs_with_entity":
            next_weight = round(current_weight + weight, 4)
        else:
            next_weight = round(max(current_weight, weight), 4)
        edges[key] = (next_weight, merged_metadata)

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._settings.benchmark_database_url, row_factory=dict_row)


def _safe_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
