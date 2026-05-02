from __future__ import annotations

from typing import Any
from uuid import NAMESPACE_URL, uuid5

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from app.config import Settings


class GraphVectorStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = QdrantClient(url=settings.qdrant_url)

    def has_indices(self) -> bool:
        existing = {collection.name for collection in self._client.get_collections().collections}
        return {
            self._settings.graph_entity_collection,
            self._settings.graph_relation_collection,
        }.issubset(existing)

    def rebuild_entities(self, records: list[dict[str, Any]], vectors: list[list[float]]) -> None:
        self._rebuild_collection(self._settings.graph_entity_collection, records, vectors, "entity_id")

    def rebuild_relations(self, records: list[dict[str, Any]], vectors: list[list[float]]) -> None:
        self._rebuild_collection(self._settings.graph_relation_collection, records, vectors, "relation_id")

    def search_entities(self, query_vector: list[float], top_k: int) -> list[dict[str, Any]]:
        return self._search(self._settings.graph_entity_collection, query_vector, top_k)

    def search_relations(self, query_vector: list[float], top_k: int) -> list[dict[str, Any]]:
        return self._search(self._settings.graph_relation_collection, query_vector, top_k)

    def _rebuild_collection(
        self,
        collection_name: str,
        records: list[dict[str, Any]],
        vectors: list[list[float]],
        id_field: str,
    ) -> None:
        existing = {collection.name for collection in self._client.get_collections().collections}
        if not records or not vectors:
            if collection_name in existing:
                self._client.delete_collection(collection_name=collection_name)
            return
        vector_size = len(vectors[0])
        if collection_name in existing:
            self._client.delete_collection(collection_name=collection_name)
        self._client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

        points = [
            PointStruct(
                id=str(uuid5(NAMESPACE_URL, str(record[id_field]))),
                vector=vector,
                payload=record,
            )
            for record, vector in zip(records, vectors, strict=True)
        ]
        self._client.upsert(collection_name=collection_name, wait=True, points=points)

    def _search(self, collection_name: str, query_vector: list[float], top_k: int) -> list[dict[str, Any]]:
        if top_k <= 0:
            return []
        existing = {collection.name for collection in self._client.get_collections().collections}
        if collection_name not in existing:
            return []
        result = self._client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )
        hits: list[dict[str, Any]] = []
        for point in result.points:
            payload = dict(point.payload or {})
            payload["score"] = float(point.score)
            hits.append(payload)
        return hits
