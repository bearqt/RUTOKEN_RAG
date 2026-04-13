from __future__ import annotations

from collections import defaultdict
from itertools import combinations

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import Settings
from app.domain.graph_models import ChunkEntityLink, GraphNode, GraphSnapshot
from app.domain.models import Chunk


ENTITY_KEYS = (
    "products",
    "interfaces",
    "os_tags",
    "language_tags",
    "components",
    "api_symbols",
)

ENTITY_LINK_WEIGHTS = {
    "products": 0.9,
    "interfaces": 1.0,
    "os_tags": 0.6,
    "language_tags": 0.5,
    "components": 1.1,
    "api_symbols": 1.8,
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
        ]
        with self._connect() as conn:
            for statement in statements:
                conn.execute(statement)

    def replace_graph(self, chunks: list[Chunk]) -> None:
        nodes: dict[str, tuple[str, str, dict]] = {}
        edges: dict[tuple[str, str, str], tuple[float, dict]] = {}
        chunk_entity_links: dict[tuple[str, str], tuple[str, str, float]] = {}

        for chunk in chunks:
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
                    "chunk_type": chunk.chunk_type,
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
                self._upsert_edge(
                    edges,
                    *sorted((left_id, right_id)),
                    "entity_cooccurs_with_entity",
                    pair_weight,
                )

        with self._connect() as conn:
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
                WHERE edge_type = 'entity_cooccurs_with_entity'
                """
            ).fetchall()
            link_rows = conn.execute(
                """
                SELECT chunk_id, document_id, node_id, entity_type, weight
                FROM chunk_entity_links
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

        entity_neighbors: dict[str, list[tuple[str, float, str]]] = defaultdict(list)
        for row in edge_rows:
            entity_neighbors[row["source_id"]].append((row["target_id"], float(row["weight"]), row["edge_type"]))
            entity_neighbors[row["target_id"]].append((row["source_id"], float(row["weight"]), row["edge_type"]))
        snapshot.entity_neighbors = dict(entity_neighbors)

        entity_to_chunks: dict[str, list[ChunkEntityLink]] = defaultdict(list)
        chunk_to_document: dict[str, str] = {}
        document_to_chunks: dict[str, list[str]] = defaultdict(list)
        for row in link_rows:
            link = ChunkEntityLink(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                node_id=row["node_id"],
                entity_type=row["entity_type"],
                weight=float(row["weight"]),
            )
            entity_to_chunks[link.node_id].append(link)
            chunk_to_document[link.chunk_id] = link.document_id
            document_to_chunks[link.document_id].append(link.chunk_id)

        snapshot.entity_to_chunks = dict(entity_to_chunks)
        snapshot.chunk_to_document = chunk_to_document
        snapshot.document_to_chunks = {
            document_id: list(dict.fromkeys(chunk_ids))
            for document_id, chunk_ids in document_to_chunks.items()
        }
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
        edges[key] = (round(current_weight + weight, 4), merged_metadata)

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self._settings.benchmark_database_url, row_factory=dict_row)
